from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
import math


class Geofence(models.Model):
    """Geofence areas for location-based marketing"""
    name = models.CharField(max_length=100)
    branch = models.ForeignKey(
        'branches.Branch', 
        on_delete=models.CASCADE, 
        related_name='geofences'
    )
    center_lat = models.DecimalField(max_digits=10, decimal_places=7)
    center_lng = models.DecimalField(max_digits=10, decimal_places=7)
    radius_meters = models.IntegerField(help_text="Radius in meters")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['branch', 'name']

    def __str__(self):
        return f'{self.name} - {self.branch.name} ({self.radius_meters}m)'

    def contains_point(self, lat, lng):
        """Check if a point is within the geofence using Haversine formula"""
        if not lat or not lng:
            return False
        
        # Convert to floats
        lat1, lng1 = float(self.center_lat), float(self.center_lng)
        lat2, lng2 = float(lat), float(lng)
        
        # Haversine formula
        R = 6371000  # Earth's radius in meters
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lng = math.radians(lng2 - lng1)
        
        a = (math.sin(delta_lat/2)**2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lng/2)**2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        distance = R * c
        return distance <= self.radius_meters


class LocationBasedCampaign(models.Model):
    """Campaigns triggered by customer location"""
    TRIGGER_TYPES = [
        ('enter', 'Enter Geofence'),
        ('exit', 'Exit Geofence'),
        ('dwell', 'Dwell Time'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('completed', 'Completed'),
    ]

    name = models.CharField(max_length=200)
    geofence = models.ForeignKey(Geofence, on_delete=models.CASCADE, related_name='campaigns')
    trigger_type = models.CharField(max_length=10, choices=TRIGGER_TYPES)
    message = models.TextField(help_text="WhatsApp message to send")
    delay_minutes = models.IntegerField(default=0, help_text="Delay in minutes before sending")
    max_sends_per_day = models.IntegerField(default=1, help_text="Maximum sends per customer per day")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    start_time = models.TimeField(null=True, blank=True, help_text="Campaign active start time")
    end_time = models.TimeField(null=True, blank=True, help_text="Campaign active end time")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='location_campaigns'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} ({self.geofence.name})'

    def is_active_now(self):
        """Check if campaign is currently active based on time constraints"""
        from django.utils import timezone
        
        if self.status != 'active':
            return False
        
        now = timezone.now().time()
        
        if self.start_time and now < self.start_time:
            return False
        
        if self.end_time and now > self.end_time:
            return False
        
        return True


class CustomerLocation(models.Model):
    """Track customer locations for targeting"""
    lead = models.ForeignKey('leads.Lead', on_delete=models.CASCADE, related_name='locations')
    lat = models.DecimalField(max_digits=10, decimal_places=7)
    lng = models.DecimalField(max_digits=10, decimal_places=7)
    accuracy = models.FloatField(null=True, blank=True, help_text="GPS accuracy in meters")
    timestamp = models.DateTimeField(auto_now_add=True)
    source = models.CharField(max_length=50, help_text="Source of location data")

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['lead', 'timestamp']),
            models.Index(fields=['timestamp']),
        ]

    def __str__(self):
        return f'{self.lead.name} location at {self.timestamp}'


class LocationTrigger(models.Model):
    """Record of location-based triggers"""
    TRIGGER_TYPES = [
        ('enter', 'Enter Geofence'),
        ('exit', 'Exit Geofence'),
        ('dwell', 'Dwell Time'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]

    lead = models.ForeignKey('leads.Lead', on_delete=models.CASCADE, related_name='location_triggers')
    campaign = models.ForeignKey(LocationBasedCampaign, on_delete=models.CASCADE, related_name='triggers')
    geofence = models.ForeignKey(Geofence, on_delete=models.CASCADE, related_name='triggers')
    trigger_type = models.CharField(max_length=10, choices=TRIGGER_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    location_at_trigger = models.JSONField(help_text="Location data at trigger time")
    scheduled_send_time = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['lead', 'created_at']),
            models.Index(fields=['status', 'scheduled_send_time']),
        ]

    def __str__(self):
        return f'{self.lead.name} - {self.trigger_type} ({self.status})'


class ProximityTarget(models.Model):
    """Target customers within proximity of branches"""
    branch = models.ForeignKey('branches.Branch', on_delete=models.CASCADE, related_name='proximity_targets')
    lead = models.ForeignKey('leads.Lead', on_delete=models.CASCADE, related_name='proximity_targets')
    distance_meters = models.FloatField()
    last_seen = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['branch', 'lead']
        ordering = ['distance_meters']
        indexes = [
            models.Index(fields=['branch', 'is_active', 'distance_meters']),
        ]

    def __str__(self):
        return f'{self.lead.name} - {self.distance_meters}m from {self.branch.name}'


class NearbyCustomerAlert(models.Model):
    """Alerts for nearby customers"""
    lead = models.ForeignKey('leads.Lead', on_delete=models.CASCADE, related_name='nearby_alerts')
    branch = models.ForeignKey('branches.Branch', on_delete=models.CASCADE, related_name='nearby_alerts')
    distance_meters = models.FloatField()
    message_sent = models.BooleanField(default=False)
    sent_at = models.DateTimeField(null=True, blank=True)
    campaign_used = models.ForeignKey(LocationBasedCampaign, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['branch', 'created_at']),
            models.Index(fields=['message_sent', 'created_at']),
        ]

    def __str__(self):
        return f'{self.lead.name} near {self.branch.name} ({self.distance_meters}m)'
