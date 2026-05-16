from django.contrib import admin
from .models import Lead, LeadActivity, FollowUp


class LeadActivityInline(admin.TabularInline):
    model           = LeadActivity
    extra           = 0
    readonly_fields = ('created_at',)


class FollowUpInline(admin.TabularInline):
    model = FollowUp
    extra = 0


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display    = ('name', 'phone', 'stage', 'source', 'branch', 'assigned_to', 'is_hot', 'score', 'created_at')
    list_filter     = ('stage', 'source', 'branch', 'segment', 'is_hot')
    search_fields   = ('name', 'phone', 'email')
    ordering        = ('-created_at',)
    inlines         = [LeadActivityInline, FollowUpInline]
    readonly_fields = ('score', 'created_at', 'updated_at')


@admin.register(LeadActivity)
class LeadActivityAdmin(admin.ModelAdmin):
    list_display    = ('lead', 'action', 'actor', 'created_at')
    list_filter     = ('action',)
    readonly_fields = ('created_at',)


@admin.register(FollowUp)
class FollowUpAdmin(admin.ModelAdmin):
    list_display  = ('lead', 'scheduled_date', 'completed', 'created_by')
    list_filter   = ('completed',)
