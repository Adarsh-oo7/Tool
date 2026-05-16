from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra):
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        user  = self.model(email=email, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, **extra):
        extra.setdefault('role', 'owner')
        extra.setdefault('is_staff', True)
        extra.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ('owner',       'Owner / Admin'),
        ('manager',     'Branch Manager'),
        ('sub_manager', 'Sub Manager'),
        ('staff',       'Office Staff'),
        ('telecaller',  'Telecaller'),
        ('field_staff', 'Field Staff'),
        ('custom',      'Custom Staff'),
    ]

    STAFF_TYPE_CHOICES = [
        ('field_staff',  'Field Staff'),
        ('office_staff', 'Office Staff'),
        ('telecaller',   'Telecaller'),
        ('custom',       'Custom'),
    ]

    # â”€â”€ Core auth â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    email     = models.EmailField(unique=True)
    full_name = models.CharField(max_length=200)
    phone     = models.CharField(max_length=15, unique=True)
    role      = models.CharField(max_length=20, choices=ROLE_CHOICES, default='staff')
    branch    = models.ForeignKey(
                    'branches.Branch', null=True, blank=True,
                    on_delete=models.SET_NULL, related_name='staff_members')
    avatar    = models.ImageField(upload_to='avatars/', null=True, blank=True)
    fcm_token = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_staff  = models.BooleanField(default=False)
    staff_type       = models.CharField(max_length=20, blank=True)
    staff_type_label = models.CharField(max_length=50, blank=True)

    # â”€â”€ Staff type â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â    # â”€â”€ Profile â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    date_of_birth           = models.DateField(null=True, blank=True)
    address                 = models.TextField(blank=True)
    employee_id             = models.CharField(max_length=20, blank=True)
    join_date               = models.DateField(null=True, blank=True)
    emergency_contact_name  = models.CharField(max_length=100, blank=True)
    emergency_contact_phone = models.CharField(max_length=15, blank=True)
    whatsapp_number         = models.CharField(max_length=15, blank=True)
    marital_status          = models.CharField(
                                max_length=20, 
                                choices=[('married', 'Married'), ('unmarried', 'Unmarried')], 
                                blank=True
                            )
    qualification           = models.CharField(max_length=200, blank=True)
    profile_completed       = models.BooleanField(default=False)
    is_profile_verified     = models.BooleanField(default=False)
    notes                   = models.TextField(blank=True)  # private HR notes
    
    # â”€â”€ Segment Expertise (for smart assignment) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    expert_segments         = models.ManyToManyField(
                                'branches.Segment',
                                blank=True,
                                related_name='expert_staff',
                                help_text="Segments this staff member specializes in"
                            )

    # â”€â”€ Timestamps â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD  = 'email'
    REQUIRED_FIELDS = ['full_name', 'phone']

    class Meta:
        ordering = ['full_name']

    def __str__(self):
        return f'{self.full_name} ({self.get_role_display()})'

    # â”€â”€ Role properties â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    @property
    def is_owner(self):
        return self.role == 'owner'

    @property
    def is_manager(self):
        return self.role == 'manager'

    @property
    def is_sub_manager(self):
        return self.role == 'sub_manager'

    @property
    def is_field_staff(self):
        return self.role == 'field_staff' or self.staff_type == 'field_staff'

    @property
    def display_role(self):
        """Human-readable role â€” uses custom label for custom staff types."""
        if self.role == 'custom' and self.staff_type_label:
            return self.staff_type_label
        return self.get_role_display()

    @property
    def work_anniversary_date(self):
        return self.join_date

    # â”€â”€ Phase 1: Dynamic RBAC Methods â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def has_permission(self, perm_name):
        if self.is_superuser or self.role == 'owner':
            return True
        return perm_name in self.get_all_permissions()

    def get_all_permissions(self):
        if not hasattr(self, '_all_permissions_cache'):
            # 1. Fetch Dynamic RBAC permissions (Phase 1)
            role_perms = Permission.objects.filter(roles__userrole__user=self).values_list('name', flat=True)
            extra_perms = self.extra_permissions.values_list('permission__name', flat=True)
            perms = set(role_perms) | set(extra_perms)

            # 2. Add legacy StaffPermission flags mapped to strings
            if hasattr(self, 'staff_permissions'):
                sp = self.staff_permissions
                mapping = {
                    'can_view_leads':        ['leads:view', 'dashboard:view'],
                    'can_add_leads':         ['leads:create'],
                    'can_edit_leads':        ['leads:edit'],
                    'can_view_attendance':   ['attendance:view', 'attendance:manage'],
                    'can_approve_attendance':['attendance:approve'],
                    'can_view_calls':        ['calls:view'],
                    'can_add_calls':         ['calls:create'],
                    'can_view_sales':        ['sales:view'],
                    'can_add_sales':         ['sales:create'],
                    'can_view_field_visits': ['field_visits:view'],
                    'can_view_reports':      ['reports:view'],
                }
                for field, p_list in mapping.items():
                    if getattr(sp, field, False):
                        perms.update(p_list)
            
            # 3. Default permissions for all active staff
            if self.is_active:
                perms.add('profile:view')
                perms.add('dashboard:view')

            self._all_permissions_cache = perms
        return self._all_permissions_cache



