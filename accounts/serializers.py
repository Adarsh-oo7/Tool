from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import StaffPermission, ProfileUpdateRequest

User = get_user_model()


class StaffPermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = StaffPermission
        fields = '__all__'


class StaffListSerializer(serializers.ModelSerializer):
    """Lightweight list — for dropdowns and assignment selects."""
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    display_role = serializers.CharField(read_only=True)

    class Meta:
        model  = User
        fields = [
            'id', 'full_name', 'email', 'phone', 'role', 'display_role', 
            'branch_name', 'branch', 'is_active', 'avatar',
            'whatsapp_number', 'marital_status', 'qualification',
            'date_of_birth', 'join_date', 'employee_id', 'address',
            'emergency_contact_name', 'emergency_contact_phone', 'notes'
        ]


class UserSerializer(serializers.ModelSerializer):
    """Full user detail — used for profile read/update."""
    branch_name  = serializers.CharField(source='branch.name', read_only=True)
    display_role = serializers.CharField(read_only=True)

    permissions = StaffPermissionSerializer(source='staff_permissions', read_only=True)
    all_permissions = serializers.SerializerMethodField()

    class Meta:
        model  = User
        fields = [
            'id', 'email', 'full_name', 'phone', 'role', 'display_role',
            'branch', 'branch_name', 'avatar', 'fcm_token',
            'staff_type', 'staff_type_label',
            'date_of_birth', 'address', 'employee_id', 'join_date',
            'emergency_contact_name', 'emergency_contact_phone',
            'whatsapp_number', 'marital_status', 'qualification',
            'profile_completed', 'is_profile_verified',
            'permissions', 'all_permissions',
            'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'email', 'created_at', 'updated_at', 'is_profile_verified']

    def get_all_permissions(self, obj):
        return list(obj.get_all_permissions())


class UserCreateSerializer(serializers.ModelSerializer):
    """Create a new staff user — owner only."""
    password  = serializers.CharField(write_only=True, min_length=8)
    password2 = serializers.CharField(write_only=True, label='Confirm Password')

    class Meta:
        model  = User
        fields = [
            'email', 'full_name', 'phone', 'role', 'branch',
            'staff_type', 'staff_type_label', 'employee_id', 'join_date',
            'password', 'password2',
        ]

    def validate(self, data):
        if data['password'] != data.pop('password2'):
            raise serializers.ValidationError({'password2': 'Passwords do not match.'})
        return data

    def create(self, validated_data):
        password = validated_data.pop('password')
        user     = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    """Partial update — no password, no role changes (use SetRoleView)."""
    class Meta:
        model  = User
        fields = [
            'full_name', 'phone', 'avatar', 'fcm_token',
            'staff_type', 'staff_type_label',
            'date_of_birth', 'address', 'employee_id', 'join_date',
            'emergency_contact_name', 'emergency_contact_phone', 
            'whatsapp_number', 'marital_status', 'qualification',
            'notes',
        ]


class ProfileUpdateRequestSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.full_name', read_only=True)

    class Meta:
        model  = ProfileUpdateRequest
        fields = '__all__'
        read_only_fields = ['user', 'status', 'created_at', 'updated_at']


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Old password is incorrect.')
        return value

    def validate(self, data):
        if data.get('old_password') == data.get('new_password'):
            raise serializers.ValidationError({'new_password': 'New password must differ from old password.'})
        return data

    def save(self):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()


class FCMTokenSerializer(serializers.Serializer):
    fcm_token = serializers.CharField()


class StaffPermissionSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.full_name', read_only=True)

    class Meta:
        model  = StaffPermission
        fields = [
            'id', 'user', 'user_name',
            'can_view_leads', 'can_add_leads', 'can_edit_leads',
            'can_assign_leads', 'can_delete_leads',
            'can_view_staff', 'can_add_staff', 'can_edit_staff', 'can_delete_staff',
            'can_view_attendance', 'can_approve_attendance',
            'can_view_calls', 'can_add_calls',
            'can_view_sales', 'can_add_sales',
            'can_view_reports', 'can_export_reports',
            'can_view_campaigns', 'can_create_campaigns',
            'can_view_field_visits',
            'modified_by', 'updated_at',
        ]
        read_only_fields = ['id', 'updated_at', 'modified_by']


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Adds user info to the JWT login response."""

    def validate(self, attrs):
        data = super().validate(attrs)
        data['user'] = UserSerializer(self.user).data
        return data
