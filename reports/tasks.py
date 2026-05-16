from celery import shared_task
from django.utils import timezone
from django.db.models import Q, Count, Sum, Avg, F
from django.contrib.auth import get_user_model
from datetime import timedelta, date
import logging

from .models import Report, DailyReport, ReportTemplate, ReportSchedule, ReportLog
from campaigns.whatsapp import WhatsAppService, WhatsAppError
from notifications.models import Notification

logger = logging.getLogger('reports')


@shared_task(bind=True, max_retries=3, name='reports.tasks.generate_daily_eod_reports')
def generate_daily_eod_reports(self):
    """Generate daily End-of-Day reports for all branches"""
    today = timezone.localdate()
    generated_count = 0
    failed_count = 0
    
    # Get all branches
    from branches.models import Branch
    branches = Branch.objects.filter(is_active=True)
    
    for branch in branches:
        try:
            # Generate comprehensive report
            report_data = _generate_branch_report_data(branch, today)
            
            # Create or update Report
            report, created = Report.objects.update_or_create(
                branch=branch,
                period='daily',
                date=today,
                defaults={
                    'data': report_data,
                    'status': 'completed'
                }
            )
            
            if not created:
                report.data = report_data
                report.status = 'completed'
                report.error_message = ''
                report.save(update_fields=['data', 'status', 'error_message'])
            
            # Generate enhanced DailyReport
            daily_report_data = _generate_daily_report_metrics(branch, today)
            
            daily_report, daily_created = DailyReport.objects.update_or_create(
                branch=branch,
                date=today,
                defaults=daily_report_data
            )
            
            if not daily_created:
                for key, value in daily_report_data.items():
                    setattr(daily_report, key, value)
                daily_report.save()
            
            # Add recipients (managers and owners)
            managers = get_user_model().objects.filter(
                role__in=['owner', 'manager'],
                is_active=True
            )
            
            if branch.manager:
                managers = managers | get_user_model().objects.filter(id=branch.manager.id)
            
            report.recipients.set(managers)
            daily_report.sent_to.set(managers)
            
            # Log successful generation
            ReportLog.objects.create(
                report=report,
                status='completed',
                completed_at=timezone.now(),
                duration_seconds=0,
                metadata={'branch_id': branch.id, 'date': str(today)},
                triggered_by='auto_daily_eod'
            )
            
            generated_count += 1
            logger.info(f'[reports] Daily EOD report generated for {branch.name}')
            
        except Exception as e:
            failed_count += 1
            logger.error(f'[reports] Error generating daily report for {branch.name}: {e}')
            
            # Log failure
            ReportLog.objects.create(
                status='failed',
                error_message=str(e),
                metadata={'branch_id': branch.id, 'date': str(today)},
                triggered_by='auto_daily_eod'
            )
            
            # Update report status if it exists
            Report.objects.filter(
                branch=branch,
                period='daily',
                date=today
            ).update(status='failed', error_message=str(e))
    
    logger.info(f'[reports] Generated {generated_count} daily EOD reports, {failed_count} failed')
    return {'generated': generated_count, 'failed': failed_count}


@shared_task(bind=True, max_retries=3, name='reports.tasks.generate_branch_snapshot')
def generate_branch_snapshot(self, branch_id: int, period: str = 'daily', start_date=None, end_date=None):
    """Generate a report snapshot for a specific branch and period."""
    from branches.models import Branch
    try:
        branch = Branch.objects.get(id=branch_id)
        report_date = timezone.localdate()
        
        # If specific range provided, we use that. 
        # Note: _generate_branch_report_data uses a 'report_date' as a reference point for 'daily'.
        # We might need to adjust it to handle ranges.
        
        # Generate comprehensive report
        report_data = _generate_branch_report_data(branch, report_date, start_date=start_date, end_date=end_date)
        
        # For historical/period reports, we might not want to update_or_create with a fixed 'date'
        # if it's not actually 'today'. But for 'trigger', usually it's for today or a specific range.
        
        report_id_to_return = None
        if not start_date:
            # Standard daily update
            report, _ = Report.objects.update_or_create(
                branch=branch,
                period=period,
                date=report_date,
                defaults={
                    'data': report_data,
                    'status': 'completed'
                }
            )
            report_id_to_return = report.id
            
            # Also update DailyReport model for consistency if it's daily
            if period == 'daily':
                daily_report_data = _generate_daily_report_metrics(branch, report_date)
                DailyReport.objects.update_or_create(
                    branch=branch,
                    date=report_date,
                    defaults=daily_report_data
                )
        else:
            # Period report (7d, 30d, etc) - store as a special period if needed
            # For now, let's just return the data or create a 'custom' period report
            report = Report.objects.create(
                branch=branch,
                period=f"custom_{period}",
                date=report_date,
                data=report_data,
                status='completed'
            )
            report_id_to_return = report.id

        logger.info(f'[reports] Snapshot generated for {branch.name} ({period})')
        return {'status': 'completed', 'report_id': report_id_to_return, 'branch': branch.name}
    except Exception as e:
        logger.error(f'[reports] Error generating snapshot for branch {branch_id}: {e}')
        raise self.retry(exc=e, countdown=60)


