from django.db import models
from django.conf import settings
from django.utils import timezone


class Customer(models.Model):
    """
    Unified customer profile by phone number.
    Primary identifier is phone number (unique).
    Tracks all interactions, purchases, and preferences across the system.
    """
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
        ('not_specified', 'Not Specified'),
    ]

    # Basic Info - Phone is the primary identifier
    phone = models.CharField(max_length=15, unique=True, db_index=True)
    name = models.CharField(max_length=200)
    email = models.EmailField(blank=True, null=True)
    age = models.PositiveIntegerField(null=True, blank=True)
    gender = models.CharField(max_length=20, choices=GENDER_CHOICES, default='not_specified')
    location = models.CharField(max_length=200, blank=True)
    lat = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    lng = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    
    # Extended Info from Legacy Data
    father_name = models.CharField(max_length=200, blank=True, null=True)
    house_name  = models.CharField(max_length=200, blank=True, null=True)
    street      = models.CharField(max_length=200, blank=True, null=True)
    panchayath  = models.CharField(max_length=200, blank=True, null=True)
    village     = models.CharField(max_length=200, blank=True, null=True)
    district    = models.CharField(max_length=200, blank=True, null=True)
    state       = models.CharField(max_length=200, blank=True, null=True)
    mobile2     = models.CharField(max_length=15, blank=True, null=True)
    notes       = models.TextField(blank=True, null=True, help_text="General notes about this customer")

    # Purchase History
    total_purchases = models.IntegerField(default=0)
    total_spent = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    last_purchase_date = models.DateTimeField(null=True, blank=True)
    avg_ticket_size = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    # Interaction Stats
    total_calls = models.IntegerField(default=0)
    total_visits = models.IntegerField(default=0)
    total_whatsapp = models.IntegerField(default=0)
    last_contact_date = models.DateTimeField(null=True, blank=True)

    # Preferences & Priority
    preferred_segments = models.ManyToManyField(
        'branches.Segment',
        blank=True,
        related_name='interested_customers'
    )
    budget_min = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    budget_max = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    budget_range = models.CharField(max_length=100, blank=True, help_text="Display string for budget range")
    
    TEMPERATURE_CHOICES = [
        ('hot', 'Hot'),
        ('warm', 'Warm'),
        ('cold', 'Cold'),
    ]
    temperature = models.CharField(max_length=10, choices=TEMPERATURE_CHOICES, default='cold', help_text="Lead priority/temperature")

    # Special Occasions (JSON field)
    occasions = models.JSONField(default=list, blank=True, help_text="List of {type, date} objects")

    # Timeline (All Interactions) - JSON field for performance
    timeline = models.JSONField(default=list, blank=True, help_text="Chronological list of all interactions")

    # System fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['phone']),
            models.Index(fields=['name']),
            models.Index(fields=['-last_contact_date']),
        ]

    def __str__(self):
        return f'{self.name} ({self.phone})'

    def add_timeline_event(self, event_type, details):
        """Add an event to the customer timeline"""
        event = {
            'date': timezone.now().isoformat(),
            'type': event_type,
            'details': details
        }
        self.timeline.append(event)
        self.save(update_fields=['timeline', 'updated_at'])

    def update_purchase_stats(self, amount):
        """Update purchase statistics after a sale"""
        self.total_purchases += 1
        self.total_spent += amount
        self.last_purchase_date = timezone.now()
        self.avg_ticket_size = self.total_spent / self.total_purchases
        self.save(update_fields=['total_purchases', 'total_spent', 'last_purchase_date', 'avg_ticket_size', 'updated_at'])

    def update_interaction_stats(self, interaction_type):
        """Update interaction statistics"""
        if interaction_type == 'call':
            self.total_calls += 1
        elif interaction_type == 'visit':
            self.total_visits += 1
        elif interaction_type == 'whatsapp':
            self.total_whatsapp += 1
        self.last_contact_date = timezone.now()
        self.save(update_fields=['total_calls', 'total_visits', 'total_whatsapp', 'last_contact_date', 'updated_at'])


