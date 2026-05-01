from django.db import models
from django.conf import settings


class WhatsAppTemplate(models.Model):
    """
    Reusable WhatsApp message templates.
    Supports placeholders: {name}, {date}, {branch}, {role}
    Used for birthday, anniversary, special days, and campaign blasts.
    """
    TRIGGER_CHOICES = [
        ('birthday',    'Birthday Wish'),
        ('anniversary', 'Work Anniversary'),
        ('special_day', 'Special Day / Festival'),
        ('campaign',    'Campaign Blast'),
        ('manual',      'Manual / On-demand'),
    ]

    name       = models.CharField(max_length=100)
    trigger    = models.CharField(max_length=20, choices=TRIGGER_CHOICES)
    message    = models.TextField(
        help_text='Placeholders: {name}, {date}, {branch}, {role}'
    )
    is_active  = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name='whatsapp_templates',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['trigger', 'name']

    def __str__(self):
        return f'[{self.get_trigger_display()}] {self.name}'

    def render(self, user) -> str:
        """Fill placeholders with actual user data."""
        from django.utils import timezone
        return self.message.format(
            name=user.full_name,
            date=str(timezone.localdate()),
            branch=user.branch.name if user.branch else '',
            role=user.display_role if hasattr(user, 'display_role') else user.get_role_display(),
        )


class Campaign(models.Model):
    CAMPAIGN_TYPE_CHOICES = [
        ('festival',    'Festival Offer'),
        ('bridal',      'Bridal Campaign'),
        ('gold_rate',   'Gold Rate Alert'),
        ('recovery',    'Lost Lead Recovery'),
        ('followup',    'Follow-up Reminder'),
        ('birthday',    'Birthday Wish'),
        ('anniversary', 'Work Anniversary'),
        ('special_day', 'Special Day'),
        ('custom',      'Custom'),
    ]
    STATUS_CHOICES = [
        ('draft',     'Draft'),
        ('scheduled', 'Scheduled'),
        ('active',    'Active'),
        ('sent',      'Sent'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    name          = models.CharField(max_length=200)
    branch        = models.ForeignKey(
                        'branches.Branch', on_delete=models.CASCADE,
                        related_name='campaigns')
    segment       = models.ForeignKey(
                        'branches.Segment', on_delete=models.SET_NULL,
                        null=True, blank=True, related_name='campaigns')
    campaign_type = models.CharField(max_length=20, choices=CAMPAIGN_TYPE_CHOICES, default='custom')

    # WhatsApp delivery
    whatsapp_template = models.ForeignKey(
                            WhatsAppTemplate, on_delete=models.SET_NULL,
                            null=True, blank=True, related_name='campaigns',
                            help_text='Reusable template with placeholders')
    template_name = models.CharField(
                        max_length=100, blank=True,
                        help_text='Meta pre-approved WhatsApp template name (overrides whatsapp_template)')
    message       = models.TextField(blank=True, help_text='Dynamic message content / params')

    status        = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    scheduled_at  = models.DateTimeField(null=True, blank=True)
    sent_at       = models.DateTimeField(null=True, blank=True)

    created_by    = models.ForeignKey(
                        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                        null=True, related_name='campaigns_created')
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} ({self.get_status_display()})'

    @property
    def total_leads(self):
        return self.campaign_leads.count()

    @property
    def sent_count(self):
        return self.campaign_leads.filter(sent=True).count()

    @property
    def converted_count(self):
        return self.campaign_leads.filter(converted=True).count()

    @property
    def roi_percent(self):
        total = self.total_leads
        if not total:
            return 0
        return round((self.converted_count / total) * 100, 1)


class CampaignLead(models.Model):
    """Tracks per-lead delivery and conversion for a campaign."""
    campaign  = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='campaign_leads')
    lead      = models.ForeignKey('leads.Lead', on_delete=models.CASCADE, related_name='campaign_entries')
    sent      = models.BooleanField(default=False)
    delivered = models.BooleanField(default=False)
    read      = models.BooleanField(default=False)
    converted = models.BooleanField(default=False)
    sent_at   = models.DateTimeField(null=True, blank=True)
    error     = models.CharField(max_length=300, blank=True)  # store send error if any

    class Meta:
        unique_together = ['campaign', 'lead']
        ordering        = ['-sent_at']

    def __str__(self):
        return f'{self.campaign.name} → {self.lead.name}'


class SpecialDayMessage(models.Model):
    """
    Admin-defined special days (festivals, holidays) with
    a WhatsApp message to send to all active staff/leads.
    """
    name          = models.CharField(max_length=100, help_text='e.g. Onam, Christmas, Eid')
    date          = models.DateField(help_text='Date this message fires every year')
    message       = models.TextField(help_text='Placeholders: {name}, {branch}')
    send_to_staff = models.BooleanField(default=True,  help_text='Send to all active staff')
    send_to_leads = models.BooleanField(default=False, help_text='Send to active leads')
    is_active     = models.BooleanField(default=True)
    created_by    = models.ForeignKey(
                        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                        null=True, blank=True, related_name='special_day_messages')
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['date']

    def __str__(self):
        return f'{self.name} ({self.date.strftime("%d %b")})'