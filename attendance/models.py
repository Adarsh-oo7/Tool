from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
import math


class Attendance(models.Model):
    STATUS_CHOICES = [
        ('present',  'Present'),
        ('late',     'Late'),
        ('absent',   'Absent'),
        ('pending',  'Pending Approval'),
        ('rejected', 'Rejected'),
    ]

    CHECK_IN_TYPE_CHOICES = [
        ('gps',      'GPS Check-in'),
        ('manual',   'Manual Check-in'),
        ('photo',    'Photo Check-in'),
    ]

    user          = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                      related_name='attendance_records')
    branch        = models.ForeignKey('branches.Branch', null=True, blank=True,
                                      on_delete=models.SET_NULL, related_name='attendance_records')
    date          = models.DateField()
    check_in_type = models.CharField(max_length=10, choices=CHECK_IN_TYPE_CHOICES, default='gps')
    check_in_lat  = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    check_in_lng  = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    check_in_time = models.DateTimeField(null=True, blank=True)
    check_out_time= models.DateTimeField(null=True, blank=True)
    check_out_lat = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    check_out_lng = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    photo         = models.ImageField(upload_to='attendance/photos/', null=True, blank=True)
    status        = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    approved_by   = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                      on_delete=models.SET_NULL, related_name='approvals')
    notes         = models.TextField(blank=True)
    distance_from_branch = models.FloatField(null=True, blank=True, help_text="Distance in meters from branch location")
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'date']
        ordering        = ['-date']

    def __str__(self):
        return f'{self.user.full_name} — {self.date} [{self.get_status_display()}]'

    def get_total_break_time(self):
        """Calculate total break time in minutes"""
        total_seconds = sum(
            (b.end_time - b.start_time).total_seconds() 
            for b in self.breaks.filter(end_time__isnull=False)
        )
        return round(total_seconds / 60, 2)

    def get_net_work_time(self):
        """Calculate net work time (check-out - check-in - breaks)"""
        if not self.check_in_time or not self.check_out_time:
            return None
        
        work_seconds = (self.check_out_time - self.check_in_time).total_seconds()
        break_seconds = sum(
            (b.end_time - b.start_time).total_seconds() 
            for b in self.breaks.filter(end_time__isnull=False)
        )
        net_seconds = work_seconds - break_seconds
        return round(net_seconds / 3600, 2) # Return in hours

    def clean(self):
        """Validate GPS coordinates and check-in logic"""
        if self.check_in_type == 'gps':
            if not self.check_in_lat or not self.check_in_lng:
                raise ValidationError('GPS coordinates are required for GPS check-in')
            
            if not self.branch:
                raise ValidationError('Branch must be specified for GPS check-in')
            
            # Validate coordinate ranges
            if not (-90 <= float(self.check_in_lat) <= 90):
                raise ValidationError('Latitude must be between -90 and 90')
            if not (-180 <= float(self.check_in_lng) <= 180):
                raise ValidationError('Longitude must be between -180 and 180')

    def calculate_distance_from_branch(self):
        """Calculate distance from branch in meters"""
        if not self.branch or not self.check_in_lat or not self.check_in_lng:
            return None
        
        if not self.branch.lat or not self.branch.lng:
            return None
        
        # Haversine formula to calculate distance
        lat1, lon1 = float(self.branch.lat), float(self.branch.lng)
        lat2, lon2 = float(self.check_in_lat), float(self.check_in_lng)
        
        R = 6371000  # Earth's radius in meters
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = (math.sin(delta_lat/2)**2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        distance = R * c
        self.distance_from_branch = round(distance, 2)
        return self.distance_from_branch

    def is_within_branch_radius(self, radius_meters=100):
        """Check if check-in is within acceptable branch radius"""
        distance = self.calculate_distance_from_branch()
        return distance is not None and distance <= radius_meters

    def calculate_check_out_distance(self):
        """Calculate check-out distance from branch in meters"""
        if not self.branch or not self.check_out_lat or not self.check_out_lng:
            return None
        
        if not self.branch.lat or not self.branch.lng:
            return None
        
        # Haversine formula
        lat1, lon1 = float(self.branch.lat), float(self.branch.lng)
        lat2, lon2 = float(self.check_out_lat), float(self.check_out_lng)
        
        R = 6371000 
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = (math.sin(delta_lat/2)**2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return round(R * c, 2)

    def save(self, *args, **kwargs):
        # Auto-set branch from user if not specified
        if not self.branch and self.user.branch:
            self.branch = self.user.branch
        
        from django.utils import timezone
        is_field_staff = getattr(self.user, 'role', 'staff') == 'field_staff'

        # 1. Handle Check-in Geofencing
        if self.check_in_type == 'gps':
            self.calculate_distance_from_branch()
            within_radius = self.is_within_branch_radius(radius_meters=100)
            
            if not is_field_staff and self.pk is None:
                if not within_radius:
                    dist = self.distance_from_branch or "Unknown"
                    raise ValidationError(f"You must be within 100 meters of the branch to check in. Current distance: {dist}m")
                self.status = 'present'
            elif self.pk is None:
                self.status = 'present' if within_radius else 'pending'
        
        # 2. Handle Check-out Geofencing
        if self.check_out_time and self.check_out_lat and self.check_out_lng:
            dist_out = self.calculate_check_out_distance()
            if not is_field_staff and dist_out is not None and dist_out > 100:
                raise ValidationError(f"You must be within 100 meters of the branch to check out. Current distance: {dist_out}m")

        # Auto-set check-in time if not provided
        if not self.check_in_time and self.check_in_type in ['gps', 'photo']:
            self.check_in_time = timezone.now()
        
        super().save(*args, **kwargs)


class AttendanceBreak(models.Model):
    attendance = models.ForeignKey(Attendance, on_delete=models.CASCADE, related_name='breaks')
    start_time = models.DateTimeField(auto_now_add=True)
    end_time   = models.DateTimeField(null=True, blank=True)
    reason     = models.CharField(max_length=100, blank=True, default='Lunch/Tea Break')

    def __str__(self):
        return f'Break for {self.attendance.user.full_name} on {self.attendance.date}'


class AttendanceSchedule(models.Model):
    """
    Defines shift timings and automated reminder slots for a branch.
    """
    branch = models.ForeignKey('branches.Branch', on_delete=models.CASCADE, related_name='attendance_schedules')
    name   = models.CharField(max_length=50, help_text="e.g. Morning Shift, Afternoon Shift")
    check_in_time = models.TimeField()
    check_out_time = models.TimeField()
    grace_period_minutes = models.IntegerField(default=15)
    
    # Notification slots for automated requests
    reminder_slots = models.JSONField(
        default=list, 
        help_text="List of times (HH:MM) to trigger automated attendance requests. Example: ['09:30', '09:40', '09:55']"
    )
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.name} ({self.branch.name})'
