from django.db import models
from django.conf import settings


class Report(models.Model):
    """Enhanced flexible branch snapshot with comprehensive metrics."""
    PERIOD_CHOICES = [
        ('daily',   'Daily'),
        ('monthly', 'Monthly'),
        ('weekly',  'Weekly'),
    ]
    
    STATUS_CHOICES = [
        ('generating', 'Generating'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    branch  = models.ForeignKey('branches.Branch', on_delete=models.CASCADE, related_name='reports')
    period  = models.CharField(max_length=10, choices=PERIOD_CHOICES, default='daily')
    date    = models.DateField()
    data    = models.JSONField(default=dict, help_text="Comprehensive report data")
    status  = models.CharField(max_length=20, choices=STATUS_CHOICES, default='generating')
    error_message = models.TextField(blank=True, help_text="Error if report generation failed")
    generated_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True, help_text="When report was sent to recipients")
    recipients = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name='received_reports')

    class Meta:
        ordering        = ['-date']
        unique_together = ['branch', 'period', 'date']
        indexes         = [models.Index(fields=['branch', 'period', 'date']), models.Index(fields=['status', 'date'])]

    def __str__(self):
        return f'{self.branch.name} [{self.period}] {self.date} ({self.get_status_display()})'

    @property
    def summary_metrics(self):
        """Get key summary metrics from report data"""
        data = self.data or {}
        return {
            'total_leads': data.get('leads', {}).get('total', 0),
            'total_sales': data.get('sales', {}).get('count', 0),
            'total_revenue': data.get('sales', {}).get('revenue', 0),
            'total_weight': data.get('sales', {}).get('weight', 0),
            'total_calls': data.get('calls', {}).get('total', 0),
            'conversion_rate': data.get('leads', {}).get('conversion_rate', 0),
            'attendance_rate': data.get('attendance', {}).get('rate', 0),
        }


class DailyReport(models.Model):
    """Enhanced daily aggregated report with detailed metrics."""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('generating', 'Generating'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    branch        = models.ForeignKey('branches.Branch', on_delete=models.CASCADE, related_name='daily_reports')
    date          = models.DateField()
    total_leads   = models.IntegerField(default=0)
    total_calls   = models.IntegerField(default=0)
    total_sales   = models.IntegerField(default=0)
    total_revenue = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_weight  = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    weight_by_segment = models.JSONField(default=dict, blank=True, help_text="Breakdown of weight by segment")
    
    # Enhanced metrics
    leads_converted = models.IntegerField(default=0)
    calls_connected = models.IntegerField(default=0)
    attendance_present = models.IntegerField(default=0)
    attendance_total = models.IntegerField(default=0)
    
    # Performance metrics
    conversion_rate = models.FloatField(default=0.0, help_text="Lead conversion rate percentage")
    call_connect_rate = models.FloatField(default=0.0, help_text="Call connection rate percentage")
    attendance_rate = models.FloatField(default=0.0, help_text="Staff attendance rate percentage")
    
    # Status and metadata
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    error_message = models.TextField(blank=True)
    generated_at = models.DateTimeField(auto_now=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    sent_to = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name='daily_reports_sent')

    class Meta:
        unique_together = ['branch', 'date']
        ordering        = ['-date']
        indexes = [models.Index(fields=['branch', 'date', 'status'])]

    def __str__(self):
        return f'Daily Report {self.branch} — {self.date} ({self.get_status_display()})'


class ReportTemplate(models.Model):
    """Templates for different types of reports"""
    TEMPLATE_TYPES = [
        ('daily_eod', 'Daily EOD Report'),
        ('weekly_summary', 'Weekly Summary'),
        ('monthly_performance', 'Monthly Performance'),
        ('sales_analysis', 'Sales Analysis'),
        ('lead_analysis', 'Lead Analysis'),
        ('staff_performance', 'Staff Performance'),
    ]
    
    name = models.CharField(max_length=100)
    template_type = models.CharField(max_length=20, choices=TEMPLATE_TYPES)
    description = models.TextField(blank=True)
    content_template = models.TextField(help_text="Template with placeholders for dynamic content")
    is_active = models.BooleanField(default=True)
    auto_generate = models.BooleanField(default=True, help_text="Auto-generate this report")
    schedule_cron = models.CharField(max_length=100, blank=True, help_text="Cron expression for scheduling")
    recipients = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name='report_templates')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_report_templates')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['template_type', 'name']

    def __str__(self):
        return f'{self.name} ({self.get_template_type_display()})'


class ReportSchedule(models.Model):
    """Schedule for automatic report generation"""
    FREQUENCY_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('custom', 'Custom'),
    ]
    
    template = models.ForeignKey(ReportTemplate, on_delete=models.CASCADE, related_name='schedules')
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES)
    time_of_day = models.TimeField(help_text="Time to generate the report")
    day_of_week = models.IntegerField(null=True, blank=True, help_text="Day of week (0=Monday, 6=Sunday)")
    day_of_month = models.IntegerField(null=True, blank=True, help_text="Day of month")
    is_active = models.BooleanField(default=True)
    last_run = models.DateTimeField(null=True, blank=True)
    next_run = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['frequency', 'time_of_day']

    def __str__(self):
        return f'{self.template.name} - {self.get_frequency_display()} at {self.time_of_day}'


class ReportLog(models.Model):
    """Log of report generation attempts"""
    STATUS_CHOICES = [
        ('started', 'Started'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    template = models.ForeignKey(ReportTemplate, on_delete=models.CASCADE, related_name='logs', null=True, blank=True)
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='logs', null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.IntegerField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, help_text="Additional log data")
    triggered_by = models.CharField(max_length=50, default='system', help_text="What triggered this generation")

    class Meta:
        ordering = ['-started_at']
        indexes = [models.Index(fields=['status', 'started_at'])]

    def __str__(self):
        return f'{self.get_status_display()} - {self.started_at}'