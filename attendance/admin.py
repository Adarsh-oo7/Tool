from django.contrib import admin
from .models import Attendance


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display    = ('user', 'date', 'status', 'approved_by', 'checked_in_at')
    list_filter     = ('status', 'date')
    search_fields   = ('user__full_name',)
    readonly_fields = ('checked_in_at',)
