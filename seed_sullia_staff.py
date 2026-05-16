from django.contrib.auth import get_user_model
from branches.models import Branch

User = get_user_model()
sullia = Branch.objects.get(name='SULLIA')

# roles: manager, staff, telecaller, field_staff
staff_types = [
    ('sullia.manager@bindu.com', 'manager', 'Sullia Manager', '9000000021'),
    ('sullia.staff@bindu.com', 'staff', 'Sullia General Staff', '9000000022'),
    ('sullia.tele@bindu.com', 'telecaller', 'Sullia Telecaller', '9000000023'),
    ('sullia.field@bindu.com', 'field_staff', 'Sullia Field Staff', '9000000024'),
]

for email, role, name, phone in staff_types:
    user, created = User.objects.get_or_create(
        email=email,
        defaults={
            'full_name': name,
            'phone': phone,
            'role': role,
            'branch': sullia,
            'is_active': True,
            'is_staff': True
        }
    )
    if created:
        user.set_password('pass123')
        user.save()
        print(f"Created {role}: {email}")
    else:
        user.role = role
        user.branch = sullia
        user.phone = phone
        user.is_active = True
        user.save()
        print(f"Updated {role}: {email}")

print("Sullia branch staff seeding complete.")
