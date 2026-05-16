from django.contrib import admin
from .models import (
    AlertType, AlertRule, Alert, AlertSubscription, AlertDigest, SmartSuggestion
)


@admin.register(AlertType)
class AlertTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'severity', 'default_enabled', 'created_at')
    list_filter = ('category', 'severity', 'default_enabled')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at',)


@admin.register(AlertRule)
class AlertRuleAdmin(admin.ModelAdmin):
    list_display = ('name', 'alert_type', 'metric', 'condition', 'threshold_value', 'is_active', 'created_at')
    list_filter = ('alert_type', 'metric', 'condition', 'is_active')
    search_fields = ('name', 'alert_type__name')
    readonly_fields = ('created_at', 'updated_at')
    filter_horizontal = ('target_users',)


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ('title', 'alert_type', 'severity', 'status', 'triggered_at', 'acknowledged_at')
    list_filter = ('status', 'severity', 'alert_type', 'triggered_at')
    search_fields = ('title', 'message')
    readonly_fields = ('triggered_at', 'acknowledged_at', 'resolved_at')
    filter_horizontal = ('recipients',)


@admin.register(AlertSubscription)
class AlertSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'alert_type', 'is_subscribed', 'created_at')
    list_filter = ('is_subscribed', 'alert_type__category', 'alert_type__severity')
    search_fields = ('user__full_name', 'alert_type__name')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(AlertDigest)
class AlertDigestAdmin(admin.ModelAdmin):
    list_display = ('user', 'period', 'digest_date', 'alert_count', 'critical_count', 'sent_at')
    list_filter = ('period', 'digest_date', 'sent_at')
    search_fields = ('user__full_name',)
    readonly_fields = ('created_at',)


@admin.register(SmartSuggestion)
class SmartSuggestionAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'priority', 'confidence_score', 'is_implemented', 'created_at')
    list_filter = ('category', 'priority', 'is_implemented', 'created_at')
    search_fields = ('title', 'description', 'recommendation')
    readonly_fields = ('created_at', 'implemented_at')
    filter_horizontal = ('target_users',)