class Lead(models.Model):
    SOURCE_CHOICES = [
        ('walkin',    'Walk-in'),
        ('instagram', 'Instagram'),
        ('facebook',  'Facebook'),
        ('website',   'Website'),
        ('referral',  'Referral'),
        ('whatsapp',  'WhatsApp'),
        ('other',     'Other'),
    ]
    STAGE_CHOICES = [
        ('new',       'New'),
        ('contacted', 'Contacted'),
        ('interested','Interested'),
        ('scheduled', 'Visit Scheduled'),
        ('converted', 'Converted'),
        ('lost',      'Lost'),
    ]

    # Core identity - Link to Customer profile
    customer = models.ForeignKey('Customer', on_delete=models.SET_NULL, null=True, blank=True, related_name='leads')
    name    = models.CharField(max_length=200)
    phone   = models.CharField(max_length=15)
    email   = models.EmailField(blank=True, null=True)
    age     = models.PositiveIntegerField(null=True, blank=True)
    gender  = models.CharField(max_length=10, blank=True,
                               choices=[('male','Male'),('female','Female'),('other','Other')])

    # Source & classification
    source  = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='walkin')
    branch  = models.ForeignKey('branches.Branch',  on_delete=models.CASCADE, related_name='leads')
    segment = models.ForeignKey('branches.Segment', on_delete=models.SET_NULL, null=True, blank=True)

    # Assignment & stage
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                    null=True, blank=True, related_name='assigned_leads')
    stage       = models.CharField(max_length=20, choices=STAGE_CHOICES, default='new')

    # Interest details
    approx_grams    = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True, help_text="Approximate weight in grams")
    occasion        = models.CharField(max_length=100, blank=True)   # wedding, gift, etc.
    product_interest= models.TextField(blank=True)                   # what they liked
    recommendations = models.TextField(blank=True, help_text="AI or Staff recommendations")
    referred_by     = models.CharField(max_length=200, blank=True)   # Referral source details
    notes           = models.TextField(blank=True)
    lat             = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    lng             = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)

    # Extended Info from Legacy Data
    father_name = models.CharField(max_length=200, blank=True, null=True)
    house_name  = models.CharField(max_length=200, blank=True, null=True)
    street      = models.CharField(max_length=200, blank=True, null=True)
    panchayath  = models.CharField(max_length=200, blank=True, null=True)
    village     = models.CharField(max_length=200, blank=True, null=True)
    district    = models.CharField(max_length=200, blank=True, null=True)
    state       = models.CharField(max_length=200, blank=True, null=True)
    mobile2     = models.CharField(max_length=15, blank=True, null=True)
    legacy_id   = models.IntegerField(null=True, blank=True, help_text="Original ID from products.json")

    # AI scoring (0-100)
    score           = models.IntegerField(default=0)
    is_hot          = models.BooleanField(default=False)
    
    LEAD_TYPES = (
        ('normal', 'Normal Sale'),
        ('advance', 'Advance Booking')
    )
    lead_type = models.CharField(max_length=20, choices=LEAD_TYPES, default='normal')

    # GPS Location
    lat             = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    lng             = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)

    # Campaign linkage
    campaign        = models.ForeignKey('campaigns.Campaign', null=True, blank=True,
                                        on_delete=models.SET_NULL, related_name='leads')

    # Timestamps
    created_by  = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                    null=True, related_name='created_leads')
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes  = [
            models.Index(fields=['branch', 'stage']),
            models.Index(fields=['assigned_to', 'stage']),
            models.Index(fields=['phone']),
        ]

    def __str__(self): return f'{self.name} ({self.stage})'

    def auto_assign(self, task_type=None):
        """
        Smart Auto-Assign: Picks the best staff member based on Role Match and Workload Score.
        1. Identifies preferred role based on task_type (visit -> field_staff, call -> telecaller).
        2. Filters for active staff in the same branch.
        3. Calculates Workload Score = (Active Leads * 2) + (Today's Pending Tasks).
        4. Selects the person with the lowest score in the preferred role (or any role as fallback).
        """
        if not self.branch:
            return None
            
        from django.contrib.auth import get_user_model
        from django.db.models import Count, Q
        from django.utils import timezone
        User = get_user_model()
        today = timezone.localdate()
        
        # 1. Determine Preferred Role based on Task Type
        target_type = task_type or getattr(self, 'followup_type', 'call')
        
        if target_type == 'visit':
            preferred_roles = ['field_staff']
        elif target_type in ['call', 'whatsapp', 'sms']:
            preferred_roles = ['telecaller']
        else:
            preferred_roles = ['staff', 'telecaller']
            
        # 2. Identify the Pool (Active staff in branch)
        staff_pool = User.objects.filter(
            branch=self.branch, 
            is_active=True
        ).exclude(role='owner')
        
        if not staff_pool.exists():
            return None
            
        # 3. Filter by preferred roles, fallback to any staff if none available
        qualified_staff = staff_pool.filter(role__in=preferred_roles)
        if not qualified_staff.exists():
            qualified_staff = staff_pool
            
        # 4. Calculate Workload Score for each staff member
        balanced_staff = qualified_staff.annotate(
            active_leads_count=Count(
                'assigned_leads', 
                filter=Q(assigned_leads__stage__in=['new', 'contacted', 'follow_up'])
            ),
            today_tasks_count=Count(
                'followups_assigned',
                filter=Q(followups_assigned__scheduled_date__date=today, followups_assigned__completed=False)
            )
        )
        
        # 5. Sort by Workload Score: (Leads * 2) + (Tasks * 1)
        # Ties are broken by staff ID for consistent round-robin distribution
        best_staff = sorted(
            balanced_staff, 
            key=lambda s: (s.active_leads_count * 2) + s.today_tasks_count
        )
        
        if best_staff:
            target = best_staff[0]
            self.assigned_to = target
            return target
            
        return None

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        
        # Auto-assign if new or if assignment is lost
        if (is_new or not self.assigned_to) and self.branch:
            self.auto_assign()
            
        super().save(*args, **kwargs)


