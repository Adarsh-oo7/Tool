from rest_framework import serializers
from .models import DailyReport


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