def _generate_branch_report_data(branch, report_date, start_date=None, end_date=None):
    """Generate comprehensive report data for a branch"""
    from sales.models import Sale
    from leads.models import Lead, FollowUp
    from calls.models import CallLog
    from attendance.models import Attendance
    from field_visits.models import FieldVisit
    
    # Date range for the report
    if start_date and end_date:
        # Convert strings to date objects if needed
        if isinstance(start_date, str):
            start_date = date.fromisoformat(start_date)
        if isinstance(end_date, str):
            end_date = date.fromisoformat(end_date)
            
        start_datetime = timezone.make_aware(
            timezone.datetime.combine(start_date, timezone.datetime.min.time())
        )
        end_datetime = timezone.make_aware(
            timezone.datetime.combine(end_date, timezone.datetime.max.time())
        )
    else:
        start_datetime = timezone.make_aware(
            timezone.datetime.combine(report_date, timezone.datetime.min.time())
        )
        end_datetime = start_datetime + timedelta(days=1)
    
    # Sales data
    sales_queryset = Sale.objects.filter(
        branch=branch,
        created_at__gte=start_datetime,
        created_at__lt=end_datetime
    )
    
    # Segment breakdown
    weight_by_segment = {}
    segment_weights = sales_queryset.values('segment__name').annotate(total=Sum('weight_grams'))
    for sw in segment_weights:
        seg_name = sw['segment__name'] or 'Unknown'
        weight_by_segment[seg_name] = float(sw['total'] or 0)

    sales_data = {
        'count': sales_queryset.count(),
        'revenue': float(sales_queryset.aggregate(
            total=Sum('amount')
        )['total'] or 0),
        'weight': float(sales_queryset.aggregate(
            total=Sum('weight_grams')
        )['total'] or 0),
        'weight_by_segment': weight_by_segment,
        'average_sale': float(sales_queryset.aggregate(
            avg=Avg('amount')
        )['avg'] or 0),
        'top_sales': list(
            sales_queryset.values('staff__full_name')
            .annotate(count=Count('id'), weight=Sum('weight_grams'))
            .order_by('-weight')[:5]
        )
    }
    
    # Leads data
    leads_queryset = Lead.objects.filter(
        branch=branch,
        created_at__gte=start_datetime,
        created_at__lt=end_datetime
    )
    
    leads_converted = leads_queryset.filter(stage='converted').count()
    conversion_rate = (leads_converted / leads_queryset.count() * 100) if leads_queryset.count() > 0 else 0
    
    leads_data = {
        'total': leads_queryset.count(),
        'converted': leads_converted,
        'conversion_rate': round(conversion_rate, 2),
        'by_source': list(
            leads_queryset.values('source')
            .annotate(count=Count('id'))
            .order_by('-count')
        ),
        'by_stage': list(
            leads_queryset.values('stage')
            .annotate(count=Count('id'))
            .order_by('-count')
        ),
        'hot_leads': leads_queryset.filter(is_hot=True).count()
    }
    
    # Calls data
    calls_queryset = CallLog.objects.filter(
        lead__branch=branch,
        created_at__gte=start_datetime,
        created_at__lt=end_datetime
    )
    
    calls_data = {
        'total': calls_queryset.count(),
        'connected': calls_queryset.exclude(outcome='no_answer').count(),
        'not_connected': calls_queryset.filter(outcome='no_answer').count(),
        'by_staff': list(
            calls_queryset.values('staff__full_name')
            .annotate(count=Count('id'))
            .order_by('-count')[:5]
        )
    }
    
    # Attendance data
    attendance_queryset = Attendance.objects.filter(
        date=report_date,
        user__branch=branch
    )
    
    attendance_data = {
        'total_staff': attendance_queryset.count(),
        'present': attendance_queryset.filter(status='present').count(),
        'absent': attendance_queryset.filter(status='absent').count(),
        'late': attendance_queryset.filter(status='late').count(),
        'rate': round(
            (attendance_queryset.filter(status='present').count() / attendance_queryset.count() * 100)
            if attendance_queryset.count() > 0 else 0, 2
        )
    }
    
    # Field visits data
    field_visits_queryset = FieldVisit.objects.filter(
        branch=branch,
        started_at__gte=start_datetime,
        started_at__lt=end_datetime
    )
    
    field_visits_data = {
        'total': field_visits_queryset.count(),
        'completed': field_visits_queryset.filter(status='completed').count(),
        'active': field_visits_queryset.filter(status='active').count(),
        'by_staff': list(
            field_visits_queryset.values('staff__full_name')
            .annotate(count=Count('id'))
            .order_by('-count')[:5]
        )
    }
    
    # Follow-ups data
    followups_queryset = FollowUp.objects.filter(
        lead__branch=branch,
        scheduled_date__gte=start_datetime,
        scheduled_date__lt=end_datetime
    )
    
    followups_data = {
        'scheduled': followups_queryset.count(),
        'completed': followups_queryset.filter(completed=True).count(),
        'missed': followups_queryset.filter(status='missed').count(),
        'pending': followups_queryset.filter(status='pending').count()
    }
    
    return {
        'date': report_date.isoformat(),
        'branch': {
            'id': branch.id,
            'name': branch.name,
            'address': branch.address,
            'phone': branch.phone
        },
        'sales': sales_data,
        'leads': leads_data,
        'calls': calls_data,
        'attendance': attendance_data,
        'field_visits': field_visits_data,
        'followups': followups_data,
        'generated_at': timezone.now().isoformat()
    }


