from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
import math


class FieldVisit(models.Model):
    STATUS_CHOICES = [
        ('active',    'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    lead       = models.ForeignKey('leads.Lead', on_delete=models.CASCADE, related_name='field_visits')
    staff      = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                   null=True, related_name='field_visits')
    branch     = models.ForeignKey('branches.Branch', null=True, blank=True,
                                   on_delete=models.SET_NULL, related_name='field_visits')
    
    # GPS tracking
    start_lat  = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    start_lng  = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    end_lat    = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    end_lng    = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    
    # Visit details
    status     = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at   = models.DateTimeField(null=True, blank=True)
    distance_km = models.FloatField(null=True, blank=True, help_text="Total distance traveled in km")
    duration_minutes = models.IntegerField(null=True, blank=True, help_text="Visit duration in minutes")

    class Meta:
        ordering = ['-started_at']

    def __str__(self):
        return f'Visit by {self.staff} to {self.lead} [{self.status}]'

    def clean(self):
        """Validate GPS coordinates"""
        if self.start_lat and not (-90 <= float(self.start_lat) <= 90):
            raise ValidationError('Start latitude must be between -90 and 90')
        if self.start_lng and not (-180 <= float(self.start_lng) <= 180):
            raise ValidationError('Start longitude must be between -180 and 180')
        if self.end_lat and not (-90 <= float(self.end_lat) <= 90):
            raise ValidationError('End latitude must be between -90 and 90')
        if self.end_lng and not (-180 <= float(self.end_lng) <= 180):
            raise ValidationError('End longitude must be between -180 and 180')


    def calculate_distance(self):
        """Calculate distance between start and end points in kilometers"""
        if not all([self.start_lat, self.start_lng, self.end_lat, self.end_lng]):
            return None
        
        # Haversine formula
        lat1, lon1 = float(self.start_lat), float(self.start_lng)
        lat2, lon2 = float(self.end_lat), float(self.end_lng)
        
        R = 6371  # Earth's radius in kilometers
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = (math.sin(delta_lat/2)**2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        distance = R * c
        self.distance_km = round(distance, 2)
        return self.distance_km

    def calculate_duration(self):
        """Calculate visit duration in minutes"""
        if not self.started_at or not self.ended_at:
            return None
        
        duration = self.ended_at - self.started_at
        self.duration_minutes = int(duration.total_seconds() / 60)
        return self.duration_minutes

    def save(self, *args, **kwargs):
        # Auto-set branch from staff if not specified
        if not self.branch and self.staff and self.staff.branch:
            self.branch = self.staff.branch
        
        # Calculate distance and duration if end coordinates are set
        if self.end_lat and self.end_lng:
            self.calculate_distance()
        
        if self.ended_at:
            self.calculate_duration()
        
        super().save(*args, **kwargs)

    @property
    def is_active(self):
        return self.status == 'active' and not self.ended_at

    @property
    def latest_location(self):
        """Get the latest GPS check-in location"""
        latest = self.checkins.order_by('-timestamp').first()
        if latest:
            return {'lat': float(latest.lat), 'lng': float(latest.lng), 'timestamp': latest.timestamp}
        return None


class LocationTracking(models.Model):
    """Real-time location tracking for field staff"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='location_updates')
    latitude = models.DecimalField(max_digits=10, decimal_places=7)
    longitude = models.DecimalField(max_digits=10, decimal_places=7)
    accuracy = models.FloatField(null=True, blank=True)  # GPS accuracy in meters
    timestamp = models.DateTimeField(auto_now_add=True)
    field_visit = models.ForeignKey('FieldVisit', on_delete=models.CASCADE, null=True, blank=True, related_name='location_updates')
    is_active = models.BooleanField(default=True)  # Whether this is the current location
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['field_visit', '-timestamp']),
        ]
    
    def __str__(self):
        return f'Location for {self.user.full_name} at {self.timestamp}'


class GPSCheckIn(models.Model):
    visit     = models.ForeignKey(FieldVisit, on_delete=models.CASCADE, related_name='checkins')
    lat       = models.DecimalField(max_digits=10, decimal_places=7)
    lng       = models.DecimalField(max_digits=10, decimal_places=7)
    address   = models.CharField(max_length=300, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f'CheckIn @ {self.lat},{self.lng} on {self.timestamp}'


class VisitReport(models.Model):
    OUTCOME_CHOICES = [
        ('interested',     'Interested'),
        ('not_interested', 'Not Interested'),
        ('call_later',     'Call Later'),
        ('converted',      'Converted'),
    ]

    visit              = models.OneToOneField(FieldVisit, on_delete=models.CASCADE, related_name='report')
    outcome            = models.CharField(max_length=20, choices=OUTCOME_CHOICES)
    time_spent_minutes = models.IntegerField()
    notes              = models.TextField(blank=True)
    submitted_at       = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Report for visit {self.visit.id} — {self.outcome}'