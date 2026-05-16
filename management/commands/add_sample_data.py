from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from branches.models import Company, Branch, Segment
from leads.models import Lead
from sales.models import Sale
from calls.models import Call
from campaigns.models import Campaign
from attendance.models import Attendance
from field_visits.models import FieldVisit
from datetime import datetime, timedelta
import random

User = get_user_model()

class Command(BaseCommand):
    help = 'Add sample data for testing branch filters and charts'

    def handle(self, *args, **options):
        self.stdout.write('Creating sample data...')
        
        # Create or get company
        company, _ = Company.objects.get_or_create(
            name='Bindu Jewellery',
            defaults={
                'address': '123 MG Road, Bangalore',
                'phone': '919876543210',
                'email': 'info@bindujewellery.com'
            }
        )
        
        # Create branches
        branches_data = [
            {
                'name': 'MG Road Branch',
                'address': '123 MG Road, Bangalore',
                'phone': '919876543211',
                'lat': 12.9756,
                'lng': 77.6066
            },
            {
                'name': 'Indiranagar Branch',
                'address': '456 12th Main, Indiranagar, Bangalore',
                'phone': '919876543212',
                'lat': 12.9719,
                'lng': 77.6412
            },
            {
                'name': 'Koramangala Branch',
                'address': '789 5th Block, Koramangala, Bangalore',
                'phone': '919876543213',
                'lat': 12.9352,
                'lng': 77.6245
            },
            {
                'name': 'Jayangar Branch',
                'address': '321 4th Block, Jayanagar, Bangalore',
                'phone': '919876543214',
                'lat': 12.9298,
                'lng': 77.5802
            },
            {
                'name': 'Whitefield Branch',
                'address': '654 Phoenix Mall, Whitefield, Bangalore',
                'phone': '919876543215',
                'lat': 12.9698,
                'lng': 77.7498
            }
        ]
        
        branches = []
        for branch_data in branches_data:
            branch, created = Branch.objects.get_or_create(
                company=company,
                name=branch_data['name'],
                defaults=branch_data
            )
            branches.append(branch)
            if created:
                self.stdout.write(f'Created branch: {branch.name}')
            else:
                self.stdout.write(f'Branch already exists: {branch.name}')
        
        # Add segments to each branch
        segment_choices = ['bridal', 'daily_wear', 'investment', 'diamond']
        for branch in branches:
            for seg_choice in segment_choices:
                Segment.objects.get_or_create(
                    branch=branch,
                    name=seg_choice,
                    defaults={'description': f'{seg_choice.replace("_", " ").title()} collection'}
                )
        
        # Create sample users for each branch
        roles = ['staff', 'manager']
        for branch in branches:
            for role in roles:
                for i in range(2):
                    username = f'{role}_{branch.name.lower().replace(" ", "_")}_{i+1}'
                    email = f'{username}@bindujewellery.com'
                    user, created = User.objects.get_or_create(
                        username=username,
                        defaults={
                            'email': email,
                            'full_name': f'{role.title()} {i+1} - {branch.name}',
                            'phone': f'9198765432{random.randint(00, 99)}',
                            'role': role,
                            'branch': branch,
                            'is_active': True
                        }
                    )
                    if created:
                        user.set_password('password123')
                        user.save()
                        self.stdout.write(f'Created user: {username}')
        
        # Create sample leads for each branch
        lead_stages = ['new', 'contacted', 'qualified', 'proposal', 'negotiation', 'won', 'lost']
        for branch in branches:
            for i in range(20):
                Lead.objects.get_or_create(
                    name=f'Lead {i+1} - {branch.name}',
                    defaults={
                        'phone': f'9198765433{random.randint(00, 99)}',
                        'email': f'lead{i+1}@example.com',
                        'branch': branch,
                        'stage': random.choice(lead_stages),
                        'source': random.choice(['website', 'referral', 'walk_in', 'social_media', 'advertisement']),
                        'assigned_to': User.objects.filter(branch=branch, role='staff').first(),
                        'status': 'active'
                    }
                )
        
        # Create sample sales for each branch
        segments = ['bridal', 'daily_wear', 'investment', 'diamond']
        for branch in branches:
            for i in range(15):
                Sale.objects.get_or_create(
                    lead=Lead.objects.filter(branch=branch).order_by('?').first(),
                    defaults={
                        'branch': branch,
                        'staff': User.objects.filter(branch=branch, role='staff').first(),
                        'product_name': f'{random.choice(segments).replace("_", " ").title()} Item',
                        'amount': random.randint(10000, 500000),
                        'weight': round(random.uniform(5, 50), 2),
                        'segment': random.choice(segments),
                        'sale_date': datetime.now() - timedelta(days=random.randint(0, 30))
                    }
                )
        
        # Create sample calls for each branch
        call_outcomes = ['answered', 'not_answered', 'voicemail', 'callback', 'interested', 'not_interested']
        for branch in branches:
            for i in range(25):
                Call.objects.get_or_create(
                    lead=Lead.objects.filter(branch=branch).order_by('?').first(),
                    defaults={
                        'branch': branch,
                        'staff': User.objects.filter(branch=branch, role='staff').first(),
                        'call_time': datetime.now() - timedelta(days=random.randint(0, 30)),
                        'duration': random.randint(1, 30),
                        'outcome': random.choice(call_outcomes),
                        'notes': f'Call notes for call {i+1}'
                    }
                )
        
        # Create sample campaigns for each branch
        campaign_types = ['email', 'social_media', 'print', 'radio', 'tv']
        for branch in branches:
            for i in range(5):
                Campaign.objects.get_or_create(
                    name=f'Campaign {i+1} - {branch.name}',
                    defaults={
                        'branch': branch,
                        'type': random.choice(campaign_types),
                        'start_date': datetime.now() - timedelta(days=random.randint(10, 60)),
                        'end_date': datetime.now() + timedelta(days=random.randint(0, 30)),
                        'budget': random.randint(50000, 500000),
                        'status': random.choice(['active', 'completed', 'scheduled']),
                        'reach': random.randint(1000, 10000)
                    }
                )
        
        # Create sample attendance for each branch
        attendance_statuses = ['present', 'late', 'absent']
        for branch in branches:
            staff_users = User.objects.filter(branch=branch, role='staff')
            for user in staff_users:
                for day in range(30):
                    date = datetime.now() - timedelta(days=day)
                    Attendance.objects.get_or_create(
                        user=user,
                        date=date.strftime('%Y-%m-%d'),
                        defaults={
                            'branch': branch,
                            'status': random.choice(attendance_statuses),
                            'check_in_time': date.replace(hour=9, minute=random.randint(0, 30)),
                            'check_out_time': date.replace(hour=18, minute=random.randint(0, 30)),
                            'check_in_lat': branch.lat,
                            'check_in_lng': branch.lng
                        }
                    )
        
        # Create sample field visits for each branch
        visit_statuses = ['in_progress', 'completed', 'cancelled']
        for branch in branches:
            for i in range(10):
                FieldVisit.objects.get_or_create(
                    lead=Lead.objects.filter(branch=branch).order_by('?').first(),
                    defaults={
                        'branch': branch,
                        'staff': User.objects.filter(branch=branch, role='staff').first(),
                        'status': random.choice(visit_statuses),
                        'started_at': datetime.now() - timedelta(days=random.randint(0, 30)),
                        'ended_at': datetime.now() - timedelta(days=random.randint(0, 29)) if random.random() > 0.3 else None,
                        'duration_minutes': random.randint(30, 120),
                        'start_lat': branch.lat,
                        'start_lng': branch.lng,
                        'end_lat': branch.lat + random.uniform(-0.01, 0.01),
                        'end_lng': branch.lng + random.uniform(-0.01, 0.01),
                        'distance_km': round(random.uniform(1, 10), 2),
                        'notes': f'Field visit notes for visit {i+1}'
                    }
                )
        
        self.stdout.write(self.style.SUCCESS('Sample data created successfully!'))
        self.stdout.write(f'Created {len(branches)} branches')
        self.stdout.write(f'Created {User.objects.count()} users')
        self.stdout.write(f'Created {Lead.objects.count()} leads')
        self.stdout.write(f'Created {Sale.objects.count()} sales')
        self.stdout.write(f'Created {Call.objects.count()} calls')
        self.stdout.write(f'Created {Campaign.objects.count()} campaigns')
        self.stdout.write(f'Created {Attendance.objects.count()} attendance records')
        self.stdout.write(f'Created {FieldVisit.objects.count()} field visits')
