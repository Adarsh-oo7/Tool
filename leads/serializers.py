from rest_framework import serializers
from .models import Customer, Lead, LeadActivity, FollowUp


class LeadActivitySerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(source='actor.full_name', read_only=True)

    class Meta:
        model  = LeadActivity
        fields = ['id', 'lead', 'actor', 'actor_name', 'action', 'detail', 'created_at']
        read_only_fields = ['id', 'created_at', 'actor']


class FollowUpSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.full_name', read_only=True)
    lead_name = serializers.CharField(source='lead.name', read_only=True)
    lead_phone = serializers.CharField(source='lead.phone', read_only=True)

    class Meta:
        model  = FollowUp
        fields = [
            'id', 'lead', 'lead_name', 'lead_phone', 'followup_type', 'priority', 
            'scheduled_date', 'note', 'status', 'completed', 'completed_at', 
            'outcome', 'next_action', 'created_by', 'created_by_name', 
            'assigned_to', 'assigned_to_name', 'created_at',
        ]
        read_only_fields = ['id', 'created_at', 'created_by', 'completed_at']
        extra_kwargs = {'lead': {'required': False, 'allow_null': True}}


class LeadSerializer(serializers.ModelSerializer):
    activities       = LeadActivitySerializer(many=True, read_only=True)
    followups        = FollowUpSerializer(many=True, read_only=True)
    assigned_to_name = serializers.SerializerMethodField()
    branch_name      = serializers.CharField(source='branch.name', read_only=True)
    segment_name     = serializers.SerializerMethodField()
    stage_display    = serializers.CharField(source='get_stage_display', read_only=True)
    source_display   = serializers.CharField(source='get_source_display', read_only=True)
    customer_name    = serializers.CharField(source='customer.name', read_only=True)
    customer_phone   = serializers.CharField(source='customer.phone', read_only=True)

    def get_assigned_to_name(self, obj):
        return obj.assigned_to.full_name if obj.assigned_to else None

    def get_segment_name(self, obj):
        return obj.segment.get_name_display() if obj.segment else None

    class Meta:
        model  = Lead
        fields = [
            'id', 'name', 'phone', 'email', 'age', 'gender',
            'source', 'source_display', 'stage', 'stage_display',
            'lead_type',
            'segment', 'segment_name', 'branch', 'branch_name',
            'assigned_to', 'assigned_to_name', 'created_by',
            'approx_grams', 'occasion', 'product_interest', 'notes',
            'recommendations', 'referred_by',
            'score', 'is_hot', 'campaign', 'customer',
            'customer_name', 'customer_phone',
            'lat', 'lng',
            'created_at', 'updated_at', 'activities', 'followups',
        ]
        read_only_fields = ['id', 'score', 'created_at', 'updated_at', 'created_by', 'customer']
        extra_kwargs = {
            'branch': {'required': False, 'allow_null': True}
        }


class LeadListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list endpoints."""
    is_hot           = serializers.SerializerMethodField()
    assigned_to_name = serializers.SerializerMethodField()
    stage_display    = serializers.CharField(source='get_stage_display', read_only=True)
    branch_name      = serializers.CharField(source='branch.name', read_only=True)
    segment_name     = serializers.SerializerMethodField()

    def get_is_hot(self, obj):
        if obj.is_hot:
            return True
        if obj.customer and obj.customer.temperature == 'hot':
            return True
        return False

    def get_assigned_to_name(self, obj):
        return obj.assigned_to.full_name if obj.assigned_to else None

    def get_segment_name(self, obj):
        return obj.segment.get_name_display() if obj.segment else None

    class Meta:
        model  = Lead
        fields = [
            'id', 'name', 'phone', 'stage', 'stage_display',
            'source', 'score', 'is_hot', 'assigned_to', 'assigned_to_name', 
            'branch', 'branch_name', 'segment', 'segment_name', 'campaign', 'created_at',
            'customer', 'lat', 'lng',
        ]


class CustomerSerializer(serializers.ModelSerializer):
    """Serializer for Customer model - unified profile by phone number."""
    preferred_segments_names = serializers.SerializerMethodField()
    lead_count = serializers.IntegerField(source='leads.count', read_only=True)
    
    class Meta:
        model = Customer
        fields = [
            'id', 'phone', 'name', 'email', 'age', 'gender', 'location',
            'father_name', 'house_name', 'street', 'panchayath',
            'village', 'district', 'state', 'mobile2', 'notes',
            'total_purchases', 'total_spent', 'last_purchase_date', 'avg_ticket_size',
            'total_calls', 'total_visits', 'total_whatsapp', 'last_contact_date',
            'preferred_segments', 'preferred_segments_names',
            'budget_min', 'budget_max', 'budget_range',
            'temperature',
            'occasions', 'timeline',
            'lead_count', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'total_purchases', 'total_spent', 'last_purchase_date',
                          'avg_ticket_size', 'total_calls', 'total_visits', 'total_whatsapp',
                          'last_contact_date', 'timeline', 'lead_count', 'created_at', 'updated_at']

    def get_preferred_segments_names(self, obj):
        return [seg.get_name_display() for seg in obj.preferred_segments.all()]


class CustomerDetailSerializer(CustomerSerializer):
    """Detailed serializer with full lead history."""
    leads = LeadSerializer(many=True, read_only=True)
    
    class Meta(CustomerSerializer.Meta):
        fields = CustomerSerializer.Meta.fields + ['leads']
