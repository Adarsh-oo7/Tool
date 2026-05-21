from rest_framework import serializers
from .models import FieldVisit, GPSCheckIn, VisitReport, LocationTracking


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


class LocationTrackingSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    user_role = serializers.CharField(source='user.role', read_only=True)
    
    class Meta:
        model = LocationTracking
        fields = ['id', 'user', 'user_name', 'user_role', 'latitude', 'longitude', 
                  'accuracy', 'timestamp', 'field_visit', 'is_active']
        read_only_fields = ['id', 'user', 'timestamp']


class FieldVisitSerializer(serializers.ModelSerializer):
    checkins        = GPSCheckInSerializer(many=True, read_only=True)
    location_updates = LocationTrackingSerializer(many=True, read_only=True)
    report          = VisitReportSerializer(read_only=True)
    staff_name      = serializers.CharField(source='staff.full_name', read_only=True)
    staff_phone     = serializers.CharField(source='staff.phone', read_only=True)
    lead_name       = serializers.CharField(source='lead.name', read_only=True)
    lead_phone      = serializers.CharField(source='lead.phone', read_only=True)
    lead_lat        = serializers.DecimalField(source='lead.lat', max_digits=10, decimal_places=7, read_only=True)
    lead_lng        = serializers.DecimalField(source='lead.lng', max_digits=10, decimal_places=7, read_only=True)
    branch_name     = serializers.CharField(source='branch.name', read_only=True)
    status_display  = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model  = FieldVisit
        fields = ['id', 'lead', 'staff', 'branch', 'status', 'status_display',
                  'started_at', 'scheduled_date', 'ended_at', 'distance_km', 'duration_minutes',
                  'notes', 'checkins', 'location_updates', 'report', 
                  'staff_name', 'staff_phone', 'lead_name', 'lead_phone',
                  'lead_lat', 'lead_lng', 'branch_name', 'start_lat', 'start_lng', 'end_lat', 'end_lng']
        read_only_fields = ['id', 'started_at', 'ended_at', 'distance_km', 'duration_minutes']