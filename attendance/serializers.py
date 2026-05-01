from rest_framework import serializers
from .models import Attendance


class AttendanceSerializer(serializers.ModelSerializer):
    user_name       = serializers.CharField(source='user.full_name', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.full_name', read_only=True)
    status_display  = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model  = Attendance
        fields = [
            'id', 'user', 'user_name', 'date', 'check_in_lat', 'check_in_lng',
            'photo', 'status', 'status_display', 'approved_by', 'approved_by_name',
            'checked_in_at',
        ]
        read_only_fields = ['id', 'user', 'date', 'checked_in_at', 'approved_by', 'status']
