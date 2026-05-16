from django.core.management.base import BaseCommand
from accounts.models import Permission, Role, RolePermission, User, UserRole

class Command(BaseCommand):
    help = 'Seed RBAC permissions and roles'

    def handle(self, *args, **kwargs):
        # 1. Define Permissions
        perms = [
            # Dashboard
            ('dashboard:view', 'Can view dashboard'),
            
            # Leads
            ('leads:view', 'Can view leads'),
            ('leads:create', 'Can create leads'),
            ('leads:edit', 'Can edit leads'),
            ('leads:delete', 'Can delete leads'),
            ('leads:assign', 'Can assign leads'),
            
            # Calls
            ('calls:view', 'Can view calls'),
            ('calls:execute', 'Can make calls'),
            
            # Sales
            ('sales:view', 'Can view sales'),
            ('sales:create', 'Can create sales'),
            
            # Staff
            ('staff:view', 'Can view staff'),
            ('staff:manage', 'Can manage staff'),
            
            # Branches
            ('branches:view', 'Can view branches'),
            ('branches:manage', 'Can manage branches'),
            
            # Campaigns
            ('campaigns:view', 'Can view campaigns'),
            ('campaigns:manage', 'Can manage campaigns'),
            
            # Reports
            ('reports:view', 'Can view reports'),
            
            # Attendance
            ('attendance:view', 'Can view attendance'),
            ('attendance:manage', 'Can manage attendance'),
            
            # Field Visits
            ('field_visits:view', 'Can view field visits'),
            ('field_visits:manage', 'Can manage field visits'),

            # Profile
            ('profile:view', 'Can view personal profile'),
        ]

        created_perms = {}
        for name, description in perms:
            perm, created = Permission.objects.get_or_create(name=name, defaults={'description': description})
            created_perms[name] = perm
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created permission: {name}'))

        # 2. Define Roles
        roles_data = {
            'manager': [
                'dashboard:view', 'leads:view', 'leads:create', 'leads:edit', 'leads:assign',
                'calls:view', 'calls:execute', 'sales:view', 'sales:create',
                'staff:view', 'staff:manage', 'attendance:view', 'attendance:manage',
                'field_visits:view', 'field_visits:manage', 'reports:view', 'branches:view', 'profile:view'
            ],
            'sub_manager': [
                'dashboard:view', 'leads:view', 'leads:create', 'leads:edit',
                'calls:view', 'calls:execute', 'sales:view', 'sales:create',
                'attendance:view', 'field_visits:view', 'profile:view'
            ],
            'staff': [
                'dashboard:view', 'leads:view', 'leads:create',
                'calls:view', 'calls:execute', 'sales:view', 'sales:create',
                'attendance:view', 'field_visits:view', 'profile:view'
            ],
            'telecaller': [
                'dashboard:view', 'leads:view', 'calls:view', 'calls:execute',
                'attendance:view', 'profile:view'
            ],
            'field_staff': [
                'dashboard:view', 'leads:view', 'field_visits:view', 'field_visits:manage',
                'attendance:view', 'profile:view'
            ],
        }

        for role_name, perm_names in roles_data.items():
            role_display_name = role_name.replace('_', ' ').title()
            role, created = Role.objects.get_or_create(name=role_display_name)
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created role: {role_display_name}'))
            
            # Assign permissions to role
            for p_name in perm_names:
                if p_name in created_perms:
                    RolePermission.objects.get_or_create(role=role, permission=created_perms[p_name])
        
        # 3. Migrate existing users to UserRole based on their static 'role' field
        users = User.objects.all()
        for user in users:
            if user.role != 'owner':
                role_display_name = user.role.replace('_', ' ').title()
                role = Role.objects.filter(name=role_display_name).first()
                if role:
                    UserRole.objects.get_or_create(user=user, role=role)
                    self.stdout.write(f'Assigned role {role.name} to user {user.email}')
        
        self.stdout.write(self.style.SUCCESS('Successfully seeded RBAC data'))
