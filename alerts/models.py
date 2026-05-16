from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError
import json


class AlertType(models.Model):
    """Types of alerts that can be configured"""
    CATEGORY_CHOICES = [
        ('performance', 'Performance'),
        ('activity', 'Activity'),
        ('deadline', 'Deadline'),
        ('opportunity', 'Opportunity'),
        ('risk', 'Risk'),
        ('system', 'System'),
    ]
    
    SEVERITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES)
    description = models.TextField()
    template_message = models.TextField(help_text="Template for alert message with placeholders")
    default_enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['category', 'severity', 'name']

    def __str__(self):
        return f'{self.name} ({self.get_category_display()})'


class AlertRule(models.Model):
    """Rules for when alerts should be triggered"""
    TRIGGER_CONDITIONS = [
        ('gt', 'Greater Than'),
        ('lt', 'Less Than'),
        ('eq', 'Equal To'),
        ('gte', 'Greater Than or Equal'),
        ('lte', 'Less Than or Equal'),
        ('contains', 'Contains'),
        ('not_contains', 'Does Not Contain'),
        ('is_null', 'Is Null'),
        ('is_not_null', 'Is Not Null'),
    ]
    
    METRICS = [
        ('sales_count', 'Sales Count'),
        ('sales_revenue', 'Sales Revenue'),
        ('leads_count', 'Leads Count'),
        ('leads_converted', 'Leads Converted'),
        ('calls_made', 'Calls Made'),
        ('conversion_rate', 'Conversion Rate'),
        ('attendance_rate', 'Attendance Rate'),
        ('response_time', 'Response Time'),
        ('followup_overdue', 'Overdue Follow-ups'),
        ('inventory_low', 'Low Inventory'),
    ]
    
    alert_type = models.ForeignKey(AlertType, on_delete=models.CASCADE, related_name='rules')
    name = models.CharField(max_length=200)
    metric = models.CharField(max_length=50, choices=METRICS)
    condition = models.CharField(max_length=20, choices=TRIGGER_CONDITIONS)
    threshold_value = models.FloatField(null=True, blank=True)
    threshold_text = models.CharField(max_length=200, blank=True)
    time_period_hours = models.IntegerField(default=24, help_text="Time period in hours to check")
    is_active = models.BooleanField(default=True)
    target_roles = models.JSONField(default=list, help_text="Roles that should receive this alert")
    target_users = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name='alert_rules')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_alert_rules')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} - {self.alert_type.name}'

    def clean(self):
        """Validate rule configuration"""
        if self.condition in ['gt', 'lt', 'eq', 'gte', 'lte'] and self.threshold_value is None:
            raise ValidationError('Threshold value is required for numeric conditions')
        
        if self.condition in ['contains', 'not_contains'] and not self.threshold_text:
            raise ValidationError('Threshold text is required for text conditions')


class Alert(models.Model):
    """Individual alert instances"""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('acknowledged', 'Acknowledged'),
        ('resolved', 'Resolved'),
        ('dismissed', 'Dismissed'),
    ]
    
    rule = models.ForeignKey(AlertRule, on_delete=models.CASCADE, related_name='alerts')
    alert_type = models.ForeignKey(AlertType, on_delete=models.CASCADE, related_name='instances')
    title = models.CharField(max_length=200)
    message = models.TextField()
    severity = models.CharField(max_length=20)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    recipients = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='received_alerts')
    metadata = models.JSONField(default=dict, help_text="Additional alert data")
    triggered_at = models.DateTimeField(auto_now_add=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    acknowledged_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='acknowledged_alerts')
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='resolved_alerts')

    class Meta:
        ordering = ['-triggered_at']
        indexes = [
            models.Index(fields=['status', 'triggered_at']),
            models.Index(fields=['severity', 'status']),
        ]

    def __str__(self):
        return f'{self.title} ({self.get_status_display()})'

    def acknowledge(self, user):
        """Acknowledge the alert"""
        self.status = 'acknowledged'
        self.acknowledged_at = timezone.now()
        self.acknowledged_by = user
        self.save(update_fields=['status', 'acknowledged_at', 'acknowledged_by'])

    def resolve(self, user):
        """Resolve the alert"""
        self.status = 'resolved'
        self.resolved_at = timezone.now()
        self.resolved_by = user
        self.save(update_fields=['status', 'resolved_at', 'resolved_by'])

    def dismiss(self, user):
        """Dismiss the alert"""
        self.status = 'dismissed'
        self.resolved_at = timezone.now()
        self.resolved_by = user
        self.save(update_fields=['status', 'resolved_at', 'resolved_by'])


class AlertSubscription(models.Model):
    """User subscriptions to specific alert types"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='alert_subscriptions')
    alert_type = models.ForeignKey(AlertType, on_delete=models.CASCADE, related_name='subscribers')
    is_subscribed = models.BooleanField(default=True)
    notification_channels = models.JSONField(
        default=dict, 
        help_text="Channels: {'in_app': true, 'email': false, 'whatsapp': false}"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'alert_type']
        ordering = ['user', 'alert_type']

    def __str__(self):
        return f'{self.user.full_name} - {self.alert_type.name}'


class AlertDigest(models.Model):
    """Daily/weekly digest of alerts"""
    PERIOD_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='alert_digests')
    period = models.CharField(max_length=10, choices=PERIOD_CHOICES)
    digest_date = models.DateField()
    alert_count = models.IntegerField(default=0)
    critical_count = models.IntegerField(default=0)
    high_count = models.IntegerField(default=0)
    medium_count = models.IntegerField(default=0)
    low_count = models.IntegerField(default=0)
    summary = models.TextField(blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'period', 'digest_date']
        ordering = ['-digest_date', 'user']

    def __str__(self):
        return f'{self.user.full_name} - {self.get_period_display()} digest ({self.digest_date})'


class SmartSuggestion(models.Model):
    """AI-powered suggestions based on data analysis"""
    CATEGORY_CHOICES = [
        ('sales', 'Sales'),
        ('leads', 'Leads'),
        ('marketing', 'Marketing'),
        ('operations', 'Operations'),
        ('performance', 'Performance'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    title = models.CharField(max_length=200)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES)
    description = models.TextField()
    recommendation = models.TextField(help_text="Specific action to take")
    expected_impact = models.TextField(blank=True, help_text="Expected outcome if suggestion is followed")
    confidence_score = models.FloatField(help_text="AI confidence score (0-1)")
    data_insights = models.JSONField(help_text="Data that led to this suggestion")
    target_users = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='suggestions')
    is_implemented = models.BooleanField(default=False)
    implemented_at = models.DateTimeField(null=True, blank=True)
    implemented_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='implemented_suggestions')
    feedback_score = models.IntegerField(null=True, blank=True, help_text="User feedback 1-5")
    feedback_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.title} ({self.get_category_display()})'

    def implement(self, user):
        """Mark suggestion as implemented"""
        self.is_implemented = True
        self.implemented_at = timezone.now()
        self.implemented_by = user
        self.save(update_fields=['is_implemented', 'implemented_at', 'implemented_by'])
