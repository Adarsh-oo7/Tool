from django.db import models
from django.conf import settings


class Campaign(models.Model):
    CAMPAIGN_TYPE_CHOICES = [
        ('festival',  'Festival Offer'),
        ('bridal',    'Bridal Campaign'),
        ('gold_rate', 'Gold Rate Alert'),
        ('recovery',  'Lost Lead Recovery'),
        ('followup',  'Follow-up Reminder'),
        ('custom',    'Custom'),
    ]
    STATUS_CHOICES = [
        ('draft',     'Draft'),
        ('scheduled', 'Scheduled'),
        ('sent',      'Sent'),
        ('completed', 'Completed'),
    ]

    name          = models.CharField(max_length=200)
    branch        = models.ForeignKey('branches.Branch', on_delete=models.CASCADE, related_name='campaigns')
    segment       = models.ForeignKey('branches.Segment', on_delete=models.SET_NULL, null=True, blank=True)
    campaign_type = models.CharField(max_length=20, choices=CAMPAIGN_TYPE_CHOICES, default='custom')
    template_name = models.CharField(max_length=100, help_text='Meta pre-approved WhatsApp template name')
    message       = models.TextField(blank=True, help_text='Dynamic message content / params')
    status        = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    scheduled_at  = models.DateTimeField(null=True, blank=True)
    created_by    = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                      null=True, related_name='campaigns_created')
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} ({self.status})'


class CampaignLead(models.Model):
    campaign  = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='campaign_leads')
    lead      = models.ForeignKey('leads.Lead', on_delete=models.CASCADE, related_name='campaign_entries')
    sent      = models.BooleanField(default=False)
    delivered = models.BooleanField(default=False)
    converted = models.BooleanField(default=False)
    sent_at   = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ['campaign', 'lead']

    def __str__(self):
        return f'{self.campaign.name} → {self.lead.name}'