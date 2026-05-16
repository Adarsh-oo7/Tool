from rest_framework import serializers
from .models import Campaign, CampaignLead, WhatsAppTemplate, SpecialDayMessage, Integration, IntegrationAnalytics


class WhatsAppTemplateSerializer(serializers.ModelSerializer):
    trigger_display    = serializers.CharField(source='get_trigger_display', read_only=True)
    created_by_name    = serializers.CharField(source='created_by.full_name', read_only=True)

    class Meta:
        model  = WhatsAppTemplate
        fields = [
            'id', 'name', 'trigger', 'trigger_display', 'message',
            'is_active', 'created_by', 'created_by_name', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by']


class SpecialDayMessageSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)

    class Meta:
        model  = SpecialDayMessage
        fields = [
            'id', 'name', 'date', 'message',
            'send_to_staff', 'send_to_leads', 'is_active',
            'created_by', 'created_by_name', 'created_at',
        ]
        read_only_fields = ['id', 'created_at', 'created_by']

    def validate_date(self, value):
        import datetime
        try:
            datetime.date(2000, value.month, value.day)
        except ValueError:
            raise serializers.ValidationError('Invalid calendar date.')
        return value


class CampaignLeadSerializer(serializers.ModelSerializer):
    lead_name  = serializers.CharField(source='lead.name', read_only=True)
    lead_phone = serializers.CharField(source='lead.phone', read_only=True)

    class Meta:
        model  = CampaignLead
        fields = [
            'id', 'campaign', 'lead', 'lead_name', 'lead_phone',
            'sent', 'delivered', 'read', 'converted', 'sent_at', 'error',
        ]
        read_only_fields = ['id', 'sent', 'sent_at', 'error']


class CampaignListSerializer(serializers.ModelSerializer):
    """Lightweight — for list endpoint."""
    branch_name    = serializers.CharField(source='branch.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    type_display   = serializers.CharField(source='get_campaign_type_display', read_only=True)
    channel_display = serializers.CharField(source='get_channel_type_display', read_only=True)
    objective_display = serializers.CharField(source='get_objective_display', read_only=True)
    total_leads    = serializers.IntegerField(read_only=True)
    leads_count    = serializers.IntegerField(source='total_leads', read_only=True)
    sent_count     = serializers.IntegerField(read_only=True)
    roi_percent    = serializers.FloatField(read_only=True)
    roi            = serializers.FloatField(source='roi_percent', read_only=True)

    class Meta:
        model  = Campaign
        fields = [
            'id', 'name', 'branch_name', 'campaign_type', 'type_display',
            'channel_type', 'channel_display', 'objective', 'objective_display',
            'tags', 'platforms',
            'status', 'status_display', 'scheduled_at',
            'total_leads', 'leads_count', 'sent_count', 'roi_percent', 'roi',
        ]


class CampaignSerializer(serializers.ModelSerializer):
    """Full detail."""
    campaign_leads    = CampaignLeadSerializer(many=True, read_only=True)
    created_by_name   = serializers.CharField(source='created_by.full_name', read_only=True)
    branch_name       = serializers.CharField(source='branch.name', read_only=True)
    segment_name      = serializers.CharField(source='segment.get_name_display', read_only=True)
    status_display    = serializers.CharField(source='get_status_display', read_only=True)
    type_display      = serializers.CharField(source='get_campaign_type_display', read_only=True)
    channel_display   = serializers.CharField(source='get_channel_type_display', read_only=True)
    objective_display = serializers.CharField(source='get_objective_display', read_only=True)
    whatsapp_template = WhatsAppTemplateSerializer(read_only=True)
    total_leads       = serializers.IntegerField(read_only=True)
    sent_count        = serializers.IntegerField(read_only=True)
    converted_count   = serializers.IntegerField(read_only=True)
    roi_percent       = serializers.FloatField(read_only=True)

    class Meta:
        model  = Campaign
        fields = [
            'id', 'name', 'branch', 'branch_name', 'segment', 'segment_name',
            'campaign_type', 'type_display',
            'channel_type', 'channel_display', 'objective', 'objective_display',
            'tags', 'platforms',
            'whatsapp_template', 'template_name', 'message',
            'status', 'status_display', 'scheduled_at', 'sent_at',
            'created_by', 'created_by_name', 'created_at', 'updated_at',
            'total_leads', 'sent_count', 'converted_count', 'roi_percent',
            'campaign_leads',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by', 'sent_at']


class CampaignCreateSerializer(serializers.ModelSerializer):
    """Write-only — for create."""
    class Meta:
        model  = Campaign
        fields = [
            'name', 'branch', 'segment', 'campaign_type',
            'channel_type', 'objective', 'tags', 'platforms',
            'whatsapp_template', 'template_name', 'message', 'scheduled_at',
        ]


class IntegrationSerializer(serializers.ModelSerializer):
    """Full integration details (without sensitive tokens)."""
    platform_display = serializers.CharField(read_only=True)
    platform_name = serializers.CharField(source='get_platform_display', read_only=True)
    sync_status_display = serializers.CharField(source='get_sync_status_display', read_only=True)
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)
    
    class Meta:
        model = Integration
        fields = [
            'id', 'platform', 'platform_display', 'platform_name',
            'account_name', 'account_id', 'is_connected', 'sync_enabled',
            'last_sync', 'sync_status', 'sync_status_display', 'sync_error',
            'branch', 'branch_name', 'created_by', 'created_by_name',
            'created_at', 'updated_at', 'metadata'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by']


class IntegrationCreateSerializer(serializers.ModelSerializer):
    """For creating/updating integrations (handles tokens securely)."""
    class Meta:
        model = Integration
        fields = [
            'platform', 'account_name', 'account_id',
            'access_token', 'refresh_token', 'token_expiry',
            'is_connected', 'sync_enabled', 'branch', 'metadata'
        ]
    
    def create(self, validated_data):
        # Encrypt tokens before saving
        access_token = validated_data.pop('access_token', None)
        refresh_token = validated_data.pop('refresh_token', None)
        
        integration = Integration.objects.create(**validated_data)
        
        if access_token:
            integration.set_access_token(access_token)
        if refresh_token:
            integration.set_refresh_token(refresh_token)
        integration.save()
        
        return integration
    
    def update(self, instance, validated_data):
        # Encrypt tokens before saving
        access_token = validated_data.pop('access_token', None)
        refresh_token = validated_data.pop('refresh_token', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        if access_token:
            instance.set_access_token(access_token)
        if refresh_token:
            instance.set_refresh_token(refresh_token)
        instance.save()
        
        return instance


class IntegrationAnalyticsSerializer(serializers.ModelSerializer):
    """Analytics data from integrations."""
    platform = serializers.CharField(source='integration.platform_display', read_only=True)
    
    class Meta:
        model = IntegrationAnalytics
        fields = [
            'id', 'integration', 'platform', 'date',
            'impressions', 'clicks', 'engagement', 'reach',
            'conversions', 'leads', 'spend', 'revenue',
            'video_views', 'roi', 'roas', 'synced_at'
        ]
        read_only_fields = ['id', 'synced_at']
