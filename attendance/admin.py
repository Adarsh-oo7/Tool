from django.contrib import admin
from .models import Attendance


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display    = ('user', 'date', 'check_in_type', 'status', 'approved_by', 'check_in_time', 'distance_from_branch')
    list_filter     = ('status', 'date', 'check_in_type')
    search_fields   = ('user__full_name', 'notes')
    readonly_fields = ('created_at', 'updated_at', 'distance_from_branch')
    list_editable   = ('status',)
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'branch', 'date', 'check_in_type')
        }),
        ('Location & Time', {
            'fields': ('check_in_lat', 'check_in_lng', 'check_in_time', 'check_out_time')
        }),
        ('Status & Approval', {
            'fields': ('status', 'approved_by', 'photo', 'notes')
        }),
        ('System Information', {
            'fields': ('distance_from_branch', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