def _generate_daily_report_metrics(branch, report_date):
    """Generate metrics for DailyReport model"""
    from sales.models import Sale
    from leads.models import Lead, FollowUp
    from calls.models import CallLog
    from attendance.models import Attendance
    
    # Date range
    start_datetime = timezone.make_aware(
        timezone.datetime.combine(report_date, timezone.datetime.min.time())
    )
    end_datetime = start_datetime + timedelta(days=1)
    
    # Basic metrics
    total_leads = Lead.objects.filter(
        branch=branch,
        created_at__gte=start_datetime,
        created_at__lt=end_datetime
    ).count()
    
    total_calls = CallLog.objects.filter(
        lead__branch=branch,
        created_at__gte=start_datetime,
        created_at__lt=end_datetime
    ).count()
    
    sales_queryset = Sale.objects.filter(
        branch=branch,
        created_at__gte=start_datetime,
        created_at__lt=end_datetime
    )
    
    total_sales = sales_queryset.count()
    total_revenue = sales_queryset.aggregate(
        total=Sum('amount')
    )['total'] or 0
    total_weight = sales_queryset.aggregate(
        total=Sum('weight_grams')
    )['total'] or 0
    
    # Segment breakdown
    weight_by_segment = {}
    segment_weights = sales_queryset.values('segment__name').annotate(total=Sum('weight_grams'))
    for sw in segment_weights:
        seg_name = sw['segment__name'] or 'Unknown'
        weight_by_segment[seg_name] = float(sw['total'] or 0)
    
    # Enhanced metrics
    leads_converted = Lead.objects.filter(
        branch=branch,
        stage='converted',
        updated_at__gte=start_datetime,
        updated_at__lt=end_datetime
    ).count()
    
    calls_connected = CallLog.objects.filter(
        created_at__gte=start_datetime,
        created_at__lt=end_datetime,
    ).exclude(outcome='no_answer').count()
    
    attendance_queryset = Attendance.objects.filter(
        date=report_date,
        user__branch=branch
    )
    
    attendance_present = attendance_queryset.filter(status='present').count()
    attendance_total = attendance_queryset.count()
    
    # Calculate rates
    conversion_rate = (leads_converted / total_leads * 100) if total_leads > 0 else 0
    call_connect_rate = (calls_connected / total_calls * 100) if total_calls > 0 else 0
    attendance_rate = (attendance_present / attendance_total * 100) if attendance_total > 0 else 0
    
    return {
        'total_leads': total_leads,
        'total_calls': total_calls,
        'total_sales': total_sales,
        'total_revenue': total_revenue,
        'total_weight': total_weight,
        'weight_by_segment': weight_by_segment,
        'leads_converted': leads_converted,
        'calls_connected': calls_connected,
        'attendance_present': attendance_present,
        'attendance_total': attendance_total,
        'conversion_rate': round(conversion_rate, 2),
        'call_connect_rate': round(call_connect_rate, 2),
        'attendance_rate': round(attendance_rate, 2),
        'status': 'completed',
        'error_message': ''
    }


