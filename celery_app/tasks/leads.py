from celery import shared_task
from django.utils import timezone
import logging

logger = logging.getLogger('leads')


@shared_task(bind=True, max_retries=3, name='celery_app.tasks.leads.send_followup_reminders')
def send_followup_reminders(self):
    """
    Daily 09:00 — send WhatsApp reminder to assigned_to staff
    for every FollowUp due today that isn't completed.
    """
    from leads.models import FollowUp
    from notifications.models import Notification
    from campaigns.whatsapp import WhatsAppService, WhatsAppError

    today   = timezone.localdate()
    service = WhatsAppService()
    sent    = 0
    notifs  = []

    due = FollowUp.objects.filter(
        scheduled_date__date=today,
        completed=False,
    ).select_related('lead', 'lead__assigned_to', 'created_by')

    for followup in due:
        lead   = followup.lead
        staff  = lead.assigned_to
        if not staff:
            continue

        msg = (
            f'🔔 Follow-up Reminder\n'
            f'Lead: {lead.name} ({lead.phone})\n'
            f'Stage: {lead.get_stage_display()}\n'
            f'Note: {followup.note or "—"}'
        )

        # WhatsApp to lead phone
        if lead.phone:
            try:
                service.send_text(lead.phone, msg)
                sent += 1
            except WhatsAppError as e:
                logger.error(f'[followup_reminder] WhatsApp to {lead.phone}: {e}')

        # In-app notification to staff member
        notifs.append(Notification(
            recipient=staff,
            title='Follow-up Reminder',
            body=f'Follow up with {lead.name} ({lead.phone}) today.',
            notif_type='followup',
        ))

    if notifs:
        Notification.objects.bulk_create(notifs, ignore_conflicts=True)

    logger.info(f'[followup_reminders] {sent} WhatsApp + {len(notifs)} in-app for {today}')
    return {'whatsapp_sent': sent, 'notifications': len(notifs), 'date': str(today)}


@shared_task(bind=True, max_retries=3, name='celery_app.tasks.leads.mark_overdue_leads')
def mark_overdue_leads(self):
    """
    Every 30 mins — find follow-ups past their scheduled_date
    and reduce related lead score by 5.
    """
    from leads.models import FollowUp, Lead
    from django.db.models import F

    now = timezone.now()
    overdue = FollowUp.objects.filter(
        scheduled_date__lt=now,
        completed=False,
    ).select_related('lead')

    count = 0
    for followup in overdue:
        Lead.objects.filter(pk=followup.lead_id).update(score=F('score') - 5)
        count += 1

    logger.info(f'[mark_overdue_leads] {count} overdue follow-ups found, scores reduced')
    return {'overdue_count': count}


@shared_task(bind=True, max_retries=3, name='celery_app.tasks.leads.assign_lead_async')
def assign_lead_async(self, lead_id, user_id):
    """Async lead assignment with in-app notification."""
    from leads.models import Lead, LeadActivity
    from django.contrib.auth import get_user_model
    from notifications.models import Notification

    User = get_user_model()
    try:
        lead = Lead.objects.get(id=lead_id)
        user = User.objects.get(id=user_id)
        lead.assigned_to = user
        lead.save(update_fields=['assigned_to'])

        LeadActivity.objects.create(
            lead=lead,
            actor=user,
            action='assigned',
            detail=f'Lead assigned to {user.full_name}',
        )
        Notification.objects.create(
            recipient=user,
            title='New Lead Assigned',
            body=f'Lead {lead.name} ({lead.phone}) has been assigned to you.',
            notif_type='general',
        )
        return {'lead_id': lead_id, 'assigned_to': user.full_name}
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3, name='celery_app.tasks.leads.send_eod_report')
def send_eod_report(self):
    """
    Daily 19:00 — generate end-of-day summary notification
    for every active branch manager and the owner.
    """
    from sales.models import Sale
    from leads.models import Lead
    from calls.models import CallLog
    from notifications.models import Notification
    from django.contrib.auth import get_user_model
    from django.db.models import Sum

    User    = get_user_model()
    today   = timezone.localdate()
    notifs  = []

    managers = User.objects.filter(
        role__in=['manager', 'owner', 'sub_manager'],
        is_active=True,
    )

    for manager in managers:
        f = {} if manager.role == 'owner' else {'branch': manager.branch}
        leads_count = Lead.objects.filter(created_at__date=today, **f).count()
        calls_count = CallLog.objects.filter(created_at__date=today, **f).count()
        sales_total_weight = (
            Sale.objects.filter(created_at__date=today, **f)
            .aggregate(t=Sum('weight_grams'))['t'] or 0
        )

        notifs.append(Notification(
            recipient=manager,
            title='End of Day Report',
            body=(
                f'📊 Summary for {today}\n'
                f'Leads: {leads_count} | Calls: {calls_count} | '
                f'Gold Sold: {sales_total_weight:,.2f}g'
            ),
            notif_type='general',
        ))

    if notifs:
        Notification.objects.bulk_create(notifs)

    logger.info(f'[eod_report] Sent to {len(notifs)} managers for {today}')
    return {'recipients': len(notifs), 'date': str(today)}


@shared_task(bind=True, max_retries=3, name='celery_app.tasks.leads.send_birthday_wishes')
def send_birthday_wishes(self):
    """Daily 00:00 — WhatsApp birthday wishes to staff."""
    from django.contrib.auth import get_user_model
    from campaigns.models import WhatsAppTemplate
    from campaigns.whatsapp import WhatsAppService, WhatsAppError

    User    = get_user_model()
    today   = timezone.localdate()
    service = WhatsAppService()
    sent    = 0

    template = WhatsAppTemplate.objects.filter(
        trigger='birthday', is_active=True
    ).first()

    if not template:
        logger.warning('[birthday] No active birthday WhatsAppTemplate found.')
        return {'sent': 0}

    users = User.objects.filter(
        date_of_birth__month=today.month,
        date_of_birth__day=today.day,
        is_active=True,
    ).exclude(phone='')

    for user in users:
        if not user.phone:
            continue
        try:
            msg = template.render(user)
            service.send_text(user.phone, msg)
            sent += 1
        except WhatsAppError as e:
            logger.error(f'[birthday] {user.full_name} ({user.phone}): {e}')

    logger.info(f'[birthday_wishes] {sent} sent on {today}')
    return {'sent': sent, 'date': str(today)}


@shared_task(bind=True, max_retries=3, name='celery_app.tasks.leads.send_anniversary_wishes')
def send_anniversary_wishes(self):
    """Daily 00:01 — WhatsApp work anniversary wishes to staff."""
    from django.contrib.auth import get_user_model
    from campaigns.models import WhatsAppTemplate
    from campaigns.whatsapp import WhatsAppService, WhatsAppError

    User    = get_user_model()
    today   = timezone.localdate()
    service = WhatsAppService()
    sent    = 0

    template = WhatsAppTemplate.objects.filter(
        trigger='anniversary', is_active=True
    ).first()

    if not template:
        logger.warning('[anniversary] No active anniversary WhatsAppTemplate found.')
        return {'sent': 0}

    users = User.objects.filter(
        join_date__month=today.month,
        join_date__day=today.day,
        is_active=True,
    ).exclude(phone='')

    for user in users:
        try:
            msg = template.render(user)
            service.send_text(user.phone, msg)
            sent += 1
        except WhatsAppError as e:
            logger.error(f'[anniversary] {user.full_name} ({user.phone}): {e}')

    logger.info(f'[anniversary_wishes] {sent} sent on {today}')
    return {'sent': sent, 'date': str(today)}