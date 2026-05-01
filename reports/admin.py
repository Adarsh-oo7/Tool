from django.contrib import admin
from .models import DailyReport


@admin.register(DailyReport)
class DailyReportAdmin(admin.ModelAdmin):
    list_display    = ('branch', 'date', 'total_leads', 'total_calls', 'total_sales', 'total_revenue')
    list_filter     = ('branch', 'date')
    ordering        = ('-date',)
    readonly_fields = ('generated_at',)
