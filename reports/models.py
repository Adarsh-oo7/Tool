from django.db import models


class DailyReport(models.Model):
    branch        = models.ForeignKey('branches.Branch', on_delete=models.CASCADE, related_name='daily_reports')
    date          = models.DateField()
    total_leads   = models.IntegerField(default=0)
    total_calls   = models.IntegerField(default=0)
    total_sales   = models.IntegerField(default=0)
    total_revenue = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    generated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['branch', 'date']
        ordering = ['-date']

    def __str__(self):
        return f'Report {self.branch} — {self.date}'