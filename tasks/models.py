from django.db import models
from django.conf import settings


class Task(models.Model):
    PRIORITY_CHOICES = [
        ('low',    'Low'),
        ('medium', 'Medium'),
        ('high',   'High'),
    ]
    STATUS_CHOICES = [
        ('pending',   'Pending'),
        ('in_progress','In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    title       = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='tasks')
    created_by  = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='tasks_created')
    
    branch      = models.ForeignKey('branches.Branch', on_delete=models.CASCADE, related_name='tasks')
    lead        = models.ForeignKey('leads.Lead', on_delete=models.SET_NULL, null=True, blank=True, related_name='tasks')
    
    priority    = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    status      = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    due_date    = models.DateTimeField(null=True, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.assigned_to.full_name}"
