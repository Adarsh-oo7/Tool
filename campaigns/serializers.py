from rest_framework import serializers
from .models import Campaign, CampaignLead


class CampaignLeadSerializer(serializers.ModelSerializer):
    lead_name  = serializers.CharField(source='lead.name', read_only=True)
    lead_phone = serializers.CharField(source='lead.phone', read_only=True)

    class Meta:
        model  = CampaignLead
        fields = [
            'id', 'campaign', 'lead', 'lead_name', 'lead_phone',
            'sent', 'delivered', 'converted', 'sent_at',
        ]
        read_only_fields = ['id', 'sent', 'delivered', 'converted', 'sent_at']


class CampaignSerializer(serializers.ModelSerializer):
    campaign_leads    = CampaignLeadSerializer(many=True, read_only=True)
    created_by_name   = serializers.CharField(source='created_by.full_name', read_only=True)
    branch_name       = serializers.CharField(source='branch.name', read_only=True)
    status_display    = serializers.CharField(source='get_status_display', read_only=True)
    type_display      = serializers.CharField(source='get_campaign_type_display', read_only=True)
    total_leads       = serializers.SerializerMethodField()
    sent_count        = serializers.SerializerMethodField()

    class Meta:
        model  = Campaign
        fields = [
            'id', 'name', 'branch', 'branch_name', 'segment',
            'campaign_type', 'type_display', 'template_name', 'message',
            'status', 'status_display', 'scheduled_at',
            'created_by', 'created_by_name', 'created_at', 'updated_at',
            'total_leads', 'sent_count', 'campaign_leads',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by']

    def get_total_leads(self, obj):
        return obj.campaign_leads.count()

    def get_sent_count(self, obj):
        return obj.campaign_leads.filter(sent=True).count()
