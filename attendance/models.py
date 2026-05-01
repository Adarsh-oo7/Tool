from django.db import models
from django.conf import settings


class Attendance(models.Model):
    STATUS_CHOICES = [
        ('pending',  'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    user          = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                      related_name='attendance_records')
    branch = models.ForeignKey(
    'branches.Branch',
    null=True, blank=True,          # ← add these
    on_delete=models.SET_NULL,      # ← change CASCADE to SET_NULL
    related_name='attendance_records'
)
    date          = models.DateField(auto_now_add=True)
    check_in_lat  = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    check_in_lng  = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    photo         = models.ImageField(upload_to='attendance/photos/', null=True, blank=True)
    status        = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    approved_by   = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                      on_delete=models.SET_NULL, related_name='approvals')
    notes         = models.TextField(blank=True)
    checked_in_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'date']
        ordering        = ['-checked_in_at']

    def __str__(self):
        return f'{self.user.full_name} — {self.date} [{self.status}]'
