from rest_framework import serializers
from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source='get_notif_type_display', read_only=True)

    class Meta:
        model  = Notification
        fields = [
            'id', 'recipient', 'notif_type', 'type_display',
            'title', 'body', 'is_read', 'data', 'created_at',
        ]
        read_only_fields = ['id', 'recipient', 'created_at']
