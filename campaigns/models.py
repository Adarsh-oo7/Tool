from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from cryptography.fernet import Fernet
import os


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
    CHANNEL_TYPE_CHOICES = [
        ('paid', 'Paid'),
        ('organic', 'Organic'),
        ('offline', 'Offline'),
        ('event', 'Event'),
    ]
    OBJECTIVE_CHOICES = [
        ('awareness', 'Awareness'),
        ('engagement', 'Engagement'),
        ('lead_generation', 'Lead Generation'),
        ('sales', 'Sales'),
        ('retention', 'Retention'),
        ('branding', 'Branding'),
    ]

    name          = models.CharField(max_length=200)
    branch        = models.ForeignKey(
                        'branches.Branch', on_delete=models.CASCADE,
                        related_name='campaigns')
    segment       = models.ForeignKey(
                        'branches.Segment', on_delete=models.SET_NULL,
                        null=True, blank=True, related_name='campaigns')
    campaign_type = models.CharField(max_length=20, choices=CAMPAIGN_TYPE_CHOICES, default='custom')
    channel_type  = models.CharField(max_length=20, choices=CHANNEL_TYPE_CHOICES, default='organic')
    objective     = models.CharField(max_length=20, choices=OBJECTIVE_CHOICES, default='awareness')
    tags          = models.JSONField(default=list, blank=True, help_text='Array of tags like festival, wedding, whatsapp')
    platforms     = models.JSONField(default=list, blank=True, help_text='Array of platforms like facebook_ads, instagram')

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


# Encryption helper for secure token storage
def get_encryption_key():
    """Get or generate encryption key for token storage."""
    key = os.environ.get('INTEGRATION_ENCRYPTION_KEY')
    if not key:
        # Generate a key and warn user to set it in production
        key = getattr(settings, 'INTEGRATION_ENCRYPTION_KEY', None)
        if not key:
            # Derive a consistent key from SECRET_KEY to prevent multi-process key mismatch
            secret_key = getattr(settings, 'SECRET_KEY', 'fallback_secret_key_12345')
            import hashlib
            import base64
            hashed = hashlib.sha256(secret_key.encode()).digest()
            key = base64.urlsafe_b64encode(hashed).decode()
    return key.encode() if isinstance(key, str) else key


def encrypt_token(token):
    """Encrypt a token for secure storage."""
    if not token:
        return None
    fernet = Fernet(get_encryption_key())
    return fernet.encrypt(token.encode()).decode()


def decrypt_token(encrypted_token):
    """Decrypt a token from storage."""
    if not encrypted_token:
        return None
    try:
        fernet = Fernet(get_encryption_key())
        return fernet.decrypt(encrypted_token.encode()).decode()
    except Exception as e:
        print(f"Decryption error (probably due to key mismatch): {e}")
        return None


