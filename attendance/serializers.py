from rest_framework import serializers
from .models import Attendance, AttendanceBreak, AttendanceSchedule


class AttendanceScheduleSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source='branch.name', read_only=True)

    class Meta:
        model = AttendanceSchedule
        fields = '__all__'


class AttendanceBreakSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttendanceBreak
        fields = ['id', 'start_time', 'end_time', 'reason']
        read_only_fields = ['id', 'start_time']


class AttendanceSerializer(serializers.ModelSerializer):
    user_name       = serializers.CharField(source='user.full_name', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.full_name', read_only=True)
    status_display  = serializers.CharField(source='get_status_display', read_only=True)
    check_in_type_display = serializers.CharField(source='get_check_in_type_display', read_only=True)
    branch_name = serializers.CharField(source='branch.name', read_only=True)

    breaks = AttendanceBreakSerializer(many=True, read_only=True)
    total_break_time = serializers.FloatField(source='get_total_break_time', read_only=True)
    net_work_time = serializers.FloatField(source='get_net_work_time', read_only=True)

    class Meta:
        model  = Attendance
        fields = [
            'id', 'user', 'user_name', 'branch', 'branch_name', 'date', 
            'check_in_type', 'check_in_type_display',
            'check_in_lat', 'check_in_lng', 'check_in_time', 
            'check_out_time', 'check_out_lat', 'check_out_lng',
            'breaks', 'total_break_time', 'net_work_time',
            'photo', 'status', 'status_display', 'approved_by', 'approved_by_name',
            'distance_from_branch', 'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'date', 'approved_by', 'distance_from_branch']


class GPSCheckInSerializer(serializers.Serializer):
    """Serializer for GPS check-in endpoint"""
    lat = serializers.DecimalField(max_digits=10, decimal_places=7, required=True)
    lng = serializers.DecimalField(max_digits=10, decimal_places=7, required=True)
    notes = serializers.CharField(required=False, allow_blank=True, max_length=500)

    def validate(self, attrs):
        lat = float(attrs['lat'])
        lng = float(attrs['lng'])
        
        if not (-90 <= lat <= 90):
            raise serializers.ValidationError("Latitude must be between -90 and 90")
        if not (-180 <= lng <= 180):
            raise serializers.ValidationError("Longitude must be between -180 and 180")
        
        return attrs


class PhotoCheckInSerializer(serializers.Serializer):
    """Serializer for photo check-in endpoint"""
    photo = serializers.ImageField(required=True)
    notes = serializers.CharField(required=False, allow_blank=True, max_length=500)
