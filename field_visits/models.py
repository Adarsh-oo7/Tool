from django.db import models
from django.conf import settings


class FieldVisit(models.Model):
    STATUS_CHOICES = [
        ('active',    'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    lead       = models.ForeignKey('leads.Lead', on_delete=models.CASCADE, related_name='field_visits')
    staff      = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                   null=True, related_name='field_visits')
    branch     = models.ForeignKey('branches.Branch', on_delete=models.CASCADE, related_name='field_visits')
    start_lat  = models.DecimalField(max_digits=10, decimal_places=7)
    start_lng  = models.DecimalField(max_digits=10, decimal_places=7)
    status     = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at   = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-started_at']

    def __str__(self):
        return f'Visit by {self.staff} to {self.lead} [{self.status}]'


class GPSCheckIn(models.Model):
    visit     = models.ForeignKey(FieldVisit, on_delete=models.CASCADE, related_name='checkins')
    lat       = models.DecimalField(max_digits=10, decimal_places=7)
    lng       = models.DecimalField(max_digits=10, decimal_places=7)
    address   = models.CharField(max_length=300, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f'CheckIn @ {self.lat},{self.lng} on {self.timestamp}'


class VisitReport(models.Model):
    OUTCOME_CHOICES = [
        ('interested',     'Interested'),
        ('not_interested', 'Not Interested'),
        ('call_later',     'Call Later'),
        ('converted',      'Converted'),
    ]

    visit              = models.OneToOneField(FieldVisit, on_delete=models.CASCADE, related_name='report')
    outcome            = models.CharField(max_length=20, choices=OUTCOME_CHOICES)
    time_spent_minutes = models.IntegerField()
    notes              = models.TextField(blank=True)
    submitted_at       = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Report for visit {self.visit.id} — {self.outcome}'