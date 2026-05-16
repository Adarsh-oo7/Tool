import os
import django
from datetime import datetime, timedelta
import random

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bindu_jewellery_backend.settings.development')
django.setup()

from django.contrib.auth import get_user_model
from branches.models import Company, Branch, Segment
from leads.models import Lead
from sales.models import Sale
from calls.models import CallLog

User = get_user_model()

def add_branches_data():
    print("Creating sample branches data...")
    
    # Create or get company
    company, _ = Company.objects.get_or_create(
        name='Bindu Jewellery',
        defaults={
            'address': '123 MG Road, Bangalore',
            'phone': '919876543210',
            'email': 'info@bindujewellery.com'
        }
    )
    print(f"Company: {company.name}")
    
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
            'name': 'Jayanagar Branch',
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
            print(f'Created branch: {branch.name}')
        else:
            print(f'Branch already exists: {branch.name}')
    
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
    phone_counter = 1000
    for branch in branches:
        for role in roles:
            for i in range(2):
                email = f'{role}_{branch.name.lower().replace(" ", "_")}_{i+1}@bindujewellery.com'
                phone = f'9198765{phone_counter}'
                phone_counter += 1
                
                # Generate random date of birth (between 22 and 55 years old)
                dob = datetime.now().date() - timedelta(days=random.randint(22*365, 55*365))
                # Generate random join date (between 1 and 10 years ago)
                join_date = datetime.now().date() - timedelta(days=random.randint(365, 10*365))
                
                user, created = User.objects.get_or_create(
                    email=email,
                    defaults={
                        'full_name': f'{role.title()} {i+1} - {branch.name}',
                        'phone': phone,
                        'role': role,
                        'branch': branch,
                        'is_active': True,
                        'date_of_birth': dob,
                        'join_date': join_date
                    }
                )
                if created:
                    user.set_password('password123')
                    user.save()
                    print(f'Created user: {email}')
    
    # Create sample leads for each branch
    print("\nCreating sample leads...")
    lead_stages = ['new', 'contacted', 'interested', 'scheduled', 'converted', 'lost']
    first_names = ['Rahul', 'Priya', 'Amit', 'Sneha', 'Vikram', 'Anjali', 'Rohit', 'Kavita', 'Arjun', 'Meera']
    last_names = ['Sharma', 'Patel', 'Reddy', 'Kumar', 'Singh', 'Gupta', 'Jain', 'Agarwal', 'Mishra', 'Verma']
    sources = ['walkin', 'instagram', 'facebook', 'website', 'referral', 'whatsapp']
    
    for branch in branches:
        staff_users = User.objects.filter(branch=branch, role='staff')
        branch_segments = Segment.objects.filter(branch=branch)
        for i in range(30):
            first_name = random.choice(first_names)
            last_name = random.choice(last_names)
            phone = f'+9198{random.randint(10000000, 99999999)}'
            email = f"{first_name.lower()}.{last_name.lower()}{i}@example.com"
            
            lead_data = {
                'name': f"{first_name} {last_name}",
                'phone': phone,
                'email': email,
                'age': random.randint(22, 55),
                'gender': random.choice(['male', 'female', 'other']),
                'source': random.choice(sources),
                'branch': branch,
                'segment': branch_segments.first() if branch_segments.exists() else None,
                'assigned_to': staff_users.first() if staff_users.exists() else None,
                'stage': random.choice(lead_stages),
                'budget': random.choice([25000, 50000, 75000, 100000, 150000, 200000]),
                'occasion': random.choice(['wedding', 'anniversary', 'birthday', 'gift', '']),
                'product_interest': random.choice(['Gold Necklace', 'Diamond Ring', 'Silver Earrings', 'Platinum Bracelet', '']),
                'notes': f'Customer interested in {random.choice(["traditional", "modern", "fusion"])} designs.',
                'score': random.randint(20, 95),
                'is_hot': random.choice([True, False])
            }
            
            Lead.objects.get_or_create(
                phone=phone,
                defaults=lead_data
            )
    
    print(f"Created {Lead.objects.count()} leads")
    
    # Create sample sales for each branch
    print("\nCreating sample sales...")
    for branch in branches:
        staff_users = User.objects.filter(branch=branch, role='staff')
        branch_leads = Lead.objects.filter(branch=branch, stage='converted')
        branch_segments = Segment.objects.filter(branch=branch)
        
        for i in range(20):
            if branch_leads.exists():
                lead = random.choice(list(branch_leads))
                segment = branch_segments.first() if branch_segments.exists() else None
                sale_data = {
                    'lead': lead,
                    'branch': branch,
                    'staff': staff_users.first() if staff_users.exists() else None,
                    'product_name': f'{segment.name.replace("_", " ").title() if segment else "Gold"} Item',
                    'amount': random.randint(10000, 500000),
                    'weight_grams': round(random.uniform(5, 50), 2),
                    'segment': segment if segment else None
                }
                
                Sale.objects.get_or_create(
                    lead=lead,
                    defaults=sale_data
                )
    
    print(f"Created {Sale.objects.count()} sales")
    
    # Create sample call logs for each branch
    print("\nCreating sample call logs...")
    call_outcomes = ['no_answer', 'interested', 'not_interested', 'call_later', 'converted']
    for branch in branches:
        staff_users = User.objects.filter(branch=branch, role='staff')
        branch_leads = Lead.objects.filter(branch=branch)
        
        for i in range(25):
            if branch_leads.exists() and staff_users.exists():
                lead = random.choice(list(branch_leads))
                staff = staff_users.first()
                call_data = {
                    'lead': lead,
                    'staff': staff,
                    'outcome': random.choice(call_outcomes),
                    'duration_seconds': random.randint(30, 600),
                    'notes': random.choice([
                        'Customer interested in gold collection',
                        'Follow-up scheduled for next week',
                        'Customer asked for price details',
                        'Call back requested',
                        'Not interested right now',
                        'Will visit the store tomorrow'
                    ]),
                    'next_followup_date': datetime.now().date() + timedelta(days=random.randint(1, 7)) if random.random() > 0.5 else None
                }
                
                CallLog.objects.create(**call_data)
    
    print(f"Created {CallLog.objects.count()} call logs")
    
    print(f"\n✅ Sample branches data created successfully!")
    print(f"📊 Summary:")
    print(f"   Branches: {len(branches)}")
    print(f"   Users: {User.objects.count()}")
    print(f"   Segments: {Segment.objects.count()}")
    print(f"   Leads: {Lead.objects.count()}")
    print(f"   Sales: {Sale.objects.count()}")
    print(f"   Call Logs: {CallLog.objects.count()}")
    
    print("\n🔑 Login Credentials (password: password123):")
    for branch in branches:
        staff_users = User.objects.filter(branch=branch, role='staff')
        manager_users = User.objects.filter(branch=branch, role='manager')
        if staff_users.exists():
            print(f"   {branch.name} Staff: {staff_users.first().email}")
        if manager_users.exists():
            print(f"   {branch.name} Manager: {manager_users.first().email}")

if __name__ == '__main__':
    add_branches_data()
