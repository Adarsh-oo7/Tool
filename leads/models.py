from django.db import models
from django.conf import settings


class Lead(models.Model):
    SOURCE_CHOICES = [
        ('walkin',    'Walk-in'),
        ('instagram', 'Instagram'),
        ('facebook',  'Facebook'),
        ('website',   'Website'),
        ('referral',  'Referral'),
        ('whatsapp',  'WhatsApp'),
        ('other',     'Other'),
    ]
    STAGE_CHOICES = [
        ('new',       'New'),
        ('contacted', 'Contacted'),
        ('interested','Interested'),
        ('scheduled', 'Visit Scheduled'),
        ('converted', 'Converted'),
        ('lost',      'Lost'),
    ]

    # Core identity
    name    = models.CharField(max_length=200)
    phone   = models.CharField(max_length=15)
    email   = models.EmailField(blank=True, null=True)
    age     = models.PositiveIntegerField(null=True, blank=True)
    gender  = models.CharField(max_length=10, blank=True,
                               choices=[('male','Male'),('female','Female'),('other','Other')])

    # Source & classification
    source  = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='walkin')
    branch  = models.ForeignKey('branches.Branch',  on_delete=models.CASCADE, related_name='leads')
    segment = models.ForeignKey('branches.Segment', on_delete=models.SET_NULL, null=True, blank=True)

    # Assignment & stage
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                    null=True, blank=True, related_name='assigned_leads')
    stage       = models.CharField(max_length=20, choices=STAGE_CHOICES, default='new')

    # Interest details
    budget          = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    occasion        = models.CharField(max_length=100, blank=True)   # wedding, gift, etc.
    product_interest= models.TextField(blank=True)                   # what they liked
    notes           = models.TextField(blank=True)

    # AI scoring (0-100)
    score           = models.IntegerField(default=0)
    is_hot          = models.BooleanField(default=False)

    # Campaign linkage
    campaign        = models.ForeignKey('campaigns.Campaign', null=True, blank=True,
                                        on_delete=models.SET_NULL, related_name='leads')

    # Timestamps
    created_by  = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                    null=True, related_name='created_leads')
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes  = [
            models.Index(fields=['branch', 'stage']),
            models.Index(fields=['assigned_to', 'stage']),
            models.Index(fields=['phone']),
        ]

    def __str__(self): return f'{self.name} ({self.stage})'


class FollowUp(models.Model):
    lead           = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='followups')
    scheduled_date = models.DateTimeField()
    note           = models.TextField(blank=True)
    completed      = models.BooleanField(default=False)
    completed_at   = models.DateTimeField(null=True, blank=True)
    created_by     = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                       null=True, related_name='followups_created')
    created_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['scheduled_date']

    def __str__(self): return f'Follow-up for {self.lead.name} on {self.scheduled_date}'


class LeadActivity(models.Model):
    """Audit log for every status change or note on a lead."""
    lead       = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='activities')
    actor      = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    action     = models.CharField(max_length=100)  # 'stage_changed', 'note_added', etc.
    detail     = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']