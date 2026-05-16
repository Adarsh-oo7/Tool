from rest_framework import serializers
from .models import CallLog


class CallLogSerializer(serializers.ModelSerializer):
    staff_name      = serializers.SerializerMethodField()
    lead_name       = serializers.CharField(source='lead.name', read_only=True)
    lead_phone      = serializers.CharField(source='lead.phone', read_only=True)
    outcome_display = serializers.CharField(source='get_outcome_display', read_only=True)

    def get_staff_name(self, obj):
        return obj.staff.full_name if obj.staff else "Deleted Staff"

    class Meta:
        model  = CallLog
        fields = [
            'id', 'lead', 'lead_name', 'lead_phone', 'staff', 'staff_name',
            'outcome', 'outcome_display', 'needs_field_visit', 
            'occasion', 'duration_seconds', 'notes', 'next_followup_date', 
            'created_at',
        ]
        read_only_fields = ['id', 'created_at', 'staff']
