from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Full user detail — used for profile read/update."""
    branch_name = serializers.CharField(source='branch.name', read_only=True)

    class Meta:
        model  = User
        fields = [
            'id', 'email', 'full_name', 'phone', 'role',
            'branch', 'branch_name', 'avatar', 'fcm_token',
            'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'email', 'created_at', 'updated_at']


class UserListSerializer(serializers.ModelSerializer):
    """Lightweight list representation."""
    branch_name = serializers.CharField(source='branch.name', read_only=True)

    class Meta:
        model  = User
        fields = ['id', 'full_name', 'email', 'phone', 'role', 'branch_name', 'is_active']


class RegisterSerializer(serializers.ModelSerializer):
    password  = serializers.CharField(write_only=True, min_length=8)
    password2 = serializers.CharField(write_only=True, label='Confirm Password')

    class Meta:
        model  = User
        fields = ['email', 'full_name', 'phone', 'role', 'branch', 'password', 'password2']

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


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Old password is incorrect.')
        return value

    def save(self):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()


class FCMTokenSerializer(serializers.Serializer):
    fcm_token = serializers.CharField()


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Adds user info to the JWT login response."""

    def validate(self, attrs):
        data = super().validate(attrs)
        data['user'] = UserSerializer(self.user).data
        return data
