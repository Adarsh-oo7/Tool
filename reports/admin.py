from django.contrib import admin
from .models import Report, DailyReport


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display    = ('branch', 'period', 'date', 'generated_at')
    list_filter     = ('period', 'branch')
    ordering        = ('-date',)
    readonly_fields = ('generated_at',)


@admin.register(DailyReport)
class DailyReportAdmin(admin.ModelAdmin):
    list_display    = ('branch', 'date', 'total_leads', 'total_calls', 'total_sales', 'total_revenue')
    list_filter     = ('branch', 'date')
    ordering        = ('-date',)
    readonly_fields = ('generated_at',)
