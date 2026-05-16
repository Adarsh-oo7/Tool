from django.contrib import admin
from .models import (
    Badge, UserBadge, Leaderboard, LeaderboardEntry,
    Achievement, UserAchievement, PointsTransaction, GamificationProfile
)


@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    list_display = ('name', 'badge_type', 'points', 'icon', 'is_active')
    list_filter = ('badge_type', 'is_active')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at',)


@admin.register(UserBadge)
class UserBadgeAdmin(admin.ModelAdmin):
    list_display = ('user', 'badge', 'earned_at', 'points_earned')
    list_filter = ('badge__badge_type', 'earned_at')
    search_fields = ('user__full_name', 'badge__name')
    readonly_fields = ('earned_at',)


@admin.register(Leaderboard)
class LeaderboardAdmin(admin.ModelAdmin):
    list_display = ('metric', 'period', 'date', 'is_active')
    list_filter = ('period', 'metric', 'is_active')
    search_fields = ('metric', 'period')
    readonly_fields = ('created_at',)


@admin.register(LeaderboardEntry)
class LeaderboardEntryAdmin(admin.ModelAdmin):
    list_display = ('leaderboard', 'user', 'rank', 'score', 'updated_at')
    list_filter = ('leaderboard__period', 'leaderboard__metric', 'rank')
    search_fields = ('user__full_name', 'leaderboard__metric')
    readonly_fields = ('updated_at',)


@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = ('name', 'points', 'badge', 'is_active')
    list_filter = ('badge__badge_type', 'is_active')
    search_fields = ('name', 'description')
    readonly_fields = ()


@admin.register(UserAchievement)
class UserAchievementAdmin(admin.ModelAdmin):
    list_display = ('user', 'achievement', 'unlocked_at', 'points_earned')
    list_filter = ('achievement__badge__badge_type', 'unlocked_at')
    search_fields = ('user__full_name', 'achievement__name')
    readonly_fields = ('unlocked_at',)


@admin.register(PointsTransaction)
class PointsTransactionAdmin(admin.ModelAdmin):
    list_display = ('user', 'transaction_type', 'points', 'description', 'created_at')
    list_filter = ('transaction_type', 'created_at')
    search_fields = ('user__full_name', 'description')
    readonly_fields = ('created_at',)


@admin.register(GamificationProfile)
class GamificationProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'current_level', 'level_name', 'total_points', 'streak_days')
    list_filter = ('current_level', 'level_name', 'streak_days')
    search_fields = ('user__full_name', 'level_name')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-total_points',)
