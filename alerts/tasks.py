from celery import shared_task
from django.utils import timezone
from django.db.models import Q, Count, Sum, Avg, F
from django.contrib.auth import get_user_model
import logging

from .models import AlertRule, Alert, AlertDigest, SmartSuggestion
from campaigns.whatsapp import WhatsAppService, WhatsAppError

logger = logging.getLogger('alerts')


@shared_task(bind=True, max_retries=3, name='alerts.tasks.check_alert_rules')
def check_alert_rules(self):
    """Check all active alert rules and create alerts if conditions are met"""
    now = timezone.now()
    triggered_count = 0
    
    # Get all active alert rules
    rules = AlertRule.objects.filter(is_active=True).select_related('alert_type')
    
    for rule in rules:
        try:
            # Check if rule should trigger
            current_value = _get_metric_value(rule.metric, rule.time_period_hours)
            threshold = rule.threshold_value if rule.threshold_value is not None else rule.threshold_text
            
            if _evaluate_condition(current_value, rule.condition, threshold):
                # Create alert for each target user
                target_users = _get_target_users(rule)
                
                for user in target_users:
                    # Check if similar alert already exists recently
                    recent_cutoff = now - timezone.timedelta(hours=rule.time_period_hours)
                    existing_alert = Alert.objects.filter(
                        rule=rule,
                        recipients=user,
                        triggered_at__gte=recent_cutoff,
                        status__in=['active', 'acknowledged']
                    ).first()
                    
                    if not existing_alert:
                        # Create new alert
                        alert = Alert.objects.create(
                            rule=rule,
                            alert_type=rule.alert_type,
                            title=_generate_alert_title(rule, current_value),
                            message=_generate_alert_message(rule, current_value),
                            severity=rule.alert_type.severity,
                            metadata={
                                'metric': rule.metric,
                                'current_value': current_value,
                                'threshold': threshold,
                                'condition': rule.condition
                            }
                        )
                        
                        alert.recipients.add(user)
                        triggered_count += 1
                        
                        logger.info(f'[alerts] Alert triggered: {alert.title} for {user.full_name}')
        
        except Exception as e:
            logger.error(f'[alerts] Error checking rule {rule.name}: {e}')
            continue
    
    logger.info(f'[alerts] Triggered {triggered_count} alerts')
    return {'triggered_count': triggered_count}


def _get_metric_value(metric, time_period_hours):
    """Get current value for a metric"""
    from datetime import timedelta
    from sales.models import Sale
    from leads.models import Lead
    from calls.models import CallLog
    from attendance.models import Attendance
    
    cutoff_time = timezone.now() - timedelta(hours=time_period_hours)
    
    if metric == 'sales_count':
        return Sale.objects.filter(created_at__gte=cutoff_time).count()
    elif metric == 'sales_revenue':
        return float(Sale.objects.filter(created_at__gte=cutoff_time).aggregate(
            total=Sum('amount')
        )['total'] or 0)
    elif metric == 'leads_count':
        return Lead.objects.filter(created_at__gte=cutoff_time).count()
    elif metric == 'leads_converted':
        return Lead.objects.filter(
            stage='converted',
            updated_at__gte=cutoff_time
        ).count()
    elif metric == 'calls_made':
        return CallLog.objects.filter(created_at__gte=cutoff_time).count()
    elif metric == 'conversion_rate':
        total_leads = Lead.objects.filter(created_at__gte=cutoff_time).count()
        converted_leads = Lead.objects.filter(
            stage='converted',
            updated_at__gte=cutoff_time
        ).count()
        return (converted_leads / total_leads * 100) if total_leads > 0 else 0
    elif metric == 'attendance_rate':
        today = timezone.localdate()
        total_staff = Attendance.objects.filter(date=today).count()
        present_staff = Attendance.objects.filter(date=today, status='present').count()
        return (present_staff / total_staff * 100) if total_staff > 0 else 0
    elif metric == 'response_time':
        # Average response time in minutes
        from leads.models import LeadActivity
        activities = LeadActivity.objects.filter(
            created_at__gte=cutoff_time,
            action='contacted'
        )
        if activities.exists():
            return activities.aggregate(
                avg_time=Avg(F('created_at') - F('lead__created_at'))
            )['avg_time'].total_seconds() / 60
        return 0
    elif metric == 'followup_overdue':
        from leads.models import FollowUp
        return FollowUp.objects.filter(
            scheduled_date__lt=now,
            completed=False
        ).count()
    else:
        return 0


