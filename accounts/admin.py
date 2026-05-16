from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, StaffPermission


class StaffPermissionInline(admin.StackedInline):
    model      = StaffPermission
    extra      = 0
    can_delete = False
    verbose_name = 'Staff Permissions'


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display    = ('full_name', 'email', 'phone', 'role', 'branch', 'is_active', 'created_at')
    list_filter     = ('role', 'branch', 'is_active', 'staff_type')
    search_fields   = ('full_name', 'email', 'phone', 'employee_id')
    ordering        = ('full_name',)
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Credentials',   {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('full_name', 'phone', 'avatar', 'date_of_birth', 'address')}),
        ('Role & Branch', {'fields': ('role', 'branch', 'staff_type', 'staff_type_label')}),
        ('HR Info',       {'fields': ('employee_id', 'join_date', 'emergency_contact_name',
                                      'emergency_contact_phone', 'notes')}),
        ('System',        {'fields': ('is_active', 'is_staff', 'is_superuser', 'fcm_token',
                                      'created_at', 'updated_at')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields':  ('email', 'full_name', 'phone', 'role', 'branch', 'password1', 'password2'),
        }),
    )

    def get_inlines(self, request, obj=None):
        if obj and obj.role != 'owner':
            return [StaffPermissionInline]
        return []


@admin.register(StaffPermission)
class StaffPermissionAdmin(admin.ModelAdmin):
    list_display  = ('user', 'can_view_leads', 'can_add_staff', 'can_approve_attendance',
                     'can_view_reports', 'can_create_campaigns', 'updated_at')
    list_filter   = ('can_view_leads', 'can_approve_attendance')
    search_fields = ('user__full_name',)
    readonly_fields = ('updated_at',)
