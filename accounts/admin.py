from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display    = ('email', 'full_name', 'phone', 'role', 'branch', 'is_active')
    list_filter     = ('role', 'branch', 'is_active')
    search_fields   = ('email', 'full_name', 'phone')
    ordering        = ('full_name',)
    filter_horizontal = ('groups', 'user_permissions')

    fieldsets = (
        (None,            {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('full_name', 'phone', 'avatar', 'fcm_token')}),
        ('Role & Branch', {'fields': ('role', 'branch')}),
        ('Permissions',   {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Timestamps',    {'fields': ('created_at', 'updated_at')}),
    )
    readonly_fields = ('created_at', 'updated_at')

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields':  ('email', 'full_name', 'phone', 'role', 'branch', 'password1', 'password2'),
        }),
    )