def _evaluate_condition(current_value, condition, threshold):
    """Evaluate if condition is met"""
    if condition == 'gt':
        return current_value > threshold
    elif condition == 'lt':
        return current_value < threshold
    elif condition == 'eq':
        return current_value == threshold
    elif condition == 'gte':
        return current_value >= threshold
    elif condition == 'lte':
        return current_value <= threshold
    elif condition == 'contains':
        return str(threshold).lower() in str(current_value).lower()
    elif condition == 'not_contains':
        return str(threshold).lower() not in str(current_value).lower()
    elif condition == 'is_null':
        return current_value is None
    elif condition == 'is_not_null':
        return current_value is not None
    else:
        return False


def _get_target_users(rule):
    """Get target users for an alert rule"""
    User = get_user_model()
    
    if rule.target_users.exists():
        return rule.target_users.all()
    
    if rule.target_roles:
        return User.objects.filter(role__in=rule.target_roles, is_active=True)
    
    return User.objects.none()


def _generate_alert_title(rule, current_value):
    """Generate alert title"""
    metric_names = {
        'sales_count': 'Sales Count',
        'sales_revenue': 'Sales Revenue',
        'leads_count': 'Lead Count',
        'leads_converted': 'Converted Leads',
        'calls_made': 'Calls Made',
        'conversion_rate': 'Conversion Rate',
        'attendance_rate': 'Attendance Rate',
        'response_time': 'Response Time',
        'followup_overdue': 'Overdue Follow-ups',
    }
    
    metric_name = metric_names.get(rule.metric, rule.metric.replace('_', ' ').title())
    
    if rule.condition in ['gt', 'gte']:
        return f'High {metric_name} Alert'
    elif rule.condition in ['lt', 'lte']:
        return f'Low {metric_name} Alert'
    else:
        return f'{metric_name} Alert'


def _generate_alert_message(rule, current_value):
    """Generate alert message"""
    metric_names = {
        'sales_count': 'sales',
        'sales_revenue': 'sales revenue',
        'leads_count': 'leads',
        'leads_converted': 'converted leads',
        'calls_made': 'calls',
        'conversion_rate': 'conversion rate',
        'attendance_rate': 'attendance rate',
        'response_time': 'response time',
        'followup_overdue': 'overdue follow-ups',
    }
    
    metric_name = metric_names.get(rule.metric, rule.metric)
    threshold = rule.threshold_value if rule.threshold_value is not None else rule.threshold_text
    
    # Use template if available
    if rule.alert_type.template_message:
        return rule.alert_type.template_message.format(
            metric=metric_name,
            current_value=current_value,
            threshold=threshold,
            condition=rule.condition
        )
    
    # Default message
    if rule.condition in ['gt', 'gte']:
        return f'{metric_name.title()} is {current_value}, which exceeds the threshold of {threshold}.'
    elif rule.condition in ['lt', 'lte']:
        return f'{metric_name.title()} is {current_value}, which is below the threshold of {threshold}.'
    else:
        return f'{metric_name.title()} is {current_value} (threshold: {threshold}).'


@shared_task(bind=True, max_retries=3, name='alerts.tasks.generate_alert_digests')
def generate_alert_digests(self):
    """Generate daily/weekly alert digests"""
    from datetime import date
    
    today = date.today()
    generated_count = 0
    
    # Generate daily digests
    users = get_user_model().objects.filter(is_active=True)
    
    for user in users:
        # Daily digest
        daily_digest, created = AlertDigest.objects.get_or_create(
            user=user,
            period='daily',
            digest_date=today,
            defaults={'alert_count': 0}
        )
        
        # Update digest counts
        alerts_today = Alert.objects.filter(
            recipients=user,
            triggered_at__date=today
        )
        
        daily_digest.alert_count = alerts_today.count()
        daily_digest.critical_count = alerts_today.filter(severity='critical').count()
        daily_digest.high_count = alerts_today.filter(severity='high').count()
        daily_digest.medium_count = alerts_today.filter(severity='medium').count()
        daily_digest.low_count = alerts_today.filter(severity='low').count()
        
        # Generate summary
        if daily_digest.alert_count > 0:
            top_alerts = alerts_today.order_by('-triggered_at')[:3]
            summary_lines = [f"Top alerts today:"]
            for alert in top_alerts:
                summary_lines.append(f"• {alert.title}")
            daily_digest.summary = '\n'.join(summary_lines)
        
        daily_digest.save()
        generated_count += 1
        
        # Weekly digest (Mondays only)
        if today.weekday() == 0:  # Monday
            week_start = today - timezone.timedelta(days=today.weekday())
            weekly_digest, _ = AlertDigest.objects.get_or_create(
                user=user,
                period='weekly',
                digest_date=week_start,
                defaults={'alert_count': 0}
            )
            
            alerts_week = Alert.objects.filter(
                recipients=user,
                triggered_at__date__gte=week_start
            )
            
            weekly_digest.alert_count = alerts_week.count()
            weekly_digest.critical_count = alerts_week.filter(severity='critical').count()
            weekly_digest.high_count = alerts_week.filter(severity='high').count()
            weekly_digest.medium_count = alerts_week.filter(severity='medium').count()
            weekly_digest.low_count = alerts_week.filter(severity='low').count()
            
            weekly_digest.save()
            generated_count += 1
    
    logger.info(f'[alerts] Generated {generated_count} alert digests')
    return {'generated_count': generated_count}