class FollowUp(models.Model):
    TYPE_CHOICES = [
        ('call',       'Phone Call'),
        ('whatsapp',   'WhatsApp Message'),
        ('email',      'Email'),
        ('visit',      'Visit'),
        ('sms',        'SMS'),
        ('auto',       'Auto-generated'),
    ]
    
    PRIORITY_CHOICES = [
        ('low',    'Low'),
        ('medium', 'Medium'),
        ('high',   'High'),
        ('urgent', 'Urgent'),
    ]
    
    STATUS_CHOICES = [
        ('pending',    'Pending'),
        ('scheduled',  'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed',   'Completed'),
        ('missed',     'Missed'),
        ('cancelled',  'Cancelled'),
    ]

    lead           = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='followups')
    followup_type  = models.CharField(max_length=20, choices=TYPE_CHOICES, default='call')
    priority       = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    scheduled_date = models.DateTimeField()
    scheduled_time = models.TimeField(null=True, blank=True, help_text="Specific time for the follow-up")
    note           = models.TextField(blank=True)
    status         = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    completed      = models.BooleanField(default=False)
    completed_at   = models.DateTimeField(null=True, blank=True)
    outcome        = models.CharField(max_length=100, blank=True, help_text="Result of the follow-up")
    next_action    = models.TextField(blank=True, help_text="Next steps identified")
    status_reason  = models.CharField(max_length=200, blank=True, help_text="Reason for closing or specific status detail")
    reminder_sent  = models.BooleanField(default=False, help_text="Whether reminder notification was sent")
    auto_generated = models.BooleanField(default=False, help_text="Whether this was auto-generated")
    created_by     = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                       null=True, related_name='followups_created')
    assigned_to    = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                       null=True, blank=True, related_name='followups_assigned')
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['scheduled_date', 'priority']
        indexes = [
            models.Index(fields=['lead', 'status', 'scheduled_date']),
            models.Index(fields=['status', 'scheduled_date']),
            models.Index(fields=['priority', 'scheduled_date']),
        ]

    def __str__(self):
        return f'{self.get_followup_type_display()} for {self.lead.name} on {self.scheduled_date}'

    def save(self, *args, **kwargs):
        # Auto-completion logic
        if self.completed and not self.completed_at:
            from django.utils import timezone
            self.completed_at = timezone.now()
            self.status = 'completed'
        
        # Auto-status based on scheduled date
        if not self.completed and self.scheduled_date:
            from django.utils import timezone
            from django.utils.dateparse import parse_datetime
            
            sched = self.scheduled_date
            if isinstance(sched, str):
                sched = parse_datetime(sched)
            
            if sched:
                # If sched is naive, make it aware (assuming local time)
                if timezone.is_naive(sched):
                    sched = timezone.make_aware(sched)
                
                if sched < timezone.now() and self.status == 'pending':
                    self.status = 'missed'
        
        super().save(*args, **kwargs)

    def mark_completed(self, outcome='', next_action=''):
        """Mark follow-up as completed with outcome"""
        from django.utils import timezone
        self.completed = True
        self.completed_at = timezone.now()
        self.status = 'completed'
        self.outcome = outcome
        self.next_action = next_action
        self.save(update_fields=['completed', 'completed_at', 'status', 'outcome', 'next_action'])

    def schedule_next_followup(self, days_ahead=3, followup_type='call', note=''):
        """Create next follow-up automatically"""
        from django.utils import timezone
        from datetime import timedelta
        
        next_date = timezone.now() + timedelta(days=days_ahead)
        
        return FollowUp.objects.create(
            lead=self.lead,
            followup_type=followup_type,
            priority=self.priority,
            scheduled_date=next_date,
            note=note or f"Auto-scheduled follow-up after previous {self.get_followup_type_display()}",
            auto_generated=True,
            created_by=self.created_by
        )


class LeadActivity(models.Model):
    """Audit log for every status change or note on a lead."""
    lead       = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='activities')
    actor      = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    action     = models.CharField(max_length=100)  # 'stage_changed', 'note_added', etc.
    detail     = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']