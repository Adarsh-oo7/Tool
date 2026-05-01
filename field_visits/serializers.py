from rest_framework import serializers
from .models import FieldVisit, GPSCheckIn, VisitReport


class GPSCheckInSerializer(serializers.ModelSerializer):
    class Meta:
        model  = GPSCheckIn
        fields = ['id', 'visit', 'lat', 'lng', 'address', 'timestamp']
        read_only_fields = ['id', 'timestamp']


class VisitReportSerializer(serializers.ModelSerializer):
    outcome_display = serializers.CharField(source='get_outcome_display', read_only=True)

    class Meta:
        model  = VisitReport
        fields = ['id', 'visit', 'outcome', 'outcome_display', 'time_spent_minutes', 'notes', 'submitted_at']
        read_only_fields = ['id', 'submitted_at']


class FieldVisitSerializer(serializers.ModelSerializer):
    checkins        = GPSCheckInSerializer(many=True, read_only=True)
    report          = VisitReportSerializer(read_only=True)
    staff_name      = serializers.CharField(source='staff.full_name', read_only=True)
    lead_name       = serializers.CharField(source='lead.name', read_only=True)
    branch_name     = serializers.CharField(source='branch.name', read_only=True)
    status_display  = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model  = FieldVisit
        fields = [
            'id', 'lead', 'lead_name', 'staff', 'staff_name',
            'branch', 'branch_name', 'start_lat', 'start_lng',
            'status', 'status_display', 'started_at', 'ended_at',
            'checkins', 'report',
        ]
        read_only_fields = ['id', 'started_at', 'staff', 'branch', 'status']  # ← add branch, status