@shared_task(bind=True, max_retries=3, name='reports.tasks.send_daily_reports')
def send_daily_reports(self):
    """Send daily reports to recipients via WhatsApp and notifications"""
    today = timezone.localdate()
    sent_count = 0
    
    # Get all completed daily reports
    reports = Report.objects.filter(
        period='daily',
        date=today,
        status='completed',
        sent_at__isnull=True
    ).select_related('branch').prefetch_related('recipients')
    
    service = WhatsAppService()
    
    for report in reports:
        try:
            # Generate report summary
            summary = _generate_report_summary(report)
            
            # Send to each recipient
            for recipient in report.recipients.all():
                if recipient.phone:
                    # Send WhatsApp message
                    message = f"📊 Daily EOD Report - {report.branch.name}\n\n{summary}"
                    service.send_text(recipient.phone, message)
                
                # Create in-app notification
                Notification.objects.create(
                    recipient=recipient,
                    title=f'Daily EOD Report - {report.branch.name}',
                    body=summary,
                    notif_type='report',
                    metadata={
                        'report_id': report.id,
                        'branch_id': report.branch.id,
                        'date': str(today)
                    }
                )
            
            # Mark as sent
            report.sent_at = timezone.now()
            report.save(update_fields=['sent_at'])
            
            sent_count += 1
            logger.info(f'[reports] Daily report sent for {report.branch.name}')
            
        except Exception as e:
            logger.error(f'[reports] Error sending daily report for {report.branch.name}: {e}')
            continue
    
    logger.info(f'[reports] Sent {sent_count} daily reports')
    return {'sent_count': sent_count}


def _generate_report_summary(report):
    """Generate a human-readable summary of the report"""
    data = report.data or {}
    
    summary_lines = [
        f"📅 Date: {report.date}",
        "",
        "📈 PERFORMANCE METRICS:",
        f"• Leads: {data.get('leads', {}).get('total', 0)}",
        f"• Sales: {data.get('sales', {}).get('count', 0)}",
        f"• Gold Sold: {data.get('sales', {}).get('weight', 0)}g",
        f"• Conversion Rate: {data.get('leads', {}).get('conversion_rate', 0)}%",
        "",
        "📞 ACTIVITY:",
        f"• Calls: {data.get('calls', {}).get('total', 0)}",
        f"• Connected: {data.get('calls', {}).get('connected', 0)}",
        f"• Field Visits: {data.get('field_visits', {}).get('total', 0)}",
        "",
        "👥 STAFF:",
        f"• Attendance Rate: {data.get('attendance', {}).get('rate', 0)}%",
        f"• Present: {data.get('attendance', {}).get('present', 0)}",
        f"• Total Staff: {data.get('attendance', {}).get('total_staff', 0)}",
    ]
    
    return '\n'.join(summary_lines)