@shared_task(bind=True, max_retries=3, name='alerts.tasks.generate_smart_suggestions')
def generate_smart_suggestions(self):
    """Generate AI-powered smart suggestions based on data analysis"""
    from datetime import timedelta
    from sales.models import Sale
    from leads.models import Lead
    from calls.models import CallLog
    
    suggestions_created = 0
    
    # Analyze sales performance
    week_ago = timezone.now() - timedelta(days=7)
    two_weeks_ago = timezone.now() - timedelta(days=14)
    
    # Sales trend analysis
    current_week_sales = Sale.objects.filter(created_at__gte=week_ago).count()
    previous_week_sales = Sale.objects.filter(
        created_at__gte=two_weeks_ago,
        created_at__lt=week_ago
    ).count()
    
    if previous_week_sales > 0:
        sales_change = ((current_week_sales - previous_week_sales) / previous_week_sales) * 100
        
        # Suggest action if sales are declining
        if sales_change < -20:
            suggestion = SmartSuggestion.objects.create(
                title='Sales Decline Detected',
                category='sales',
                priority='high',
                description=f'Sales have decreased by {abs(sales_change):.1f}% compared to last week.',
                recommendation='Review recent sales activities and consider launching a promotional campaign.',
                expected_impact='Increased sales through targeted marketing efforts.',
                confidence_score=0.85,
                data_insights={
                    'current_week_sales': current_week_sales,
                    'previous_week_sales': previous_week_sales,
                    'percentage_change': sales_change
                }
            )
            
            # Assign to managers and owners
            managers = get_user_model().objects.filter(role__in=['owner', 'manager'], is_active=True)
            suggestion.target_users.set(managers)
            suggestions_created += 1
        
        # Suggest action if sales are growing
        elif sales_change > 30:
            suggestion = SmartSuggestion.objects.create(
                title='Sales Growth Opportunity',
                category='sales',
                priority='medium',
                description=f'Sales have increased by {sales_change:.1f}% compared to last week.',
                recommendation='Analyze successful strategies and consider scaling up effective campaigns.',
                expected_impact='Sustained growth through optimized strategies.',
                confidence_score=0.80,
                data_insights={
                    'current_week_sales': current_week_sales,
                    'previous_week_sales': previous_week_sales,
                    'percentage_change': sales_change
                }
            )
            
            managers = get_user_model().objects.filter(role__in=['owner', 'manager'], is_active=True)
            suggestion.target_users.set(managers)
            suggestions_created += 1
    
    # Lead conversion analysis
    total_leads = Lead.objects.filter(created_at__gte=week_ago).count()
    converted_leads = Lead.objects.filter(
        stage='converted',
        updated_at__gte=week_ago
    ).count()
    
    if total_leads > 0:
        conversion_rate = (converted_leads / total_leads) * 100
        
        if conversion_rate < 10:
            suggestion = SmartSuggestion.objects.create(
                title='Low Conversion Rate',
                category='leads',
                priority='high',
                description=f'Lead conversion rate is {conversion_rate:.1f}% this week.',
                recommendation='Review lead follow-up processes and provide additional sales training.',
                expected_impact='Improved conversion rates through better lead management.',
                confidence_score=0.75,
                data_insights={
                    'total_leads': total_leads,
                    'converted_leads': converted_leads,
                    'conversion_rate': conversion_rate
                }
            )
            
            managers = get_user_model().objects.filter(role__in=['owner', 'manager'], is_active=True)
            suggestion.target_users.set(managers)
            suggestions_created += 1
    
    logger.info(f'[alerts] Generated {suggestions_created} smart suggestions')
    return {'suggestions_created': suggestions_created}


@shared_task(bind=True, max_retries=3, name='alerts.tasks.cleanup_old_alerts')
def cleanup_old_alerts(self):
    """Clean up old resolved alerts"""
    from datetime import timedelta
    
    cutoff_date = timezone.now() - timedelta(days=90)
    
    deleted_count = Alert.objects.filter(
        status__in=['resolved', 'dismissed'],
        resolved_at__lt=cutoff_date
    ).delete()[0]
    
    logger.info(f'[alerts] Cleaned up {deleted_count} old alerts')
    return {'deleted_count': deleted_count}
