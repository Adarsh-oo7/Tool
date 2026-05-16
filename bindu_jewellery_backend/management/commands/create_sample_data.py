from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from datetime import datetime, timedelta
import random

User = get_user_model()

class Command(BaseCommand):
    help = 'Create sample data for testing'

    def handle(self, *args, **options):
        self.stdout.write('Creating sample data...')
        
        # Create admin user if not exists
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@bindujewellery.com',
                'full_name': 'Admin User',
                'phone': '+918011111111',
                'role': 'owner',
                'is_active': True,
                'is_staff': True,
                'is_superuser': True
            }
        )
        
        if created:
            admin_user.set_password('password123')
            admin_user.save()
            self.stdout.write(self.style.SUCCESS(f'Created admin user: {admin_user.username}'))
        else:
            self.stdout.write(f'Admin user already exists: {admin_user.username}')
        
        # Create sample branch
        from branches.models import Branch
        
        branch, created = Branch.objects.get_or_create(
            name='Main Branch - MG Road',
            defaults={
                'address': '123 MG Road, Bangalore',
                'phone': '+918012345678',
                'email': 'mgroad@bindujewellery.com',
                'lat': 12.9716,
                'lng': 77.5946,
                'is_active': True
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created branch: {branch.name}'))
        else:
            self.stdout.write(f'Branch already exists: {branch.name}')
        
        # Create sample users
        users_data = [
            {
                'username': 'manager1',
                'email': 'manager1@bindujewellery.com',
                'full_name': 'Manager One',
                'phone': '+918022222222',
                'role': 'manager',
                'branch': branch,
                'is_staff': True
            },
            {
                'username': 'staff1',
                'email': 'staff1@bindujewellery.com',
                'full_name': 'Staff One',
                'phone': '+918033333333',
                'role': 'staff',
                'branch': branch
            },
            {
                'username': 'telecaller1',
                'email': 'telecaller1@bindujewellery.com',
                'full_name': 'Telecaller One',
                'phone': '+918055555555',
                'role': 'telecaller',
                'branch': branch
            },
            {
                'username': 'fieldstaff1',
                'email': 'fieldstaff1@bindujewellery.com',
                'full_name': 'Field Staff One',
                'phone': '+918066666666',
                'role': 'field_staff',
                'branch': branch
            }
        ]
        
        users = [admin_user]
        for user_data in users_data:
            user, created = User.objects.get_or_create(
                username=user_data['username'],
                defaults={
                    **user_data,
                    'is_active': True,
                    'is_staff': user_data.get('is_staff', False)
                }
            )
            
            if created:
                user.set_password('password123')
                user.save()
                self.stdout.write(self.style.SUCCESS(f'Created user: {user.full_name} ({user.role})'))
            else:
                self.stdout.write(f'User already exists: {user.full_name} ({user.role})')
            
            users.append(user)
        
        # Create sample leads
        from leads.models import Lead
        
        first_names = ['Rahul', 'Priya', 'Amit', 'Sneha', 'Vikram', 'Anjali']
        sources = ['walkin', 'instagram', 'facebook', 'website', 'referral', 'whatsapp']
        
        leads_created = 0
        for i in range(20):
            first_name = random.choice(first_names)
            phone = f'+9198{random.randint(10000000, 99999999)}'
            
            lead_data = {
                'name': f"{first_name} Customer {i+1}",
                'phone': phone,
                'source': random.choice(sources),
                'branch': branch,
                'assigned_to': random.choice(users),
                'stage': random.choice(['new', 'contacted', 'interested', 'scheduled', 'converted', 'lost']),
                'budget': random.choice([25000, 50000, 75000, 100000]),
                'notes': f'Sample lead {i+1} for testing',
                'score': random.randint(20, 95),
                'created_by': admin_user
            }
            
            lead = Lead.objects.create(**lead_data)
            leads_created += 1
        
        self.stdout.write(self.style.SUCCESS(f'Created {leads_created} leads'))
        
        # Create sample sales
        from sales.models import Sale
        
        sales_created = 0
        for i in range(10):
            lead = random.choice(Lead.objects.all())
            
            sale_data = {
                'lead': lead,
                'branch': branch,
                'amount': random.choice([25000, 50000, 75000, 100000]),
                'items': f'Item {i+1}',
                'payment_method': random.choice(['cash', 'card', 'upi']),
                'created_by': admin_user
            }
            
            sale = Sale.objects.create(**sale_data)
            sales_created += 1
            
            # Update lead stage to converted
            lead.stage = 'converted'
            lead.save()
        
        self.stdout.write(self.style.SUCCESS(f'Created {sales_created} sales'))
        
        # Create sample attendance
        from attendance.models import Attendance
        
        today = datetime.now().date()
        attendance_created = 0
        
        for user in users:
            if user.role in ['staff', 'telecaller', 'field_staff']:
                status = random.choice(['present', 'absent', 'late'])
                
                attendance_data = {
                    'user': user,
                    'branch': branch,
                    'date': today,
                    'status': status,
                    'created_by': user
                }
                
                if status == 'present':
                    attendance_data['checkin_time'] = datetime.now().replace(hour=9, minute=0)
                    attendance_data['checkout_time'] = datetime.now().replace(hour=18, minute=0)
                    attendance_data['checkin_lat'] = branch.lat + random.uniform(-0.01, 0.01)
                    attendance_data['checkin_lng'] = branch.lng + random.uniform(-0.01, 0.01)
                
                attendance = Attendance.objects.create(**attendance_data)
                attendance_created += 1
        
        self.stdout.write(self.style.SUCCESS(f'Created {attendance_created} attendance records'))
        
        # Create call logs
        from calls.models import CallLog
        
        call_logs_created = 0
        for i in range(15):
            lead = random.choice(Lead.objects.all())
            
            call_data = {
                'lead': lead,
                'phone': lead.phone,
                'status': random.choice(['connected', 'not_connected', 'busy']),
                'duration': random.randint(0, 1800),
                'notes': f'Call log {i+1}',
                'created_by': admin_user
            }
            
            call_log = CallLog.objects.create(**call_data)
            call_logs_created += 1
        
        self.stdout.write(self.style.SUCCESS(f'Created {call_logs_created} call logs'))
        
        # Create field visits
        from field_visits.models import FieldVisit
        
        field_visits_created = 0
        for i in range(8):
            lead = random.choice(Lead.objects.all())
            field_staff = next((u for u in users if u.role == 'field_staff'), admin_user)
            
            visit_data = {
                'lead': lead,
                'branch': branch,
                'staff': field_staff,
                'purpose': random.choice(['Product demonstration', 'Delivery', 'Measurement']),
                'status': random.choice(['scheduled', 'active', 'completed']),
                'notes': f'Field visit {i+1}',
                'created_by': admin_user
            }
            
            field_visit = FieldVisit.objects.create(**visit_data)
            field_visits_created += 1
        
        self.stdout.write(self.style.SUCCESS(f'Created {field_visits_created} field visits'))
        
        self.stdout.write(self.style.SUCCESS('\n✅ Sample data creation completed!'))
        self.stdout.write('\n📊 Summary:')
        self.stdout.write(f'   Users: {len(users)}')
        self.stdout.write(f'   Leads: {leads_created}')
        self.stdout.write(f'   Sales: {sales_created}')
        self.stdout.write(f'   Attendance Records: {attendance_created}')
        self.stdout.write(f'   Call Logs: {call_logs_created}')
        self.stdout.write(f'   Field Visits: {field_visits_created}')
        
        self.stdout.write('\n🔑 Login Credentials:')
        self.stdout.write('   Username: admin, Password: password123')
        self.stdout.write('   Username: manager1, Password: password123')
        self.stdout.write('   Username: staff1, Password: password123')
        self.stdout.write('   Username: telecaller1, Password: password123')
        self.stdout.write('   Username: fieldstaff1, Password: password123')
