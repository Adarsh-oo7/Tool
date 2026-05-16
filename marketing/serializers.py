from rest_framework import serializers
from .models import (
    Geofence, LocationBasedCampaign, CustomerLocation, LocationTrigger,
    ProximityTarget, NearbyCustomerAlert
)


class GeofenceSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source='branch.name', read_only=True)

    class Meta:
        model = Geofence
        fields = [
            'id', 'name', 'branch', 'branch_name', 'center_lat', 'center_lng',
            'radius_meters', 'is_active', 'created_at'
        ]


class LocationBasedCampaignSerializer(serializers.ModelSerializer):
    geofence_name = serializers.CharField(source='geofence.name', read_only=True)
    branch_name = serializers.CharField(source='geofence.branch.name', read_only=True)
    trigger_type_display = serializers.CharField(source='get_trigger_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_active_now = serializers.BooleanField(read_only=True)

    class Meta:
        model = LocationBasedCampaign
        fields = [
            'id', 'name', 'geofence', 'geofence_name', 'branch_name',
            'trigger_type', 'trigger_type_display', 'message', 'delay_minutes',
            'max_sends_per_day', 'status', 'status_display', 'start_time',
            'end_time', 'created_by', 'created_at', 'updated_at', 'is_active_now'
        ]


class CustomerLocationSerializer(serializers.ModelSerializer):
    lead_name = serializers.CharField(source='lead.name', read_only=True)
    lead_phone = serializers.CharField(source='lead.phone', read_only=True)

    class Meta:
        model = CustomerLocation
        fields = [
            'id', 'lead', 'lead_name', 'lead_phone', 'lat', 'lng',
            'accuracy', 'timestamp', 'source'
        ]


class LocationTriggerSerializer(serializers.ModelSerializer):
    lead_name = serializers.CharField(source='lead.name', read_only=True)
    campaign_name = serializers.CharField(source='campaign.name', read_only=True)
    geofence_name = serializers.CharField(source='geofence.name', read_only=True)
    trigger_type_display = serializers.CharField(source='get_trigger_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = LocationTrigger
        fields = [
            'id', 'lead', 'lead_name', 'campaign', 'campaign_name',
            'geofence', 'geofence_name', 'trigger_type', 'trigger_type_display',
            'status', 'status_display', 'location_at_trigger',
            'scheduled_send_time', 'sent_at', 'error_message', 'created_at'
        ]


class ProximityTargetSerializer(serializers.ModelSerializer):
    lead_name = serializers.CharField(source='lead.name', read_only=True)
    lead_phone = serializers.CharField(source='lead.phone', read_only=True)
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    distance_display = serializers.SerializerMethodField()

    class Meta:
        model = ProximityTarget
        fields = [
            'id', 'branch', 'branch_name', 'lead', 'lead_name', 'lead_phone',
            'distance_meters', 'distance_display', 'last_seen', 'is_active', 'created_at'
        ]

    def get_distance_display(self, obj):
        distance = obj.distance_meters
        if distance < 1000:
            return f"{int(distance)}m"
        else:
            return f"{distance/1000:.1f}km"


class NearbyCustomerAlertSerializer(serializers.ModelSerializer):
    lead_name = serializers.CharField(source='lead.name', read_only=True)
    lead_phone = serializers.CharField(source='lead.phone', read_only=True)
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    campaign_name = serializers.CharField(source='campaign_used.name', read_only=True)
    distance_display = serializers.SerializerMethodField()

    class Meta:
        model = NearbyCustomerAlert
        fields = [
            'id', 'lead', 'lead_name', 'lead_phone', 'branch', 'branch_name',
            'distance_meters', 'distance_display', 'message_sent', 'sent_at',
            'campaign_used', 'campaign_name', 'created_at'
        ]

    def get_distance_display(self, obj):
        distance = obj.distance_meters
        if distance < 1000:
            return f"{int(distance)}m"
        else:
            return f"{distance/1000:.1f}km"
