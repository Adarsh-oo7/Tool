from rest_framework import serializers
from .models import Lead, LeadActivity, FollowUp


class LeadActivitySerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(source='actor.full_name', read_only=True)

    class Meta:
        model  = LeadActivity
        fields = ['id', 'lead', 'actor', 'actor_name', 'action', 'detail', 'created_at']
        read_only_fields = ['id', 'created_at', 'actor']


class FollowUpSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)

    class Meta:
        model  = FollowUp
        fields = [
            'id', 'lead', 'scheduled_date', 'note', 'completed',
            'completed_at', 'created_by', 'created_by_name', 'created_at',
        ]
        read_only_fields = ['id', 'created_at', 'created_by', 'completed_at']


class LeadSerializer(serializers.ModelSerializer):
    activities       = LeadActivitySerializer(many=True, read_only=True)
    followups        = FollowUpSerializer(many=True, read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.full_name', read_only=True)
    branch_name      = serializers.CharField(source='branch.name', read_only=True)
    segment_name     = serializers.CharField(source='segment.get_name_display', read_only=True)
    stage_display    = serializers.CharField(source='get_stage_display', read_only=True)
    source_display   = serializers.CharField(source='get_source_display', read_only=True)

    class Meta:
        model  = Lead
        fields = [
            'id', 'name', 'phone', 'email', 'age', 'gender',
            'source', 'source_display', 'stage', 'stage_display',
            'segment', 'segment_name', 'branch', 'branch_name',
            'assigned_to', 'assigned_to_name', 'created_by',
            'budget', 'occasion', 'product_interest', 'notes',
            'score', 'is_hot', 'campaign',
            'created_at', 'updated_at', 'activities', 'followups',
        ]
        read_only_fields = ['id', 'score', 'is_hot', 'created_at', 'updated_at', 'created_by']


class LeadListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list endpoints."""
    assigned_to_name = serializers.CharField(source='assigned_to.full_name', read_only=True)
    stage_display    = serializers.CharField(source='get_stage_display', read_only=True)

    class Meta:
        model  = Lead
        fields = [
            'id', 'name', 'phone', 'stage', 'stage_display',
            'source', 'score', 'is_hot', 'assigned_to_name', 'created_at',
        ]
