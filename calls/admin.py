from django.contrib import admin
from .models import CallLog


@admin.register(CallLog)
class CallLogAdmin(admin.ModelAdmin):
    list_display  = ('lead', 'staff', 'outcome', 'duration_seconds', 'created_at')
    list_filter   = ('outcome',)
    search_fields = ('lead__name', 'staff__full_name')
    readonly_fields = ('created_at',)
