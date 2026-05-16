"""
Populate actual branch data for Bindu Jewellery with realistic leads and sales.
Branches: SULLIA, MANGALURU, KASARAGOD.
"""
import os, django, random
from datetime import datetime, timedelta
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bindu_jewellery_backend.settings.development')
django.setup()

from django.contrib.auth import get_user_model
from branches.models import Branch, Segment, Company
from leads.models import Customer, Lead, LeadActivity, FollowUp
from calls.models import CallLog
from field_visits.models import FieldVisit
from sales.models import Sale
from attendance.models import Attendance

User = get_user_model()

# ── Helpers ──────────────────────────────────────────────────────────────────
def rdate(days_ago_max=90, days_ago_min=0):
    return timezone.now() - timedelta(days=random.randint(days_ago_min, days_ago_max))

def rphone():
    return f'9{random.randint(600000000, 999999999)}'

# ── Data pools ────────────────────────────────────────────────────────────────
FIRST_NAMES = ['Priya','Anjali','Meera','Kavita','Sunita','Lakshmi','Radha','Sneha','Divya','Pooja','Rahul','Amit','Vikram','Arjun','Rohit']
LAST_NAMES = ['Sharma','Patel','Reddy','Kumar','Singh','Gupta','Jain','Agarwal','Mishra','Verma','Shetty','Gowda','Rai','Hegde']
STAGES  = ['new','contacted','interested','scheduled','converted','lost']
SOURCES = ['walkin', 'instagram', 'facebook', 'website', 'referral', 'whatsapp']
PRODUCTS = ['Gold Necklace', 'Diamond Ring', 'Gold Bangles', 'Silver Anklets', 'Temple Jewellery']

# ── STEP 1: CLEAR OLD DATA ────────────────────────────────────────────────────
def clear_data():
    print('Clearing old transactional data...')
    FollowUp.objects.all().delete()
    LeadActivity.objects.all().delete()
    Lead.objects.all().delete()
    Customer.objects.all().delete()
    Sale.objects.all().delete()
    CallLog.objects.all().delete()
    FieldVisit.objects.all().delete()
    Attendance.objects.all().delete()
    
    # Clear all non-superuser accounts
    print('Clearing all non-superuser users...')
    User.objects.filter(is_superuser=False).delete()
    
    print('Done.\n')

# ── STEP 2: ENSURE COMPANY + BRANCHES ────────────────────────────────────────
def setup_branches():
    company, _ = Company.objects.get_or_create(
        name='Bindu Jewellery',
        defaults={'address':'Mangaluru, Karnataka', 'email':'bindujewellerymangalore@gmail.com'}
    )
    branch_defs = [
        dict(name='SULLIA', address='Opposite Police Station, Sullia-574239', phone='8113929916'),
        dict(name='MANGALURU', address='Near SCS Hospital, Bendore, Mangaluru', phone='8296120400'),
        dict(name='KASARAGOD', address='NH-17, Ashwini Nagar, Kasaragod 671121', phone='9847020400'),
    ]
    branches = []
    for bd in branch_defs:
        b, created = Branch.objects.get_or_create(name=bd['name'], defaults={**bd, 'company':company})
        branches.append(b)
        print(f'   Branch: {b.name} {"(created)" if created else "(exists)"}')
    return branches

# ── STEP 3: ENSURE USERS ─────────────────────────────────────────────────────
def setup_users(branches):
    user_defs = [
        dict(email='admin@bindujewellery.com',  full_name='Adarsh Shetty', role='owner', branch=branches[1], phone='9800000001'),
        dict(email='sullia.mgr@bindu.com',      full_name='Suresh Rai',    role='manager', branch=branches[0], phone='9800000002'),
        dict(email='mangalore.mgr@bindu.com',   full_name='Rekha Shetty',  role='manager', branch=branches[1], phone='9800000003'),
        dict(email='kasaragod.mgr@bindu.com',   full_name='Abdul Rahman',  role='manager', branch=branches[2], phone='9800000004'),
        dict(email='staff.sullia@bindu.com',    full_name='Kiran Kumar',   role='staff', branch=branches[0], phone='9800000005'),
        dict(email='staff.mangalore@bindu.com',  full_name='Deepa Nair',    role='staff', branch=branches[1], phone='9800000006'),
        dict(email='staff.kasaragod@bindu.com',  full_name='Meena Rao',     role='staff', branch=branches[2], phone='9800000007'),
    ]
    users = []
    for ud in user_defs:
        u, created = User.objects.get_or_create(email=ud['email'], defaults={**ud, 'is_active':True})
        if created:
            u.set_password('password123')
            u.save()
        users.append(u)
    return users

# ── STEP 4: CREATE LEADS & SALES ─────────────────────────────────────────────
def seed_leads_and_sales(branches, users):
    print('\nSeeding Leads & Sales...')
    for branch in branches:
        # Create 15-20 leads per branch
        for _ in range(random.randint(15, 25)):
            name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
            phone = rphone()
            cust = Customer.objects.create(name=name, phone=phone, location=branch.name)
            
            stage = random.choice(STAGES)
            staff = random.choice([u for u in users if u.branch == branch and u.role == 'staff'] or users)
            
            lead = Lead.objects.create(
                customer=cust, name=name, phone=phone, branch=branch,
                assigned_to=staff, stage=stage, source=random.choice(SOURCES),
                product_interest=random.choice(PRODUCTS),
                budget=random.randint(10000, 200000)
            )
            # Backdate
            Lead.objects.filter(pk=lead.pk).update(created_at=rdate())

            if stage == 'converted':
                Sale.objects.create(
                    lead=lead, branch=branch, staff=staff,
                    product_name=lead.product_interest,
                    amount=lead.budget or 50000
                )
    print('   Done.')

if __name__ == '__main__':
    clear_data()
    branches = setup_branches()
    users = setup_users(branches)
    seed_leads_and_sales(branches, users)
    print('\nActual database populated with branch data and fresh leads!')
