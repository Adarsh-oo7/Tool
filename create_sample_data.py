import os
import django
from datetime import datetime, timedelta
import random

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bindu_jewellery_backend.settings.development')
django.setup()

from django.contrib.auth import get_user_model
from branches.models import Branch, Segment
from leads.models import Lead
from sales.models import Sale
from attendance.models import Attendance
from calls.models import CallLog
from field_visits.models import FieldVisit
from gamification.models import Badge, UserBadge, GamificationProfile
from alerts.models import AlertType, AlertRule

User = get_user_model()

def create_sample_data():
    print("Creating sample data...")
    
    from branches.models import Company
    
    # Create company
    company, _ = Company.objects.get_or_create(
        name='Bindu Jewellery',
        defaults={
            'address': 'Bangalore, Karnataka',
            'phone': '+918012345678',
            'email': 'info@bindujewellery.com'
        }
    )
    
    # Create branches
    branches_data = [
        {
            'name': 'Main Branch - MG Road',
            'company': company,
            'address': '123 MG Road, Bangalore',
            'phone': '+918012345678',
            'lat': 12.9716,
            'lng': 77.5946,
            'is_active': True
        },
        {
            'name': 'Indiranagar Branch',
            'company': company,
            'address': '456 Indiranagar, Bangalore',
            'phone': '+918023456789',
            'lat': 12.9786,
            'lng': 77.6408,
            'is_active': True
        },
        {
            'name': 'Jayanagar Branch',
            'company': company,
            'address': '789 Jayanagar, Bangalore',
            'phone': '+918034567890',
            'lat': 12.9267,
            'lng': 77.5812,
            'is_active': True
        }
    ]
    
    branches = []
    for branch_data in branches_data:
        branch, created = Branch.objects.get_or_create(
            name=branch_data['name'],
            defaults=branch_data
        )
        branches.append(branch)
        print(f"Branch: {branch.name} - {'Created' if created else 'Exists'}")
    
    # Create segments
    segments_data = [
        {'name': 'bridal', 'description': 'High-value bridal customers'},
        {'name': 'daily_wear', 'description': 'Regular daily wear customers'},
        {'name': 'diamond', 'description': 'Diamond collection customers'}
    ]
    
    segments = []
    # Create segments for the first branch just for simplicity
    for seg_data in segments_data:
        segment, created = Segment.objects.get_or_create(
            name=seg_data['name'],
            branch=branches[0],
            defaults={'description': seg_data['description']}
        )
        segments.append(segment)
        print(f"Segment: {segment.get_name_display()} - {'Created' if created else 'Exists'}")
    
    # Create users
    users_data = [
        {
            'email': 'admin@bindujewellery.com',
            'full_name': 'Admin User',
            'phone': '+918011111111',
            'role': 'owner',
            'branch': branches[0]
        },
        {
            'email': 'manager1@bindujewellery.com',
            'full_name': 'Manager One',
            'phone': '+918022222222',
            'role': 'manager',
            'branch': branches[0]
        },
        {
            'email': 'staff1@bindujewellery.com',
            'full_name': 'Staff One',
            'phone': '+918033333333',
            'role': 'staff',
            'branch': branches[0]
        },
        {
            'email': 'staff2@bindujewellery.com',
            'full_name': 'Staff Two',
            'phone': '+918044444444',
            'role': 'staff',
            'branch': branches[1]
        },
        {
            'email': 'telecaller1@bindujewellery.com',
            'full_name': 'Telecaller One',
            'phone': '+918055555555',
            'role': 'telecaller',
            'branch': branches[0]
        },
        {
            'email': 'fieldstaff1@bindujewellery.com',
            'full_name': 'Field Staff One',
            'phone': '+918066666666',
            'role': 'field_staff',
            'branch': branches[0]
        }
    ]
    
    users = []
    for user_data in users_data:
        user, created = User.objects.get_or_create(
            email=user_data['email'],
            defaults={
                **user_data,
                'is_active': True,
                'is_staff': user_data['role'] in ['owner', 'manager']
            }
        )
        if created:
            user.set_password('password123')
            user.save()
        users.append(user)
        print(f"User: {user.full_name} ({user.role}) - {'Created' if created else 'Exists'}")
    
    # Assign managers to branches
    for i, branch in enumerate(branches):
        if i < len(users) and users[i].role == 'manager':
            branch.manager = users[i]
            branch.save()
    
    # Create leads
    first_names = ['Rahul', 'Priya', 'Amit', 'Sneha', 'Vikram', 'Anjali', 'Rohit', 'Kavita', 'Arjun', 'Meera']
    last_names = ['Sharma', 'Patel', 'Reddy', 'Kumar', 'Singh', 'Gupta', 'Jain', 'Agarwal', 'Mishra', 'Verma']
    sources = ['walkin', 'instagram', 'facebook', 'website', 'referral', 'whatsapp']
    
    leads = []
    for i in range(50):
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
            'branch': random.choice(branches),
            'segment': random.choice(segments),
            'assigned_to': random.choice(users),
            'stage': random.choice(['new', 'contacted', 'interested', 'scheduled', 'converted', 'lost']),
            'budget': random.choice([25000, 50000, 75000, 100000, 150000, 200000]),
            'occasion': random.choice(['wedding', 'anniversary', 'birthday', 'gift', '']),
            'product_interest': random.choice(['Gold Necklace', 'Diamond Ring', 'Silver Earrings', 'Platinum Bracelet', '']),
            'notes': f'Customer interested in {random.choice(["traditional", "modern", "fusion"])} designs.',
            'score': random.randint(20, 95),
            'is_hot': random.choice([True, False]),
            'created_by': random.choice(users)
        }
        
        lead = Lead.objects.create(**lead_data)
        leads.append(lead)
    
    print(f"Created {len(leads)} leads")
    
    # Create sales
    sales = []
    for i in range(30):
        lead = random.choice(leads)
        sale_data = {
            'lead': lead,
            'branch': lead.branch,
            'amount': random.choice([15000, 25000, 35000, 50000, 75000, 100000, 125000]),
            'product_name': random.choice(["Gold Necklace", "Diamond Ring", "Silver Earrings", "Platinum Bracelet"]),
            'staff': random.choice(users)
        }
        
        sale = Sale.objects.create(**sale_data)
        sales.append(sale)
        # Update lead stage to converted
        lead.stage = 'converted'
        lead.save()
    
    print(f"Created {len(sales)} sales")
    
    # Create attendance records
    attendance_records = []
    from django.utils import timezone
    today = timezone.localdate()
    
    for i in range(7):
        date = today - timedelta(days=i)
        for user in users:
            if user.role in ['staff', 'telecaller', 'field_staff']:
                # Random attendance status
                status = random.choices(
                    ['present', 'absent', 'late', 'half_day'],
                    weights=[70, 10, 15, 5]
                )[0]
                
                check_in = timezone.make_aware(datetime.combine(date, datetime.strptime('09:00', '%H:%M').time())) + timedelta(minutes=random.randint(-30, 30))
                check_out = timezone.make_aware(datetime.combine(date, datetime.strptime('18:00', '%H:%M').time())) + timedelta(minutes=random.randint(-60, 60))
                
                attendance_data = {
                    'user': user,
                    'branch': user.branch,
                    'date': date,
                    'status': status,
                    'check_in_time': check_in,
                    'check_out_time': check_out,
                }
                
                if status == 'present':
                    attendance_data['check_in_lat'] = float(user.branch.lat) + random.uniform(-0.01, 0.01)
                    attendance_data['check_in_lng'] = float(user.branch.lng) + random.uniform(-0.01, 0.01)
                
                attendance, created = Attendance.objects.update_or_create(
                    user=user,
                    date=date,
                    defaults=attendance_data
                )
                if created:
                    attendance_records.append(attendance)
    
    print(f"Created {len(attendance_records)} attendance records")
    
    # Create call logs
    call_logs = []
    for i in range(40):
        lead = random.choice(leads)
        call_data = {
            'lead': lead,
            'outcome': random.choice(['no_answer', 'interested', 'not_interested', 'call_later', 'converted']),
            'duration_seconds': random.randint(0, 1800),  # 0 to 30 minutes
            'notes': random.choice([
                'Customer interested in gold collection',
                'Follow-up scheduled for next week',
                'Customer asked for price details',
                'Call back requested',
                'Not interested right now'
            ]),
            'staff': random.choice(users)
        }
        
        call_log = CallLog.objects.create(**call_data)
        call_logs.append(call_log)
    
    print(f"Created {len(call_logs)} call logs")
    
    # Create field visits
    field_visits = []
    for i in range(20):
        lead = random.choice(leads)
        visit_data = {
            'lead': lead,
            'branch': lead.branch,
            'staff': random.choice([u for u in users if u.role == 'field_staff']) or users[0],
            'status': random.choice(['active', 'completed', 'cancelled']),
        }
        
        if visit_data['status'] in ['active', 'completed']:
            visit_data['start_lat'] = float(lead.branch.lat) + random.uniform(-0.05, 0.05)
            visit_data['start_lng'] = float(lead.branch.lng) + random.uniform(-0.05, 0.05)
        
        if visit_data['status'] == 'completed':
            visit_data['end_lat'] = visit_data['start_lat'] + random.uniform(-0.01, 0.01)
            visit_data['end_lng'] = visit_data['start_lng'] + random.uniform(-0.01, 0.01)
            visit_data['duration_minutes'] = random.randint(30, 120)
            visit_data['distance_km'] = random.uniform(1.0, 15.0)
            visit_data['ended_at'] = timezone.now() - timedelta(hours=random.randint(0, 4))
        
        field_visit = FieldVisit.objects.create(**visit_data)
        
        # Override auto_now_add started_at
        field_visit.started_at = timezone.now() - timedelta(hours=random.randint(1, 8))
        field_visit.save(update_fields=['started_at'])
        
        field_visits.append(field_visit)
    
    print(f"Created {len(field_visits)} field visits")
    
    # Create gamification profiles
    for user in users:
        profile, created = GamificationProfile.objects.get_or_create(
            user=user,
            defaults={
                'total_points': random.randint(100, 2500),
                'current_level': random.randint(1, 8),
                'level_name': random.choice(['Beginner', 'Intermediate', 'Senior', 'Bronze', 'Silver', 'Gold']),
                'badges_count': random.randint(0, 15),
                'achievements_count': random.randint(0, 10),
                'streak_days': random.randint(0, 30),
                'last_activity_date': datetime.now().date() - timedelta(days=random.randint(0, 7))
            }
        )
        print(f"Gamification profile for {user.full_name} - {'Created' if created else 'Exists'}")
    
    # Create badges
    badges_data = [
        {
            'name': 'First Sale',
            'description': 'Made your first sale',
            'badge_type': 'sales',
            'icon': '🏆',
            'points': 50,
            'criteria': {'sales_count': 1}
        },
        {
            'name': 'Sales Champion',
            'description': 'Achieved 10 sales in a month',
            'badge_type': 'sales',
            'icon': '🥇',
            'points': 200,
            'criteria': {'monthly_sales': 10}
        },
        {
            'name': 'Lead Generator',
            'description': 'Generated 50 leads',
            'badge_type': 'leads',
            'icon': '🎯',
            'points': 100,
            'criteria': {'total_leads': 50}
        },
        {
            'name': 'Perfect Attendance',
            'description': 'Perfect attendance for a week',
            'badge_type': 'attendance',
            'icon': '⭐',
            'points': 75,
            'criteria': {'perfect_week': True}
        },
        {
            'name': 'Call Expert',
            'description': 'Made 100 successful calls',
            'badge_type': 'calls',
            'icon': '📞',
            'points': 150,
            'criteria': {'calls_made': 100}
        }
    ]
    
    badges = []
    for badge_data in badges_data:
        badge, created = Badge.objects.get_or_create(
            name=badge_data['name'],
            defaults=badge_data
        )
        badges.append(badge)
        print(f"Badge: {badge.name} - {'Created' if created else 'Exists'}")
    
    # Award some badges to users
    for user in users:
        for badge in random.sample(badges, random.randint(1, 3)):
            user_badge, created = UserBadge.objects.get_or_create(
                user=user,
                badge=badge,
                defaults={'points_earned': badge.points}
            )
            if created:
                print(f"Awarded badge '{badge.name}' to {user.full_name}")
    
    # Create alert types and rules
    alert_types_data = [
        {
            'name': 'Low Sales Alert',
            'category': 'performance',
            'severity': 'high',
            'description': 'Alert when sales are below target',
            'template_message': 'Sales are {current_value}, which is below the threshold of {threshold}',
            'default_enabled': True
        },
        {
            'name': 'High Lead Conversion',
            'category': 'performance',
            'severity': 'low',
            'description': 'Alert when lead conversion is high',
            'template_message': 'Great job! Lead conversion is {current_value}%',
            'default_enabled': True
        },
        {
            'name': 'Attendance Alert',
            'category': 'activity',
            'severity': 'medium',
            'description': 'Alert when attendance is low',
            'template_message': 'Attendance rate is {current_value}%',
            'default_enabled': True
        }
    ]
    
    for alert_type_data in alert_types_data:
        alert_type, created = AlertType.objects.get_or_create(
            name=alert_type_data['name'],
            defaults=alert_type_data
        )
        print(f"Alert Type: {alert_type.name} - {'Created' if created else 'Exists'}")
    
    print("\n✅ Sample data creation completed!")
    print("\n📊 Summary:")
    print(f"   Branches: {len(branches)}")
    print(f"   Users: {len(users)}")
    print(f"   Leads: {len(leads)}")
    print(f"   Sales: {len(sales)}")
    print(f"   Attendance Records: {len(attendance_records)}")
    print(f"   Call Logs: {len(call_logs)}")
    print(f"   Field Visits: {len(field_visits)}")
    print(f"   Badges: {len(badges)}")
    
    print("\n🔑 Login Credentials:")
    print("   Username: admin, Password: password123")
    print("   Username: manager1, Password: password123")
    print("   Username: staff1, Password: password123")
    print("   Username: telecaller1, Password: password123")
    print("   Username: fieldstaff1, Password: password123")

if __name__ == '__main__':
    create_sample_data()
