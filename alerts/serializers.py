from rest_framework import serializers
from .models import (
    AlertType, AlertRule, Alert, AlertSubscription, AlertDigest, SmartSuggestion
)


class AlertTypeSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    severity_display = serializers.CharField(source='get_severity_display', read_only=True)

    class Meta:
        model = AlertType
        fields = [
            'id', 'name', 'category', 'category_display', 'severity', 'severity_display',
            'description', 'template_message', 'default_enabled', 'created_at'
        ]


class AlertRuleSerializer(serializers.ModelSerializer):
    alert_type_name = serializers.CharField(source='alert_type.name', read_only=True)
    alert_type_category = serializers.CharField(source='alert_type.category', read_only=True)
    metric_display = serializers.CharField(source='get_metric_display', read_only=True)
    condition_display = serializers.CharField(source='get_condition_display', read_only=True)
    target_users_names = serializers.SerializerMethodField()
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)

    class Meta:
        model = AlertRule
        fields = [
            'id', 'alert_type', 'alert_type_name', 'alert_type_category', 'name',
            'metric', 'metric_display', 'condition', 'condition_display',
            'threshold_value', 'threshold_text', 'time_period_hours', 'is_active',
            'target_roles', 'target_users', 'target_users_names',
            'created_by', 'created_by_name', 'created_at', 'updated_at'
        ]

    def get_target_users_names(self, obj):
        return [user.full_name for user in obj.target_users.all()]


class AlertSerializer(serializers.ModelSerializer):
    rule_name = serializers.CharField(source='rule.name', read_only=True)
    alert_type_name = serializers.CharField(source='alert_type.name', read_only=True)
    alert_type_category = serializers.CharField(source='alert_type.category', read_only=True)
    severity_display = serializers.CharField(source='get_severity_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    recipients_names = serializers.SerializerMethodField()
    acknowledged_by_name = serializers.CharField(source='acknowledged_by.full_name', read_only=True)
    resolved_by_name = serializers.CharField(source='resolved_by.full_name', read_only=True)
    time_since_triggered = serializers.SerializerMethodField()

    class Meta:
        model = Alert
        fields = [
            'id', 'rule', 'rule_name', 'alert_type', 'alert_type_name', 'alert_type_category',
            'title', 'message', 'severity', 'severity_display', 'status', 'status_display',
            'recipients', 'recipients_names', 'metadata', 'triggered_at', 'time_since_triggered',
            'acknowledged_at', 'acknowledged_by', 'acknowledged_by_name',
            'resolved_at', 'resolved_by', 'resolved_by_name'
        ]

    def get_recipients_names(self, obj):
        return [user.full_name for user in obj.recipients.all()]

    def get_time_since_triggered(self, obj):
        from django.utils import timezone
        now = timezone.now()
        diff = now - obj.triggered_at
        
        if diff.days > 0:
            return f"{diff.days}d ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours}h ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes}m ago"
        else:
            return "Just now"


class AlertSubscriptionSerializer(serializers.ModelSerializer):
    alert_type_name = serializers.CharField(source='alert_type.name', read_only=True)
    alert_type_category = serializers.CharField(source='alert_type.category', read_only=True)
    alert_type_severity = serializers.CharField(source='alert_type.severity', read_only=True)

    class Meta:
        model = AlertSubscription
        fields = [
            'id', 'alert_type', 'alert_type_name', 'alert_type_category', 'alert_type_severity',
            'is_subscribed', 'notification_channels', 'created_at', 'updated_at'
        ]


class AlertDigestSerializer(serializers.ModelSerializer):
    period_display = serializers.CharField(source='get_period_display', read_only=True)

    class Meta:
        model = AlertDigest
        fields = [
            'id', 'user', 'period', 'period_display', 'digest_date',
            'alert_count', 'critical_count', 'high_count', 'medium_count', 'low_count',
            'summary', 'sent_at', 'created_at'
        ]


class SmartSuggestionSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    target_users_names = serializers.SerializerMethodField()
    implemented_by_name = serializers.CharField(source='implemented_by.full_name', read_only=True)
    confidence_display = serializers.SerializerMethodField()
    time_since_created = serializers.SerializerMethodField()

    class Meta:
        model = SmartSuggestion
        fields = [
            'id', 'title', 'category', 'category_display', 'priority', 'priority_display',
            'description', 'recommendation', 'expected_impact', 'confidence_score',
            'confidence_display', 'data_insights', 'target_users', 'target_users_names',
            'is_implemented', 'implemented_at', 'implemented_by', 'implemented_by_name',
            'feedback_score', 'feedback_notes', 'created_at', 'time_since_created'
        ]

    def get_target_users_names(self, obj):
        return [user.full_name for user in obj.target_users.all()]

    def get_confidence_display(self, obj):
        return f"{obj.confidence_score * 100:.0f}%"

    def get_time_since_created(self, obj):
        from django.utils import timezone
        now = timezone.now()
        diff = now - obj.created_at
        
        if diff.days > 0:
            return f"{diff.days}d ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours}h ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes}m ago"
        else:
            return "Just now"
