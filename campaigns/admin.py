from django.contrib import admin
from .models import Campaign, CampaignLead


class CampaignLeadInline(admin.TabularInline):
    model           = CampaignLead
    extra           = 0
    readonly_fields = ('sent', 'delivered', 'converted', 'sent_at')


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display    = ('name', 'branch', 'campaign_type', 'status', 'created_by', 'created_at')
    list_filter     = ('status', 'campaign_type', 'branch')
    search_fields   = ('name',)
    readonly_fields = ('created_at', 'updated_at')
    inlines         = [CampaignLeadInline]


@admin.register(CampaignLead)
class CampaignLeadAdmin(admin.ModelAdmin):
    list_display  = ('campaign', 'lead', 'sent', 'delivered', 'converted', 'sent_at')
    list_filter   = ('sent', 'delivered', 'converted')
