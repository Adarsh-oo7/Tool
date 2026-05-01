from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models


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
        ('owner',       'Owner'),
        ('manager',     'Branch Manager'),
        ('staff',       'Shop Staff'),
        ('telecaller',  'Telecaller'),
        ('field_staff', 'Field Staff'),
    ]

    email      = models.EmailField(unique=True)
    full_name  = models.CharField(max_length=200)
    phone      = models.CharField(max_length=15, unique=True)
    role       = models.CharField(max_length=20, choices=ROLE_CHOICES, default='staff')
    branch     = models.ForeignKey(
                     'branches.Branch', null=True, blank=True,
                     on_delete=models.SET_NULL, related_name='staff_members')
    avatar     = models.ImageField(upload_to='avatars/', null=True, blank=True)
    fcm_token  = models.TextField(blank=True, null=True)
    is_active  = models.BooleanField(default=True)
    is_staff   = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD  = 'email'
    REQUIRED_FIELDS = ['full_name', 'phone']

    class Meta:
        ordering = ['full_name']

    def __str__(self):
        return f'{self.full_name} ({self.role})'

    @property
    def is_owner(self):
        return self.role == 'owner'

    @property
    def is_manager(self):
        return self.role == 'manager'