from rest_framework import serializers
from .models import (
    Badge, UserBadge, Leaderboard, LeaderboardEntry,
    Achievement, UserAchievement, PointsTransaction, GamificationProfile
)


class BadgeSerializer(serializers.ModelSerializer):
    badge_type_display = serializers.CharField(source='get_badge_type_display', read_only=True)

    class Meta:
        model = Badge
        fields = [
            'id', 'name', 'description', 'badge_type', 'badge_type_display',
            'icon', 'points', 'criteria', 'is_active', 'created_at'
        ]


class UserBadgeSerializer(serializers.ModelSerializer):
    badge = BadgeSerializer(read_only=True)
    badge_name = serializers.CharField(source='badge.name', read_only=True)
    badge_icon = serializers.CharField(source='badge.icon', read_only=True)
    badge_type = serializers.CharField(source='badge.badge_type', read_only=True)

    class Meta:
        model = UserBadge
        fields = [
            'id', 'badge', 'badge_name', 'badge_icon', 'badge_type',
            'earned_at', 'points_earned'
        ]


class LeaderboardEntrySerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    user_role = serializers.CharField(source='user.role', read_only=True)
    user_branch = serializers.CharField(source='user.branch.name', read_only=True)

    class Meta:
        model = LeaderboardEntry
        fields = [
            'id', 'leaderboard', 'user', 'user_name', 'user_role', 'user_branch',
            'rank', 'score', 'value', 'updated_at'
        ]


class LeaderboardSerializer(serializers.ModelSerializer):
    metric_display = serializers.CharField(source='get_metric_display', read_only=True)
    period_display = serializers.CharField(source='get_period_display', read_only=True)
    entries = LeaderboardEntrySerializer(many=True, read_only=True)

    class Meta:
        model = Leaderboard
        fields = [
            'id', 'period', 'period_display', 'metric', 'metric_display',
            'date', 'is_active', 'created_at', 'entries'
        ]


class AchievementSerializer(serializers.ModelSerializer):
    badge = BadgeSerializer(read_only=True)
    badge_name = serializers.CharField(source='badge.name', read_only=True)

    class Meta:
        model = Achievement
        fields = [
            'id', 'name', 'description', 'points', 'badge', 'badge_name', 'is_active'
        ]


class UserAchievementSerializer(serializers.ModelSerializer):
    achievement = AchievementSerializer(read_only=True)
    achievement_name = serializers.CharField(source='achievement.name', read_only=True)
    points_earned_display = serializers.SerializerMethodField()

    class Meta:
        model = UserAchievement
        fields = [
            'id', 'achievement', 'achievement_name', 'unlocked_at',
            'points_earned', 'points_earned_display', 'metadata'
        ]

    def get_points_earned_display(self, obj):
        return f"+{obj.points_earned} pts"


class PointsTransactionSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    transaction_type_display = serializers.CharField(source='get_transaction_type_display', read_only=True)
    points_display = serializers.SerializerMethodField()

    class Meta:
        model = PointsTransaction
        fields = [
            'id', 'user', 'user_name', 'transaction_type', 'transaction_type_display',
            'points', 'points_display', 'description', 'reference_id', 'created_at'
        ]

    def get_points_display(self, obj):
        prefix = "+" if obj.points > 0 else ""
        return f"{prefix}{obj.points} pts"


class GamificationProfileSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    user_role = serializers.CharField(source='user.role', read_only=True)
    user_branch = serializers.SerializerMethodField()
    level_progress = serializers.SerializerMethodField()
    next_level_points = serializers.SerializerMethodField()
    badges = serializers.SerializerMethodField()

    def get_user_branch(self, obj):
        """Get user branch name safely"""
        try:
            return obj.user.branch.name if obj.user.branch else 'No Branch'
        except:
            return 'Unknown'

    def get_badges(self, obj):
        """Get user badges safely"""
        try:
            badges = UserBadge.objects.filter(user=obj.user).select_related('badge')
            return UserBadgeSerializer(badges, many=True).data
        except:
            return []

    class Meta:
        model = GamificationProfile
        fields = [
            'id', 'user', 'user_name', 'user_role', 'user_branch',
            'total_points', 'current_level', 'level_name', 'level_progress',
            'next_level_points', 'badges_count', 'achievements_count',
            'streak_days', 'last_activity_date', 'created_at', 'updated_at', 'badges'
        ]

    def get_level_progress(self, obj):
        """Calculate progress towards next level"""
        level_points = {
            1: (0, 200),    # Beginner -> Intermediate
            2: (200, 500),  # Intermediate -> Senior
            3: (500, 1000), # Senior -> Bronze
            4: (1000, 1500), # Bronze -> Bronze Elite
            5: (1500, 2500), # Bronze Elite -> Silver
            6: (2500, 3500), # Silver -> Silver Elite
            7: (3500, 5000), # Silver Elite -> Gold
            8: (5000, 7500), # Gold -> Platinum
            9: (7500, 10000), # Platinum -> Diamond
            10: (10000, None) # Diamond (max level)
        }
        
        if obj.current_level >= 10:
            return 100.0
        
        min_points, max_points = level_points.get(obj.current_level, (0, 200))
        if max_points is None:
            return 100.0
        
        progress = ((obj.total_points - min_points) / (max_points - min_points)) * 100
        return max(0, min(100, progress))

    def get_next_level_points(self, obj):
        """Get points needed for next level"""
        level_points = {
            1: 200, 2: 500, 3: 1000, 4: 1500, 5: 2500,
            6: 3500, 7: 5000, 8: 7500, 9: 10000, 10: 10000
        }
        
        if obj.current_level >= 10:
            return None
        
        return level_points.get(obj.current_level + 1, 200)
