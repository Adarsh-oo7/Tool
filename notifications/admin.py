from django.contrib import admin
from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display    = ('recipient', 'title', 'notif_type', 'is_read', 'created_at')
    list_filter     = ('notif_type', 'is_read')
    search_fields   = ('recipient__full_name', 'title')
    readonly_fields = ('created_at',)
