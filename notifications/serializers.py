from rest_framework import serializers
from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source='get_notif_type_display', read_only=True)
    sender_name  = serializers.CharField(source='sender.full_name', read_only=True)

    class Meta:
        model  = Notification
        fields = [
            'id', 'recipient', 'sender', 'sender_name', 'notif_type', 'type_display',
            'title', 'body', 'image', 'is_broadcast', 'is_read', 'data', 'created_at',
        ]
        read_only_fields = ['id', 'sender', 'created_at']
