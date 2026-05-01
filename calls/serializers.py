from rest_framework import serializers
from .models import CallLog


class CallLogSerializer(serializers.ModelSerializer):
    staff_name      = serializers.CharField(source='staff.full_name', read_only=True)
    lead_name       = serializers.CharField(source='lead.name', read_only=True)
    outcome_display = serializers.CharField(source='get_outcome_display', read_only=True)

    class Meta:
        model  = CallLog
        fields = [
            'id', 'lead', 'lead_name', 'staff', 'staff_name',
            'outcome', 'outcome_display', 'duration_seconds',
            'notes', 'next_followup_date', 'created_at',
        ]
        read_only_fields = ['id', 'created_at', 'staff']