@shared_task(bind=True, max_retries=3, name='reports.tasks.generate_weekly_reports')
def generate_weekly_reports(self):
    """Generate weekly summary reports"""
    today = timezone.localdate()
    week_start = today - timedelta(days=today.weekday())
    generated_count = 0
    
    # Get all branches
    from branches.models import Branch
    branches = Branch.objects.filter(is_active=True)
    
    for branch in branches:
        try:
            # Generate weekly data by aggregating daily reports
            daily_reports = Report.objects.filter(
                branch=branch,
                period='daily',
                date__gte=week_start,
                date__lt=today + timedelta(days=1),
                status='completed'
            )
            
            if daily_reports.exists():
                weekly_data = _aggregate_weekly_data(daily_reports)
                
                # Create weekly report
                report, created = Report.objects.update_or_create(
                    branch=branch,
                    period='weekly',
                    date=week_start,
                    defaults={
                        'data': weekly_data,
                        'status': 'completed'
                    }
                )
                
                if not created:
                    report.data = weekly_data
                    report.status = 'completed'
                    report.save(update_fields=['data', 'status'])
                
                # Add recipients
                managers = get_user_model().objects.filter(
                    role__in=['owner', 'manager'],
                    is_active=True
                )
                
                if branch.manager:
                    managers = managers | get_user_model().objects.filter(id=branch.manager.id)
                
                report.recipients.set(managers)
                
                generated_count += 1
                logger.info(f'[reports] Weekly report generated for {branch.name}')
        
        except Exception as e:
            logger.error(f'[reports] Error generating weekly report for {branch.name}: {e}')
            continue
    
    logger.info(f'[reports] Generated {generated_count} weekly reports')
    return {'generated_count': generated_count}


def _aggregate_weekly_data(daily_reports):
    """Aggregate daily reports into weekly data"""
    weekly_data = {
        'date': daily_reports.first().date,
        'period': 'weekly',
        'branch': daily_reports.first().data.get('branch'),
        'sales': {'count': 0, 'revenue': 0, 'weight': 0},
        'leads': {'total': 0, 'converted': 0},
        'calls': {'total': 0, 'connected': 0},
        'attendance': {'total_staff': 0, 'present': 0},
        'field_visits': {'total': 0, 'completed': 0},
        'followups': {'scheduled': 0, 'completed': 0},
        'daily_breakdown': []
    }
    
    for daily_report in daily_reports:
        data = daily_report.data
        
        # Aggregate sales
        weekly_data['sales']['count'] += data.get('sales', {}).get('count', 0)
        weekly_data['sales']['revenue'] += data.get('sales', {}).get('revenue', 0)
        weekly_data['sales']['weight'] += data.get('sales', {}).get('weight', 0)
        
        # Aggregate leads
        weekly_data['leads']['total'] += data.get('leads', {}).get('total', 0)
        weekly_data['leads']['converted'] += data.get('leads', {}).get('converted', 0)
        
        # Aggregate calls
        weekly_data['calls']['total'] += data.get('calls', {}).get('total', 0)
        weekly_data['calls']['connected'] += data.get('calls', {}).get('connected', 0)
        
        # Aggregate attendance
        weekly_data['attendance']['total_staff'] += data.get('attendance', {}).get('total_staff', 0)
        weekly_data['attendance']['present'] += data.get('attendance', {}).get('present', 0)
        
        # Add daily breakdown
        weekly_data['daily_breakdown'].append({
            'date': data.get('date'),
            'sales': data.get('sales', {}),
            'leads': data.get('leads', {}),
            'calls': data.get('calls', {})
        })
    
    # Calculate averages and rates
    if weekly_data['leads']['total'] > 0:
        weekly_data['leads']['conversion_rate'] = round(
            (weekly_data['leads']['converted'] / weekly_data['leads']['total'] * 100), 2
        )
    
    if weekly_data['attendance']['total_staff'] > 0:
        weekly_data['attendance']['rate'] = round(
            (weekly_data['attendance']['present'] / weekly_data['attendance']['total_staff'] * 100), 2
        )
    
    return weekly_data


@shared_task(bind=True, max_retries=3, name='reports.tasks.cleanup_old_reports')
def cleanup_old_reports(self):
    """Clean up old reports to save storage space"""
    from datetime import timedelta
    
    # Keep reports for 90 days
    cutoff_date = timezone.localdate() - timedelta(days=90)
    
    deleted_count = Report.objects.filter(date__lt=cutoff_date).delete()[0]
    
    # Keep daily reports for 30 days
    daily_cutoff = timezone.localdate() - timedelta(days=30)
    deleted_daily = DailyReport.objects.filter(date__lt=daily_cutoff).delete()[0]
    
    # Keep logs for 30 days
    log_cutoff = timezone.now() - timedelta(days=30)
    deleted_logs = ReportLog.objects.filter(started_at__lt=log_cutoff).delete()[0]
    
    logger.info(f'[reports] Cleaned up {deleted_count} reports, {deleted_daily} daily reports, {deleted_logs} logs')
    return {
        'deleted_reports': deleted_count,
        'deleted_daily_reports': deleted_daily,
        'deleted_logs': deleted_logs
    }