class StaffPermission(models.Model):
    """
    Permission checklist for staff members.
    Auto-created when user role is set to a staff role.
    Admin (owner) can override any field.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='staff_permissions',
    )

    # â”€â”€ Leads â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    can_view_leads   = models.BooleanField(default=True)
    can_add_leads    = models.BooleanField(default=False)
    can_edit_leads   = models.BooleanField(default=False)
    can_assign_leads = models.BooleanField(default=False)
    can_delete_leads = models.BooleanField(default=False)

    # â”€â”€ Staff â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    can_view_staff   = models.BooleanField(default=True)
    can_add_staff    = models.BooleanField(default=False)
    can_edit_staff    = models.BooleanField(default=False)
    can_delete_staff = models.BooleanField(default=False)

    # â”€â”€ Attendance â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    can_view_attendance    = models.BooleanField(default=True)
    can_approve_attendance = models.BooleanField(default=False)

    # â”€â”€ Calls â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    can_view_calls = models.BooleanField(default=False)
    can_add_calls  = models.BooleanField(default=False)

    # â”€â”€ Sales â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    can_view_sales = models.BooleanField(default=False)
    can_add_sales  = models.BooleanField(default=False)

    # â”€â”€ Reports â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    can_view_reports   = models.BooleanField(default=False)
    can_export_reports = models.BooleanField(default=False)

    # â”€â”€ Campaigns â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    can_view_campaigns   = models.BooleanField(default=False)
    can_create_campaigns = models.BooleanField(default=False)

    # â”€â”€ Field visits â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    can_view_field_visits = models.BooleanField(default=False)

    # â”€â”€ Meta â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    modified_by = models.ForeignKey(
        User, null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='permission_changes',
    )
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Permissions — {self.user.full_name}'

    class Meta:
        ordering = ['user__full_name']

    

    @classmethod
    def get_defaults_for(cls, label: str) -> dict:
        """
        Default permissions by sub-manager type label.
        Admin can override after creation.
        """
        presets = {
            'HR Manager': {
                'can_view_staff': True,
                'can_add_staff': True,
                'can_edit_staff': True,
                'can_view_attendance': True,
                'can_approve_attendance': True,
                'can_view_reports': True,
            },
            'Sales Manager': {
                'can_view_leads': True,
                'can_edit_leads': True,
                'can_assign_leads': True,
                'can_view_sales': True,
                'can_add_sales': True,
                'can_view_reports': True,
                'can_view_campaigns': True,
            },
            'Operations Manager': {
                'can_view_leads': True,
                'can_view_staff': True,
                'can_view_attendance': True,
                'can_approve_attendance': True,
                'can_view_field_visits': True,
                'can_view_reports': True,
            },
        }
        return presets.get(label, {})


class ProfileUpdateRequest(models.Model):
    """
    Stores requested profile changes for admin approval.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    user           = models.ForeignKey(User, on_delete=models.CASCADE, related_name='profile_requests')
    requested_data = models.JSONField(help_text="Proposed changes in JSON format")
    status         = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    admin_note     = models.TextField(blank=True)
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Request from {self.user.full_name} ({self.status})"


# Signal: auto-create StaffPermission when role is not owner
@receiver(post_save, sender=User)
def create_staff_permissions(sender, instance, created, **kwargs):
    """
    Automatically creates StaffPermission when a user
    is assigned or updated to a staff role (not owner).
    """
    if instance.role != 'owner':
        obj, new = StaffPermission.objects.get_or_create(user=instance)
        if new and instance.staff_type_label:
            # Apply preset defaults based on sub-manager label
            defaults = StaffPermission.get_defaults_for(instance.staff_type_label)
            for field, value in defaults.items():
                setattr(obj, field, value)
            obj.save()


# â”€â”€ Phase 1: Dynamic RBAC Models â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class Permission(models.Model):
    name = models.CharField(max_length=100, unique=True, help_text="e.g. leads:view")
    description = models.CharField(max_length=255, blank=True)
    module = models.CharField(max_length=50, blank=True, help_text="e.g. CRM, HR")

    def __str__(self):
        return self.name

class Role(models.Model):
    name = models.CharField(max_length=100, unique=True, help_text="e.g. Manager, Telecaller")
    description = models.TextField(blank=True)
    permissions = models.ManyToManyField(Permission, through='RolePermission', related_name='roles')

    def __str__(self):
        return self.name

class RolePermission(models.Model):
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('role', 'permission')

class UserRole(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_roles')
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    
    class Meta:
        unique_together = ('user', 'role')

class UserExtraPermission(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='extra_permissions')
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('user', 'permission')

