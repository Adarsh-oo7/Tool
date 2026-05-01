from celery import shared_task
from django.utils import timezone
from django.db.models import Sum, Count
import logging

logger = logging.getLogger('campaigns')


@shared_task(bind=True, max_retries=3, name='celery_app.tasks.campaigns.send_weekly_campaign_report')
def send_weekly_campaign_report(self):
    from campaigns.models import Campaign
    from notifications.models import Notification
    from accounts.models import User

    today    = timezone.localdate()
    week_ago = today - timezone.timedelta(days=7)

    campaigns = Campaign.objects.filter(
        status='active',
    ).annotate(
        total_leads=Count('campaign_leads', distinct=True),   # ← fixed: campaign_leads not leads
        total_sales=Sum('campaign_leads__lead__sales__amount'),
    )

    managers = User.objects.filter(role__in=['owner', 'manager'], is_active=True)
    notifs   = []

    for manager in managers:
        lines = [f'📈 Weekly Report ({week_ago} → {today}):']
        for c in campaigns:
            lines.append(f'• {c.name}: {c.total_leads} leads | ₹{c.total_sales or 0:,.2f} sales')
        if not campaigns:
            lines.append('No active campaigns this week.')
        notifs.append(Notification(
            user=manager,
            title='Weekly Campaign Report',
            message='\n'.join(lines),
            notif_type='report',
        ))

    if notifs:
        Notification.objects.bulk_create(notifs)

    return {'recipients': len(notifs)}


@shared_task(bind=True, max_retries=3, name='celery_app.tasks.campaigns.activate_due_campaigns')
def activate_due_campaigns(self):
    from campaigns.models import Campaign

    today = timezone.localdate()
    count = Campaign.objects.filter(
        status='scheduled',
        scheduled_at__date__lte=today,   # ← fixed: scheduled_at not start_date
    ).update(status='active')

    logger.info(f'[activate_due_campaigns] {count} activated')
    return {'activated': count}


@shared_task(bind=True, max_retries=3, name='celery_app.tasks.campaigns.deactivate_expired_campaigns')
def deactivate_expired_campaigns(self):
    from campaigns.models import Campaign

    today = timezone.localdate()
    # Campaigns sent more than 1 day ago → mark completed
    count = Campaign.objects.filter(
        status='active',
        sent_at__date__lt=today,         # ← fixed: sent_at not end_date
    ).update(status='completed')

    logger.info(f'[deactivate_expired_campaigns] {count} completed')
    return {'completed': count}


@shared_task(bind=True, max_retries=3, name='celery_app.tasks.campaigns.generate_branch_snapshot')
def generate_branch_snapshot(self, branch_id, period='daily'):
    from branches.models import Branch
    from reports.models import Report
    from sales.models import Sale
    from leads.models import Lead
    from calls.models import Call
    from django.db.models import Sum

    today  = timezone.localdate()
    branch = Branch.objects.get(id=branch_id)
    f = {'created_at__date': today} if period == 'daily' else {
        'created_at__year': today.year,
        'created_at__month': today.month,
    }
    data = {
        'leads':        Lead.objects.filter(branch=branch, **f).count(),
        'calls':        Call.objects.filter(branch=branch, **f).count(),
        'sales_count':  Sale.objects.filter(branch=branch, **f).count(),
        'sales_amount': str(
            Sale.objects.filter(branch=branch, **f)
            .aggregate(t=Sum('amount'))['t'] or 0
        ),
    }
    report = Report.objects.create(branch=branch, period=period, date=today, data=data)
    logger.info(f'[branch_snapshot] {period} report for {branch.name} — id:{report.id}')
    return {'report_id': report.id, 'branch': branch.name, 'data': data}


@shared_task(bind=True, max_retries=3, name='celery_app.tasks.campaigns.send_special_day_messages')
def send_special_day_messages(self):
    """Daily 12:04 AM — send WhatsApp for today's special days (Onam, Eid, Christmas etc.)"""
    from campaigns.models import SpecialDayMessage
    from campaigns.whatsapp import WhatsAppService
    from accounts.models import User
    from leads.models import Lead

    today   = timezone.localdate()
    service = WhatsAppService()
    sent    = 0

    days = SpecialDayMessage.objects.filter(
        date__month=today.month,
        date__day=today.day,
        is_active=True,
    )

    for day in days:
        if day.send_to_staff:
            for user in User.objects.filter(is_active=True).exclude(phone=''):
                try:
                    msg = day.message.format(
                        name=user.full_name,
                        branch=user.branch.name if user.branch else '',
                    )
                    service.send_text(user.phone, msg)
                    sent += 1
                except Exception as e:
                    logger.error(f'[special_day] Staff {user.full_name}: {e}')

        if day.send_to_leads:
            for lead in Lead.objects.filter(
                status__in=['interested', 'contacted']
            ).exclude(phone=''):
                try:
                    msg = day.message.format(name=lead.name, branch='')
                    service.send_text(lead.phone, msg)
                    sent += 1
                except Exception as e:
                    logger.error(f'[special_day] Lead {lead.name}: {e}')

    logger.info(f'[special_day_messages] {sent} messages sent on {today}')
    return {'sent': sent, 'date': str(today)}