from django.contrib import admin
from .models import (
    Geofence, LocationBasedCampaign, CustomerLocation, LocationTrigger,
    ProximityTarget, NearbyCustomerAlert
)


@admin.register(Geofence)
class GeofenceAdmin(admin.ModelAdmin):
    list_display = ('name', 'branch', 'radius_meters', 'is_active', 'created_at')
    list_filter = ('branch', 'is_active')
    search_fields = ('name', 'branch__name')
    readonly_fields = ('created_at',)


@admin.register(LocationBasedCampaign)
class LocationBasedCampaignAdmin(admin.ModelAdmin):
    list_display = ('name', 'geofence', 'trigger_type', 'status', 'delay_minutes', 'created_at')
    list_filter = ('geofence', 'trigger_type', 'status')
    search_fields = ('name', 'geofence__name')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(CustomerLocation)
class CustomerLocationAdmin(admin.ModelAdmin):
    list_display = ('lead', 'lat', 'lng', 'source', 'timestamp')
    list_filter = ('source', 'timestamp')
    search_fields = ('lead__name', 'lead__phone')
    readonly_fields = ('timestamp',)


@admin.register(LocationTrigger)
class LocationTriggerAdmin(admin.ModelAdmin):
    list_display = ('lead', 'campaign', 'trigger_type', 'status', 'scheduled_send_time', 'sent_at')
    list_filter = ('trigger_type', 'status', 'created_at')
    search_fields = ('lead__name', 'campaign__name')
    readonly_fields = ('created_at',)


@admin.register(ProximityTarget)
class ProximityTargetAdmin(admin.ModelAdmin):
    list_display = ('lead', 'branch', 'distance_meters', 'is_active', 'last_seen')
    list_filter = ('branch', 'is_active')
    search_fields = ('lead__name', 'branch__name')
    readonly_fields = ('created_at',)


@admin.register(NearbyCustomerAlert)
class NearbyCustomerAlertAdmin(admin.ModelAdmin):
    list_display = ('lead', 'branch', 'distance_meters', 'message_sent', 'sent_at')
    list_filter = ('branch', 'message_sent', 'created_at')
    search_fields = ('lead__name', 'branch__name')
    readonly_fields = ('created_at',)
