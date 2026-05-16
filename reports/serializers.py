from rest_framework import serializers
from .models import Report, DailyReport


class ReportSerializer(serializers.ModelSerializer):
    branch_name  = serializers.CharField(source='branch.name', read_only=True)
    period_display = serializers.CharField(source='get_period_display', read_only=True)

    class Meta:
        model  = Report
        fields = ['id', 'branch', 'branch_name', 'period', 'period_display', 'date', 'data', 'generated_at']
        read_only_fields = ['id', 'generated_at']


class DailyReportSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source='branch.name', read_only=True)

    class Meta:
        model  = DailyReport
        fields = [
            'id', 'branch', 'branch_name', 'date',
            'total_leads', 'total_calls', 'total_sales',
            'total_revenue', 'generated_at',
        ]
        read_only_fields = ['id', 'generated_at']
