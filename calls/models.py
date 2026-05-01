from django.db import models
from django.conf import settings


class CallLog(models.Model):
    OUTCOME_CHOICES = [
        ('no_answer',      'No Answer'),
        ('interested',     'Interested'),
        ('not_interested', 'Not Interested'),
        ('call_later',     'Call Later'),
        ('converted',      'Converted'),
    ]

    lead             = models.ForeignKey('leads.Lead', on_delete=models.CASCADE, related_name='call_logs')
    staff            = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                         null=True, related_name='call_logs')
    outcome          = models.CharField(max_length=20, choices=OUTCOME_CHOICES)
    duration_seconds = models.IntegerField(null=True, blank=True)
    notes            = models.TextField(blank=True)
    next_followup_date = models.DateField(null=True, blank=True)
    created_at       = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes  = [
            models.Index(fields=['staff', 'created_at']),
            models.Index(fields=['lead']),
        ]

    def __str__(self):
        return f'Call by {self.staff} on {self.lead} — {self.outcome}'