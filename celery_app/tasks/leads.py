from celery import shared_task
from django.utils import timezone
import logging

logger = logging.getLogger('leads')


@shared_task(bind=True, max_retries=3, name='celery_app.tasks.leads.send_followup_reminders')
def send_followup_reminders(self):
    from leads.models import Lead
    from notifications.models import Notification

    today = timezone.localdate()
    due_leads = Lead.objects.filter(
        next_followup_date=today,
        status__in=['new', 'contacted', 'interested'],
    ).select_related('assigned_to')

    notifs = [
        Notification(
            user=lead.assigned_to,
            title='Follow-up Reminder',
            message=f'Follow up with {lead.name} ({lead.phone}) today.',
            notif_type='followup',
        )
        for lead in due_leads if lead.assigned_to
    ]
    if notifs:
        Notification.objects.bulk_create(notifs, ignore_conflicts=True)

    logger.info(f'[followup_reminders] {len(notifs)} notifications for {today}')
    return {'sent': len(notifs), 'date': str(today)}


@shared_task(bind=True, max_retries=3, name='celery_app.tasks.leads.mark_overdue_leads')
def mark_overdue_leads(self):
    from leads.models import Lead

    today = timezone.localdate()
    count = Lead.objects.filter(
        next_followup_date__lt=today,
        status__in=['new', 'contacted', 'interested'],
    ).update(status='overdue')

    logger.info(f'[mark_overdue_leads] {count} leads marked overdue')
    return {'marked_overdue': count}


@shared_task(bind=True, max_retries=3, name='celery_app.tasks.leads.assign_lead_async')
def assign_lead_async(self, lead_id, user_id):
    from leads.models import Lead
    from accounts.models import User
    from notifications.models import Notification

    try:
        lead = Lead.objects.get(id=lead_id)
        user = User.objects.get(id=user_id)
        lead.assigned_to = user
        lead.save(update_fields=['assigned_to'])
        Notification.objects.create(
            user=user,
            title='New Lead Assigned',
            message=f'Lead {lead.name} ({lead.phone}) assigned to you.',
            notif_type='assignment',
        )
        return {'lead_id': lead_id, 'assigned_to': user.full_name}
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3, name='celery_app.tasks.leads.send_eod_report')
def send_eod_report(self):
    from sales.models import Sale
    from leads.models import Lead
    from calls.models import Call
    from notifications.models import Notification
    from accounts.models import User
    from django.db.models import Sum

    today = timezone.localdate()
    managers = User.objects.filter(role__in=['manager', 'owner'], is_active=True)
    notifs = []

    for manager in managers:
        f = {} if manager.role == 'owner' else {'branch': manager.branch}
        leads_count = Lead.objects.filter(created_at__date=today, **f).count()
        calls_count = Call.objects.filter(called_at__date=today, **f).count()
        sales_total = Sale.objects.filter(created_at__date=today, **f).aggregate(t=Sum('amount'))['t'] or 0

        notifs.append(Notification(
            user=manager,
            title='End of Day Report',
            message=f'📊 {today}: {leads_count} leads | {calls_count} calls | ₹{sales_total:,.2f} sales',
            notif_type='report',
        ))

    if notifs:
        Notification.objects.bulk_create(notifs)

    return {'recipients': len(notifs), 'date': str(today)}