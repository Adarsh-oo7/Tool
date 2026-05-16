from django.db import models
from django.conf import settings


class Notification(models.Model):
    TYPE_CHOICES = [
        ('followup',   'Follow-up Reminder'),
        ('hot_lead',   'Hot Lead Alert'),
        ('attendance', 'Attendance Approval'),
        ('campaign',   'Campaign Update'),
        ('announcement', 'Announcement'),
        ('birthday',   'Birthday Wish'),
        ('anniversary', 'Work Anniversary'),
        ('general',    'General'),
    ]

    recipient    = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                   related_name='notifications', null=True, blank=True)
    sender       = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                   related_name='sent_notifications', null=True, blank=True)
    notif_type   = models.CharField(max_length=20, choices=TYPE_CHOICES, default='general')
    title        = models.CharField(max_length=200)
    body         = models.TextField()
    image        = models.ImageField(upload_to='notifications/', null=True, blank=True)
    is_broadcast = models.BooleanField(default=False)
    is_read      = models.BooleanField(default=False)
    data         = models.JSONField(default=dict, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.title} → {self.recipient}'