class Integration(models.Model):
    """
    External platform integration for analytics and campaign tracking.
    READ-ONLY access only - no posting/publishing permissions.
    """
    PLATFORM_CHOICES = [
        ('google_analytics', 'Google Analytics'),
        ('google_ads', 'Google Ads'),
        ('facebook_ads', 'Facebook Ads'),
        ('instagram_insights', 'Instagram Insights'),
        ('youtube_analytics', 'YouTube Analytics'),
        ('whatsapp_business', 'WhatsApp Business Analytics'),
        ('mailchimp', 'Mailchimp'),
        ('brevo', 'Brevo'),
        ('sendgrid', 'SendGrid'),
    ]
    
    SYNC_STATUS_CHOICES = [
        ('idle', 'Idle'),
        ('syncing', 'Syncing'),
        ('success', 'Success'),
        ('error', 'Error'),
    ]

    platform = models.CharField(max_length=30, choices=PLATFORM_CHOICES)
    account_name = models.CharField(max_length=200, blank=True, help_text='Display name for the connected account')
    account_id = models.CharField(max_length=200, blank=True, help_text='Platform-specific account ID')
    
    # Encrypted tokens - never exposed to frontend
    access_token = models.TextField(blank=True, help_text='Encrypted OAuth access token')
    refresh_token = models.TextField(blank=True, help_text='Encrypted OAuth refresh token')
    token_expiry = models.DateTimeField(null=True, blank=True, help_text='Token expiration time')
    
    # Connection status
    is_connected = models.BooleanField(default=False)
    sync_enabled = models.BooleanField(default=True, help_text='Enable automatic analytics syncing')
    
    # Sync tracking
    last_sync = models.DateTimeField(null=True, blank=True)
    sync_status = models.CharField(max_length=20, choices=SYNC_STATUS_CHOICES, default='idle')
    sync_error = models.TextField(blank=True, help_text='Last sync error message')
    
    # Platform-specific settings (Page IDs, IG IDs, etc.)
    metadata = models.JSONField(default=dict, blank=True, help_text='Extra configuration and platform-specific IDs')
    
    # Branch association for multi-branch support
    branch = models.ForeignKey(
        'branches.Branch',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='integrations',
        help_text='Branch-specific integration (null = global)'
    )
    
    # Audit
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='integrations_created'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['platform']
        verbose_name = 'Integration'
        verbose_name_plural = 'Integrations'
        unique_together = ['platform', 'branch']

    def __str__(self):
        return f'{self.get_platform_display()} - {self.account_name or "Not Connected"}'

    def set_access_token(self, token):
        """Encrypt and set access token."""
        self.access_token = encrypt_token(token)

    def get_access_token(self):
        """Decrypt and return access token."""
        return decrypt_token(self.access_token) if self.access_token else None

    def set_refresh_token(self, token):
        """Encrypt and set refresh token."""
        self.refresh_token = encrypt_token(token)

    def get_refresh_token(self):
        """Decrypt and return refresh token."""
        return decrypt_token(self.refresh_token) if self.refresh_token else None

    def clean(self):
        """Validate that platform-specific requirements are met."""
        if self.is_connected and not self.access_token:
            raise ValidationError('Access token is required when integration is connected.')

    @property
    def is_token_expired(self):
        """Check if the access token is expired."""
        if not self.token_expiry:
            return False
        from django.utils import timezone
        return timezone.now() >= self.token_expiry

    @property
    def platform_display(self):
        """Get platform display name with icon."""
        icons = {
            'google_analytics': '📊',
            'google_ads': '📣',
            'facebook_ads': '📘',
            'instagram_insights': '📷',
            'youtube_analytics': '▶️',
            'whatsapp_business': '💬',
            'mailchimp': '📧',
            'brevo': '📧',
            'sendgrid': '📧',
        }
        icon = icons.get(self.platform, '🔗')
        return f'{icon} {self.get_platform_display()}'


class IntegrationAnalytics(models.Model):
    """
    Store synced analytics data from external platforms.
    This enables historical tracking and AI-ready data structure.
    """
    integration = models.ForeignKey(Integration, on_delete=models.CASCADE, related_name='analytics')
    date = models.DateField(help_text='Date of the analytics data')
    
    # Campaign metrics
    impressions = models.BigIntegerField(default=0)
    clicks = models.BigIntegerField(default=0)
    engagement = models.BigIntegerField(default=0)
    reach = models.BigIntegerField(default=0)
    
    # Conversion metrics
    conversions = models.IntegerField(default=0)
    leads = models.IntegerField(default=0)
    
    # Financial metrics
    spend = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Video metrics (for YouTube/Instagram)
    video_views = models.BigIntegerField(default=0)
    
    # Calculated metrics
    roi = models.DecimalField(max_digits=8, decimal_places=2, default=0, help_text='Return on Investment %')
    roas = models.DecimalField(max_digits=8, decimal_places=2, default=0, help_text='Return on Ad Spend')
    
    # Raw data for flexibility
    raw_data = models.JSONField(blank=True, null=True, help_text='Raw API response for debugging')
    
    synced_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date']
        unique_together = ['integration', 'date']
        verbose_name = 'Integration Analytics'
        verbose_name_plural = 'Integration Analytics'

    def __str__(self):
        return f'{self.integration.platform} - {self.date}'