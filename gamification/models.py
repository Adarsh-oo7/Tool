from django.db import models
from django.conf import settings
from django.utils import timezone
from django.db.models import Sum, Count, F


class Badge(models.Model):
    """Achievement badges that can be earned by staff"""
    BADGE_TYPES = [
        ('sales', 'Sales Achievement'),
        ('leads', 'Lead Management'),
        ('attendance', 'Attendance'),
        ('conversion', 'Conversion Rate'),
        ('special', 'Special Achievement'),
    ]
    
    name = models.CharField(max_length=100)
    description = models.TextField()
    badge_type = models.CharField(max_length=20, choices=BADGE_TYPES)
    icon = models.CharField(max_length=50, help_text="Icon name or emoji")
    points = models.IntegerField(default=0, help_text="Points awarded for this badge")
    criteria = models.JSONField(help_text="JSON criteria for earning this badge")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['badge_type', 'name']

    def __str__(self):
        return f'{self.name} ({self.get_badge_type_display()})'


class UserBadge(models.Model):
    """Badge awarded to a specific user"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='badges')
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE, related_name='awards')
    earned_at = models.DateTimeField(auto_now_add=True)
    points_earned = models.IntegerField()

    class Meta:
        unique_together = ['user', 'badge']
        ordering = ['-earned_at']

    def __str__(self):
        return f'{self.user.full_name} - {self.badge.name}'


class Leaderboard(models.Model):
    """Weekly/monthly leaderboards for different metrics"""
    PERIOD_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ]
    
    METRIC_CHOICES = [
        ('sales_count', 'Sales Count'),
        ('sales_revenue', 'Sales Revenue'),
        ('leads_generated', 'Leads Generated'),
        ('leads_converted', 'Leads Converted'),
        ('conversion_rate', 'Conversion Rate'),
        ('calls_made', 'Calls Made'),
        ('attendance', 'Attendance Score'),
    ]

    period = models.CharField(max_length=10, choices=PERIOD_CHOICES)
    metric = models.CharField(max_length=20, choices=METRIC_CHOICES)
    date = models.DateField(help_text="Start date for this leaderboard period")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['period', 'metric', 'date']
        ordering = ['-date', 'period', 'metric']

    def __str__(self):
        return f'{self.get_metric_display()} - {self.get_period_display()} ({self.date})'


class LeaderboardEntry(models.Model):
    """Individual entries on a leaderboard"""
    leaderboard = models.ForeignKey(Leaderboard, on_delete=models.CASCADE, related_name='entries')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='leaderboard_entries')
    rank = models.IntegerField()
    score = models.FloatField()
    value = models.JSONField(help_text="Raw metric values")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['leaderboard', 'user']
        ordering = ['rank']

    def __str__(self):
        return f'#{self.rank} {self.user.full_name} - {self.score}'


class Achievement(models.Model):
    """Track specific achievements and milestones"""
    name = models.CharField(max_length=100)
    description = models.TextField()
    points = models.IntegerField(default=0)
    badge = models.ForeignKey(Badge, on_delete=models.SET_NULL, null=True, blank=True, related_name='achievements')
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class UserAchievement(models.Model):
    """Achievement unlocked by a user"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='achievements')
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE, related_name='unlocked_by')
    unlocked_at = models.DateTimeField(auto_now_add=True)
    points_earned = models.IntegerField()
    metadata = models.JSONField(default=dict, help_text="Additional data about the achievement")

    class Meta:
        unique_together = ['user', 'achievement']
        ordering = ['-unlocked_at']

    def __str__(self):
        return f'{self.user.full_name} - {self.achievement.name}'


class PointsTransaction(models.Model):
    """Track points earned and spent by users"""
    TRANSACTION_TYPES = [
        ('earned', 'Points Earned'),
        ('spent', 'Points Spent'),
        ('bonus', 'Bonus Points'),
        ('penalty', 'Points Penalty'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='points_transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    points = models.IntegerField(help_text="Positive for earned, negative for spent")
    description = models.CharField(max_length=200)
    reference_id = models.CharField(max_length=50, blank=True, help_text="Reference to related object")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.full_name}: {self.points} points ({self.transaction_type})'


class GamificationProfile(models.Model):
    """Extended profile for gamification features"""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='gamification_profile')
    total_points = models.IntegerField(default=0)
    current_level = models.IntegerField(default=1)
    level_name = models.CharField(max_length=50, default='Beginner')
    badges_count = models.IntegerField(default=0)
    achievements_count = models.IntegerField(default=0)
    streak_days = models.IntegerField(default=0)
    last_activity_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-total_points']

    def __str__(self):
        return f'{self.user.full_name} - Level {self.current_level} ({self.total_points} pts)'

    def calculate_level(self):
        """Calculate level based on total points"""
        points = self.total_points
        if points >= 10000:
            self.current_level = 10
            self.level_name = 'Diamond'
        elif points >= 7500:
            self.current_level = 9
            self.level_name = 'Platinum'
        elif points >= 5000:
            self.current_level = 8
            self.level_name = 'Gold'
        elif points >= 3500:
            self.current_level = 7
            self.level_name = 'Silver Elite'
        elif points >= 2500:
            self.current_level = 6
            self.level_name = 'Silver'
        elif points >= 1500:
            self.current_level = 5
            self.level_name = 'Bronze Elite'
        elif points >= 1000:
            self.current_level = 4
            self.level_name = 'Bronze'
        elif points >= 500:
            self.current_level = 3
            self.level_name = 'Senior'
        elif points >= 200:
            self.current_level = 2
            self.level_name = 'Intermediate'
        else:
            self.current_level = 1
            self.level_name = 'Beginner'

    def update_streak(self):
        """Update activity streak"""
        today = timezone.localdate()
        if self.last_activity_date == today - timezone.timedelta(days=1):
            self.streak_days += 1
        elif self.last_activity_date != today:
            self.streak_days = 1
        self.last_activity_date = today

    def add_points(self, points, description, reference_id=''):
        """Add points to user's total"""
        self.total_points += points
        self.calculate_level()
        self.save(update_fields=['total_points', 'current_level', 'level_name'])
        
        # Create points transaction
        PointsTransaction.objects.create(
            user=self.user,
            transaction_type='earned',
            points=points,
            description=description,
            reference_id=reference_id
        )
