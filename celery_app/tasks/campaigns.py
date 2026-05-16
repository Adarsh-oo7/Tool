from celery import shared_task
from django.utils import timezone
from django.db.models import Sum, Count
import logging

logger = logging.getLogger('campaigns')


@shared_task(bind=True, max_retries=3, name='celery_app.tasks.campaigns.send_whatsapp_campaign')
def send_whatsapp_campaign(self, campaign_id: int):
    """
    Blast WhatsApp messages to all CampaignLeads for a given campaign.
    Errors stored per-lead in CampaignLead.error — never aborts the whole blast.
    """
    from campaigns.models import Campaign, CampaignLead
    from campaigns.whatsapp import WhatsAppService, WhatsAppError
    from django.utils import timezone as tz

    try:
        campaign = Campaign.objects.select_related('whatsapp_template').get(id=campaign_id)
    except Campaign.DoesNotExist:
        logger.error(f'[campaign_blast] Campaign {campaign_id} not found')
        return {'error': 'campaign not found'}

    service = WhatsAppService()
    leads   = CampaignLead.objects.filter(campaign=campaign, sent=False).select_related('lead')
    now     = tz.now()
    sent    = 0
    failed  = 0

    for cl in leads:
        phone = cl.lead.phone
        if not phone:
            continue

        # Determine message: whatsapp_template > template_name > message
        try:
            if campaign.whatsapp_template:
                msg = campaign.whatsapp_template.render(cl.lead)
                service.send_text(phone, msg)
            elif campaign.template_name:
                service.send_template(phone, campaign.template_name, [])
            else:
                service.send_text(phone, campaign.message)

            cl.sent    = True
            cl.sent_at = now
            cl.error   = ''
            sent += 1
        except WhatsAppError as e:
            cl.error = str(e)[:300]
            failed  += 1
            logger.error(f'[campaign_blast] Lead {cl.lead.name} ({phone}): {e}')
        finally:
            cl.save(update_fields=['sent', 'sent_at', 'error'])

    # Update campaign status
    if sent > 0:
        campaign.sent_at = now
        campaign.status  = 'sent'
        campaign.save(update_fields=['sent_at', 'status'])

    logger.info(f'[campaign_blast] campaign={campaign_id} sent={sent} failed={failed}')
    return {'campaign_id': campaign_id, 'sent': sent, 'failed': failed}


@shared_task(bind=True, max_retries=3, name='celery_app.tasks.campaigns.send_weekly_campaign_report')
def send_weekly_campaign_report(self):
    """Monday 08:00 — weekly campaign performance summary to managers."""
    from campaigns.models import Campaign
    from notifications.models import Notification
    from django.contrib.auth import get_user_model

    User     = get_user_model()
    today    = timezone.localdate()
    week_ago = today - timezone.timedelta(days=7)

    campaigns = Campaign.objects.filter(
        status__in=['active', 'sent', 'completed'],
        created_at__date__gte=week_ago,
    )

    managers = User.objects.filter(role__in=['owner', 'manager'], is_active=True)
    notifs   = []

    for manager in managers:
        lines = [f'📈 Weekly Campaign Report ({week_ago} → {today}):']
        for c in campaigns:
            lines.append(
                f'• {c.name}: {c.total_leads} leads | '
                f'{c.sent_count} sent | {c.roi_percent}% ROI'
            )
        if not campaigns:
            lines.append('No active campaigns this week.')

        notifs.append(Notification(
            recipient=manager,
            title='Weekly Campaign Report',
            body='\n'.join(lines),
            notif_type='general',
        ))

    if notifs:
        Notification.objects.bulk_create(notifs)

    return {'recipients': len(notifs)}


@shared_task(bind=True, max_retries=3, name='celery_app.tasks.campaigns.activate_due_campaigns')
def activate_due_campaigns(self):
    """Daily 00:02 — auto-activate campaigns whose scheduled_at has passed."""
    from campaigns.models import Campaign

    now   = timezone.now()
    count = Campaign.objects.filter(
        status='scheduled',
        scheduled_at__lte=now,
    ).update(status='active')

    logger.info(f'[activate_due_campaigns] {count} campaigns activated')
    return {'activated': count}


@shared_task(bind=True, max_retries=3, name='celery_app.tasks.campaigns.deactivate_expired_campaigns')
def deactivate_expired_campaigns(self):
    """Daily 00:03 — mark 'sent' campaigns older than 1 day as 'completed'."""
    from campaigns.models import Campaign
    from django.utils import timezone as tz

    yesterday = tz.now() - timezone.timedelta(days=1)
    count = Campaign.objects.filter(
        status='sent',
        sent_at__lt=yesterday,
    ).update(status='completed')

    logger.info(f'[deactivate_expired_campaigns] {count} campaigns completed')
    return {'completed': count}




@shared_task(bind=True, max_retries=3, name='celery_app.tasks.campaigns.send_special_day_messages')
def send_special_day_messages(self):
    """Daily 00:04 — send WhatsApp for today's special days (Onam, Eid, Christmas etc.)"""
    from campaigns.models import SpecialDayMessage
    from campaigns.whatsapp import WhatsAppService, WhatsAppError
    from django.contrib.auth import get_user_model
    from leads.models import Lead

    User    = get_user_model()
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
                except WhatsAppError as e:
                    logger.error(f'[special_day] Staff {user.full_name}: {e}')
                except KeyError as e:
                    logger.error(f'[special_day] Template placeholder error: {e}')

        if day.send_to_leads:
            for lead in Lead.objects.filter(
                stage__in=['interested', 'contacted']
            ).exclude(phone=''):
                try:
                    msg = day.message.format(name=lead.name, branch='')
                    service.send_text(lead.phone, msg)
                    sent += 1
                except WhatsAppError as e:
                    logger.error(f'[special_day] Lead {lead.name}: {e}')

    logger.info(f'[special_day_messages] {sent} messages sent on {today}')
    return {'sent': sent, 'date': str(today)}