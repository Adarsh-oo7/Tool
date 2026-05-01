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

    # ── Core auth ─────────────────────────────────────────────────────────────
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

    # ── Staff type ────────────────────────────────────────────────────────────
    staff_type       = models.CharField(max_length=30, choices=STAFF_TYPE_CHOICES, blank=True)
    staff_type_label = models.CharField(max_length=50, blank=True)   # label for custom type

    # ── Profile ───────────────────────────────────────────────────────────────
    date_of_birth           = models.DateField(null=True, blank=True)
    address                 = models.TextField(blank=True)
    employee_id             = models.CharField(max_length=20, blank=True)
    join_date               = models.DateField(null=True, blank=True)
    emergency_contact_name  = models.CharField(max_length=100, blank=True)
    emergency_contact_phone = models.CharField(max_length=15, blank=True)
    notes                   = models.TextField(blank=True)  # private HR notes

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD  = 'email'
    REQUIRED_FIELDS = ['full_name', 'phone']

    class Meta:
        ordering = ['full_name']

    def __str__(self):
        return f'{self.full_name} ({self.get_role_display()})'

    # ── Role properties ───────────────────────────────────────────────────────
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
        """Human-readable role — uses custom label for custom staff types."""
        if self.role == 'custom' and self.staff_type_label:
            return self.staff_type_label
        return self.get_role_display()

    @property
    def work_anniversary_date(self):
        return self.join_date


class SubManagerPermission(models.Model):
    """
    Permission checklist for sub-managers.
    Auto-created when user role is set to sub_manager.
    Admin (owner) can override any field.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='sub_permissions',
        limit_choices_to={'role': 'sub_manager'},
    )

    # ── Leads ─────────────────────────────────────────────────────────────────
    can_view_leads   = models.BooleanField(default=True)
    can_add_leads    = models.BooleanField(default=False)
    can_edit_leads   = models.BooleanField(default=False)
    can_assign_leads = models.BooleanField(default=False)
    can_delete_leads = models.BooleanField(default=False)

    # ── Staff ─────────────────────────────────────────────────────────────────
    can_view_staff   = models.BooleanField(default=True)
    can_add_staff    = models.BooleanField(default=False)
    can_edit_staff   = models.BooleanField(default=False)
    can_delete_staff = models.BooleanField(default=False)

    # ── Attendance ────────────────────────────────────────────────────────────
    can_view_attendance    = models.BooleanField(default=True)
    can_approve_attendance = models.BooleanField(default=False)

    # ── Calls ─────────────────────────────────────────────────────────────────
    can_view_calls = models.BooleanField(default=False)
    can_add_calls  = models.BooleanField(default=False)

    # ── Sales ─────────────────────────────────────────────────────────────────
    can_view_sales = models.BooleanField(default=False)
    can_add_sales  = models.BooleanField(default=False)

    # ── Reports ───────────────────────────────────────────────────────────────
    can_view_reports   = models.BooleanField(default=False)
    can_export_reports = models.BooleanField(default=False)

    # ── Campaigns ─────────────────────────────────────────────────────────────
    can_view_campaigns   = models.BooleanField(default=False)
    can_create_campaigns = models.BooleanField(default=False)

    # ── Field visits ──────────────────────────────────────────────────────────
    can_view_field_visits = models.BooleanField(default=False)

    # ── Meta ──────────────────────────────────────────────────────────────────
    modified_by = models.ForeignKey(
        User, null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='permission_changes',
    )
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Permissions — {self.user.full_name}'

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


# ── Signal: auto-create SubManagerPermission when role = sub_manager ─────────
@receiver(post_save, sender=User)
def create_sub_manager_permissions(sender, instance, created, **kwargs):
    """
    Automatically creates SubManagerPermission when a user
    is assigned or updated to role='sub_manager'.
    """
    if instance.role == 'sub_manager':
        obj, new = SubManagerPermission.objects.get_or_create(user=instance)
        if new and instance.staff_type_label:
            # Apply preset defaults based on sub-manager label
            defaults = SubManagerPermission.get_defaults_for(instance.staff_type_label)
            for field, value in defaults.items():
                setattr(obj, field, value)
            obj.save()