from django.contrib import admin
from .models import Campaign, CampaignLead, WhatsAppTemplate, SpecialDayMessage


@admin.register(WhatsAppTemplate)
class WhatsAppTemplateAdmin(admin.ModelAdmin):
    list_display    = ('name', 'trigger', 'is_active', 'created_by', 'created_at')
    list_filter     = ('trigger', 'is_active')
    search_fields   = ('name', 'message')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(SpecialDayMessage)
class SpecialDayMessageAdmin(admin.ModelAdmin):
    list_display    = ('name', 'date', 'send_to_staff', 'send_to_leads', 'is_active')
    list_filter     = ('is_active', 'send_to_staff', 'send_to_leads')
    search_fields   = ('name',)
    readonly_fields = ('created_at',)


class CampaignLeadInline(admin.TabularInline):
    model           = CampaignLead
    extra           = 0
    readonly_fields = ('sent', 'delivered', 'read', 'converted', 'sent_at', 'error')
    fields          = ('lead', 'sent', 'delivered', 'read', 'converted', 'sent_at', 'error')


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display    = ('name', 'branch', 'campaign_type', 'status', 'created_by', 'created_at')
    list_filter     = ('status', 'campaign_type', 'branch')
    search_fields   = ('name',)
    readonly_fields = ('created_at', 'updated_at', 'sent_at')
    inlines         = [CampaignLeadInline]


@admin.register(CampaignLead)
class CampaignLeadAdmin(admin.ModelAdmin):
    list_display  = ('campaign', 'lead', 'sent', 'delivered', 'read', 'converted', 'sent_at')
    list_filter   = ('sent', 'delivered', 'converted')
    search_fields = ('lead__name', 'campaign__name')
    readonly_fields = ('sent_at',)
