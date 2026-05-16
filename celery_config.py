import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault(
    'DJANGO_SETTINGS_MODULE',
    'bindu_jewellery_backend.settings.development'
)

app = Celery('bindu_jewellery_backend')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks(['celery_app.tasks'])

app.conf.beat_schedule = {

    # ── Leads ─────────────────────────────────────────────────────────────────
    'daily-followup-reminders': {
        'task':     'celery_app.tasks.leads.send_followup_reminders',
        'schedule': crontab(hour=9, minute=0),          # 9:00 AM daily
    },
    'mark-overdue-leads': {
        'task':     'celery_app.tasks.leads.mark_overdue_leads',
        'schedule': crontab(minute='*/30'),              # every 30 mins
    },
    'daily-eod-report': {
        'task':     'celery_app.tasks.leads.send_eod_report',
        'schedule': crontab(hour=19, minute=0),          # 7:00 PM daily
    },

    # ── Staff WhatsApp automation ─────────────────────────────────────────────
    'send-birthday-wishes': {
        'task':     'celery_app.tasks.leads.send_birthday_wishes',
        'schedule': crontab(hour=0, minute=0),           # midnight daily
    },
    'send-anniversary-wishes': {
        'task':     'celery_app.tasks.leads.send_anniversary_wishes',
        'schedule': crontab(hour=0, minute=1),           # 12:01 AM daily
    },

    # ── Campaigns ─────────────────────────────────────────────────────────────
    'weekly-campaign-report': {
        'task':     'celery_app.tasks.campaigns.send_weekly_campaign_report',
        'schedule': crontab(day_of_week=1, hour=8, minute=0),  # Monday 8 AM
    },
    'activate-scheduled-campaigns': {
        'task':     'celery_app.tasks.campaigns.activate_due_campaigns',
        'schedule': crontab(hour=0, minute=2),           # 12:02 AM daily
    },
    'deactivate-expired-campaigns': {
        'task':     'celery_app.tasks.campaigns.deactivate_expired_campaigns',
        'schedule': crontab(hour=0, minute=3),           # 12:03 AM daily
    },
    'send-special-day-messages': {
        'task':     'celery_app.tasks.campaigns.send_special_day_messages',
        'schedule': crontab(hour=0, minute=4),           # 12:04 AM daily
    },

}

app.conf.timezone = 'Asia/Kolkata'


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Health check — celery -A bindu_jewellery_backend call debug_task"""
    print(f'[Celery] Worker alive. Request: {self.request!r}')