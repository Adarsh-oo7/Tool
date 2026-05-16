"""
Fresh sample data for Bindu Jewellery CRM.
Clears all existing transactional data and creates rich, realistic data
for 3 branches with proper Customer profiles linked to Leads.

Run with:
    python fresh_sample_data.py
"""
import os, django, random
from datetime import datetime, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bindu_jewellery_backend.settings.development')
django.setup()

from django.utils import timezone
from django.contrib.auth import get_user_model
from branches.models import Branch, Segment, Company
from leads.models import Customer, Lead, LeadActivity, FollowUp
from calls.models import CallLog
from field_visits.models import FieldVisit
from sales.models import Sale
from attendance.models import Attendance

User = get_user_model()

# ── Helpers ──────────────────────────────────────────────────────────────────
def rdate(days_ago_max=180, days_ago_min=0):
    return timezone.now() - timedelta(days=random.randint(days_ago_min, days_ago_max))

def rphone():
    return f'9{random.randint(600000000, 999999999)}'

# ── Data pools ────────────────────────────────────────────────────────────────
FIRST_NAMES = [
    'Priya','Anjali','Meera','Kavita','Sunita','Lakshmi','Radha','Sneha','Divya','Pooja',
    'Rahul','Amit','Vikram','Arjun','Rohit','Sanjay','Deepak','Kiran','Suresh','Mahesh',
    'Nisha','Rekha','Usha','Geeta','Shalini','Ravi','Ajay','Vinod','Ramesh','Ganesh',
]
LAST_NAMES = [
    'Sharma','Patel','Reddy','Kumar','Singh','Gupta','Jain','Agarwal','Mishra','Verma',
    'Shah','Mehta','Nair','Pillai','Iyer','Rao','Naidu','Hegde','Gowda','Shetty',
]
OCCASIONS = ['wedding','anniversary','birthday','festival','engagement','gift','']
PRODUCTS  = [
    'Gold Necklace Set','Diamond Ring','Gold Bangles (22kt)','Platinum Wedding Ring',
    'Silver Anklets','Ruby Earrings','Emerald Pendant','Pearl Necklace',
    'Gold Mangalsutra','Diamond Nose Pin','Antique Temple Jewellery','Gold Chain',
]
NOTES_POOL = [
    'Customer looking for bridal set under budget.',
    'Interested in modern lightweight designs.',
    'Traditional South Indian jewellery preference.',
    'Comparing prices, needs follow-up.',
    'Ready to buy, waiting for specific design.',
    'Wants customization on the piece.',
    'Walk-in customer, saw our Instagram ad.',
    'Referred by existing customer Meera Sharma.',
    'Looking for anniversary gift for wife.',
    'Budget flexible if design is right.',
]
STAGES  = ['new','contacted','interested','scheduled','converted','lost']
SOURCES = ['walkin','instagram','facebook','website','referral','whatsapp','other']

# ── STEP 1: CLEAR OLD DATA ────────────────────────────────────────────────────
def clear_data():
    print('🗑  Clearing old transactional data...')
    FollowUp.objects.all().delete()
    LeadActivity.objects.all().delete()
    Lead.objects.all().delete()
    Customer.objects.all().delete()
    Sale.objects.all().delete()
    CallLog.objects.all().delete()
    FieldVisit.objects.all().delete()
    Attendance.objects.all().delete()
    print('   Done.\n')

# ── STEP 2: ENSURE COMPANY + BRANCHES ────────────────────────────────────────
def get_or_create_branches():
    company, _ = Company.objects.get_or_create(
        name='Bindu Jewellery',
        defaults={'address':'Bangalore, Karnataka','phone':'08012345678','email':'info@bindujewellery.com'}
    )
    branch_defs = [
        dict(name='MG Road Branch',    address='123 MG Road, Bangalore',      phone='08012345678', lat=12.9716, lng=77.5946),
        dict(name='Indiranagar Branch',address='456 Indiranagar, Bangalore',   phone='08023456789', lat=12.9786, lng=77.6408),
        dict(name='Jayanagar Branch',  address='789 Jayanagar, Bangalore',     phone='08034567890', lat=12.9267, lng=77.5812),
    ]
    branches = []
    for bd in branch_defs:
        b, created = Branch.objects.get_or_create(name=bd['name'], defaults={**bd,'company':company,'is_active':True})
        branches.append(b)
        print(f'   Branch: {b.name} {"(created)" if created else "(exists)"}')
    return branches

# ── STEP 3: ENSURE SEGMENTS ───────────────────────────────────────────────────
def get_or_create_segments(branches):
    seg_names = ['bridal','daily_wear','diamond','gold','silver','platinum']
    segments = []
    for branch in branches:
        for name in seg_names:
            s, _ = Segment.objects.get_or_create(name=name, branch=branch)
            segments.append(s)
    print(f'   Created/verified {len(segments)} segments across {len(branches)} branches\n')
    return segments

# ── STEP 4: ENSURE USERS ─────────────────────────────────────────────────────
def get_or_create_users(branches):
    user_defs = [
        dict(email='admin@bindujewellery.com',       full_name='Adarsh Shetty (Owner)',   role='owner',       branch=branches[0], phone='9800000001'),
        dict(email='manager.mgroad@bindu.com',       full_name='Rekha Sharma',            role='manager',     branch=branches[0], phone='9800000002'),
        dict(email='manager.indiranagar@bindu.com',  full_name='Vijay Patel',             role='manager',     branch=branches[1], phone='9800000003'),
        dict(email='manager.jayanagar@bindu.com',    full_name='Sunita Reddy',            role='manager',     branch=branches[2], phone='9800000004'),
        dict(email='staff1.mgroad@bindu.com',        full_name='Deepa Nair',              role='staff',       branch=branches[0], phone='9800000005'),
        dict(email='staff2.mgroad@bindu.com',        full_name='Kiran Gupta',             role='staff',       branch=branches[0], phone='9800000006'),
        dict(email='staff1.indiranagar@bindu.com',   full_name='Ravi Iyer',               role='staff',       branch=branches[1], phone='9800000007'),
        dict(email='staff1.jayanagar@bindu.com',     full_name='Meena Rao',               role='staff',       branch=branches[2], phone='9800000008'),
        dict(email='tele1@bindu.com',                full_name='Preethi Shetty',          role='telecaller',  branch=branches[0], phone='9800000009'),
        dict(email='tele2@bindu.com',                full_name='Akash Singh',             role='telecaller',  branch=branches[1], phone='9800000010'),
        dict(email='field1@bindu.com',               full_name='Mohan Gowda',             role='field_staff', branch=branches[0], phone='9800000011'),
        dict(email='field2@bindu.com',               full_name='Suresh Hegde',            role='field_staff', branch=branches[2], phone='9800000012'),
    ]
    users = []
    for ud in user_defs:
        u, created = User.objects.get_or_create(email=ud['email'], defaults={**ud,'is_active':True,'is_staff':ud['role'] in ['owner','manager']})
        if created:
            u.set_password('password123')
            u.save()
        users.append(u)
        print(f'   User: {u.full_name} ({u.role} @ {u.branch.name}) {"(created)" if created else "(exists)"}')
    # Assign managers to branches
    for u in users:
        if u.role == 'manager':
            u.branch.manager = u
            u.branch.save()
    return users

# ── STEP 5: CREATE CUSTOMERS + LEADS ─────────────────────────────────────────
def create_customers_and_leads(branches, segments, users):
    print('\n👥 Creating Customers & Leads...')
    all_leads = []

    # Customer definitions: each gets 1–3 leads across different branches
    customer_profiles = [
        dict(name='Priya Sharma',     phone='9611111101', email='priya.sharma@gmail.com',  age=28, gender='female', location='Indiranagar', occasions=[{'type':'wedding','date':'2024-11-15'}], budget_range='₹1L–₹2L'),
        dict(name='Anjali Reddy',     phone='9611111102', email='anjali.r@gmail.com',       age=34, gender='female', location='Jayanagar',   occasions=[{'type':'anniversary','date':'2024-12-20'}], budget_range='₹50K–₹1L'),
        dict(name='Meera Patel',      phone='9611111103', email='meera.p@gmail.com',        age=26, gender='female', location='MG Road',     occasions=[{'type':'engagement','date':'2025-01-10'}], budget_range='₹75K–₹1.5L'),
        dict(name='Kavita Singh',     phone='9611111104', email='kavita.s@gmail.com',       age=42, gender='female', location='Koramangala', occasions=[], budget_range='₹25K–₹50K'),
        dict(name='Sunita Gupta',     phone='9611111105', email='sunita.g@gmail.com',       age=38, gender='female', location='Whitefield',  occasions=[{'type':'birthday','date':'2025-03-05'}], budget_range='₹30K–₹80K'),
        dict(name='Rahul Kumar',      phone='9611111106', email='rahul.k@gmail.com',        age=31, gender='male',   location='HSR Layout',  occasions=[], budget_range='₹50K–₹1L'),
        dict(name='Amit Jain',        phone='9611111107', email='amit.j@gmail.com',         age=45, gender='male',   location='Malleswaram', occasions=[{'type':'anniversary','date':'2025-02-14'}], budget_range='₹1L–₹3L'),
        dict(name='Vikram Agarwal',   phone='9611111108', email='vikram.a@gmail.com',       age=29, gender='male',   location='Rajajinagar', occasions=[], budget_range='₹20K–₹40K'),
        dict(name='Divya Nair',       phone='9611111109', email='divya.n@gmail.com',        age=24, gender='female', location='JP Nagar',    occasions=[{'type':'wedding','date':'2025-06-20'}], budget_range='₹2L–₹5L'),
        dict(name='Pooja Verma',      phone='9611111110', email='pooja.v@gmail.com',        age=33, gender='female', location='Banashankari',occasions=[{'type':'festival','date':'2025-04-14'}], budget_range='₹15K–₹30K'),
        dict(name='Rohit Mehta',      phone='9611111111', email='rohit.m@gmail.com',        age=36, gender='male',   location='Marathahalli',occasions=[], budget_range='₹40K–₹90K'),
        dict(name='Sneha Rao',        phone='9611111112', email='sneha.r@gmail.com',        age=27, gender='female', location='Electronic City', occasions=[{'type':'engagement','date':'2025-05-01'}], budget_range='₹80K–₹2L'),
        dict(name='Lakshmi Iyer',     phone='9611111113', email='lakshmi.i@gmail.com',      age=52, gender='female', location='Basavanagudi',occasions=[{'type':'anniversary','date':'2025-07-10'}], budget_range='₹1.5L–₹4L'),
        dict(name='Sanjay Hegde',     phone='9611111114', email='sanjay.h@gmail.com',       age=48, gender='male',   location='Sadashivanagar',occasions=[],budget_range='₹2L–₹6L'),
        dict(name='Geeta Pillai',     phone='9611111115', email='geeta.p@gmail.com',        age=39, gender='female', location='Vijayanagar', occasions=[{'type':'birthday','date':'2025-08-22'}], budget_range='₹10K–₹25K'),
        dict(name='Ravi Gowda',       phone='9611111116', email='ravi.g@gmail.com',         age=41, gender='male',   location='Nagarbhavi',  occasions=[], budget_range='₹60K–₹1.2L'),
        dict(name='Usha Shetty',      phone='9611111117', email='usha.s@gmail.com',         age=55, gender='female', location='Yeshwantpur', occasions=[{'type':'anniversary','date':'2025-09-30'}], budget_range='₹3L–₹8L'),
        dict(name='Deepak Mishra',    phone='9611111118', email='deepak.m@gmail.com',       age=30, gender='male',   location='Hebbal',      occasions=[], budget_range='₹25K–₹60K'),
        dict(name='Rekha Naidu',      phone='9611111119', email='rekha.n@gmail.com',        age=44, gender='female', location='RT Nagar',    occasions=[{'type':'festival','date':'2025-10-02'}], budget_range='₹50K–₹1.5L'),
        dict(name='Suresh Shah',      phone='9611111120', email='suresh.s@gmail.com',       age=37, gender='male',   location='Frazer Town', occasions=[], budget_range='₹75K–₹2L'),
    ]

    created_customers = []
    for cp in customer_profiles:
        occasions = cp.pop('occasions', [])
        budget_range = cp.pop('budget_range', '')
        cust = Customer.objects.create(
            **cp,
            budget_range=budget_range,
            occasions=occasions,
        )
        created_customers.append(cust)

        # Add 1–3 leads per customer across branches
        num_leads = random.randint(1, 3)
        for l_idx in range(num_leads):
            branch = branches[l_idx % len(branches)]
            stage = random.choice(STAGES)
            days_ago = random.randint(1, 150)
            staff_in_branch = [u for u in users if u.branch == branch and u.role in ['staff','telecaller']]
            assigned = random.choice(staff_in_branch) if staff_in_branch else random.choice(users)
            segs_in_branch = [s for s in segments if s.branch == branch]

            lead = Lead.objects.create(
                customer=cust,
                name=cust.name,
                phone=cust.phone,
                email=cust.email,
                age=cust.age,
                gender=cust.gender,
                source=random.choice(SOURCES),
                branch=branch,
                segment=random.choice(segs_in_branch) if segs_in_branch else None,
                assigned_to=assigned,
                created_by=assigned,
                stage=stage,
                budget=random.choice([25000,50000,75000,100000,150000,200000,300000]),
                occasion=random.choice(OCCASIONS),
                product_interest=random.choice(PRODUCTS),
                notes=random.choice(NOTES_POOL),
                recommendations='Consider showing the bridal collection and antique pieces.' if stage in ['interested','scheduled'] else '',
                score=random.randint(20,95),
                is_hot=stage in ['interested','scheduled','converted'],
            )
            # Backdate created_at
            Lead.objects.filter(pk=lead.pk).update(created_at=timezone.now()-timedelta(days=days_ago))

            # Add timeline event
            cust.add_timeline_event('lead_created', {
                'source': lead.source,
                'branch': branch.name,
                'stage': stage,
            })

            # Add 1–3 follow-ups per lead
            for _ in range(random.randint(1, 3)):
                scheduled = timezone.now() + timedelta(days=random.randint(-10, 30))
                completed = scheduled < timezone.now()
                FollowUp.objects.create(
                    lead=lead,
                    followup_type=random.choice(['call','whatsapp','visit']),
                    scheduled_date=scheduled,
                    note=random.choice(NOTES_POOL),
                    completed=completed,
                    created_by=assigned,
                )

            # Add lead activity
            LeadActivity.objects.create(
                lead=lead,
                actor=assigned,
                action='lead_created',
                detail=f'Lead created via {lead.source}',
            )
            if stage != 'new':
                LeadActivity.objects.create(
                    lead=lead,
                    actor=assigned,
                    action='stage_change',
                    detail=f'Stage moved to {stage}',
                )

            all_leads.append(lead)

    print(f'   Created {len(created_customers)} customers, {len(all_leads)} leads\n')
    return created_customers, all_leads

# ── STEP 6: CALL LOGS ─────────────────────────────────────────────────────────
def create_call_logs(leads, users):
    print('📞 Creating Call Logs...')
    outcomes = ['no_answer','interested','not_interested','call_later','converted','busy']
    notes = [
        'Customer wants to visit the showroom next weekend.',
        'Not interested right now, call after Diwali.',
        'Interested in gold bangles, asked for price.',
        'Scheduled a visit for Saturday 11am.',
        'Sale confirmed — coming to collect tomorrow.',
        'Busy, requested callback at 6pm.',
        'Spoke for 10 minutes, very interested in bridal set.',
        'No answer — try again tomorrow.',
    ]
    count = 0
    for lead in leads:
        n = random.randint(1, 5)
        for _ in range(n):
            staff_list = [u for u in users if u.branch == lead.branch]
            staff = random.choice(staff_list) if staff_list else random.choice(users)
            cl = CallLog.objects.create(
                lead=lead,
                outcome=random.choice(outcomes),
                duration_seconds=random.randint(0, 1200),
                notes=random.choice(notes),
                staff=staff,
            )
            # Add to customer timeline
            if lead.customer:
                lead.customer.add_timeline_event('call', {
                    'outcome': cl.outcome,
                    'duration': cl.duration_seconds,
                    'notes': cl.notes,
                    'staff': staff.full_name,
                })
            count += 1
    print(f'   Created {count} call logs\n')

# ── STEP 7: SALES ─────────────────────────────────────────────────────────────
def create_sales(leads, users):
    print('💰 Creating Sales...')
    converted_leads = [l for l in leads if l.stage == 'converted']
    products = ['Gold Necklace Set','Diamond Ring','Gold Bangles 22kt','Platinum Band',
                'Silver Anklets','Ruby Earrings','Emerald Pendant','Pearl Set','Mangalsutra']
    count = 0
    for lead in converted_leads:
        staff_list = [u for u in users if u.branch == lead.branch]
        staff = random.choice(staff_list) if staff_list else random.choice(users)
        amount = random.choice([25000,35000,50000,75000,100000,125000,150000,200000,250000])
        Sale.objects.create(
            lead=lead,
            branch=lead.branch,
            amount=amount,
            product_name=random.choice(products),
            staff=staff,
        )
        if lead.customer:
            lead.customer.update_purchase_stats(amount)
        count += 1
    print(f'   Created {count} sales\n')

# ── STEP 8: FIELD VISITS ──────────────────────────────────────────────────────
def create_field_visits(leads, users):
    print('🗺  Creating Field Visits...')
    field_staff = [u for u in users if u.role == 'field_staff']
    if not field_staff:
        field_staff = users[:2]
    count = 0
    for lead in random.sample(leads, min(20, len(leads))):
        staff = next((u for u in field_staff if u.branch == lead.branch), random.choice(field_staff))
        status = random.choice(['active','completed','cancelled','completed','completed'])
        b = lead.branch
        slat = float(b.lat) + random.uniform(-0.05, 0.05)
        slng = float(b.lng) + random.uniform(-0.05, 0.05)
        fv_data = dict(lead=lead, branch=b, staff=staff, status=status, start_lat=slat, start_lng=slng)
        if status == 'completed':
            fv_data.update(
                end_lat=slat + random.uniform(-0.01, 0.01),
                end_lng=slng + random.uniform(-0.01, 0.01),
                duration_minutes=random.randint(20, 120),
                distance_km=round(random.uniform(1.0, 15.0), 2),
                ended_at=timezone.now() - timedelta(hours=random.randint(0, 48)),
                notes='Visit completed successfully.',
            )
            if lead.customer:
                lead.customer.add_timeline_event('visit_completed', {'staff': staff.full_name, 'duration_mins': fv_data['duration_minutes']})
        fv = FieldVisit.objects.create(**fv_data)
        FieldVisit.objects.filter(pk=fv.pk).update(started_at=timezone.now() - timedelta(hours=random.randint(1, 72)))
        count += 1
    print(f'   Created {count} field visits\n')

# ── STEP 9: ATTENDANCE ────────────────────────────────────────────────────────
def create_attendance(users, branches):
    print('📅 Creating Attendance...')
    today = timezone.localdate()
    count = 0
    for i in range(14):  # last 2 weeks
        date = today - timedelta(days=i)
        if date.weekday() == 6:  # skip Sunday
            continue
        for user in users:
            if user.role not in ['staff','telecaller','field_staff']:
                continue
            status = random.choices(['present','absent','late','half_day'], weights=[75,8,12,5])[0]
            ci = timezone.make_aware(datetime.combine(date, datetime.strptime('09:30','%H:%M').time())) + timedelta(minutes=random.randint(-20,60))
            co = timezone.make_aware(datetime.combine(date, datetime.strptime('18:30','%H:%M').time())) + timedelta(minutes=random.randint(-60,60))
            data = dict(user=user, branch=user.branch, date=date, status=status, check_in_time=ci, check_out_time=co)
            if status in ['present','late']:
                data['check_in_lat'] = float(user.branch.lat) + random.uniform(-0.01,0.01)
                data['check_in_lng'] = float(user.branch.lng) + random.uniform(-0.01,0.01)
            _, created = Attendance.objects.update_or_create(user=user, date=date, defaults=data)
            if created:
                count += 1
    print(f'   Created {count} attendance records\n')

# ── UPDATE CUSTOMER INTERACTION STATS ────────────────────────────────────────
def update_customer_stats():
    print('📊 Updating customer interaction stats...')
    for cust in Customer.objects.all():
        calls = CallLog.objects.filter(lead__customer=cust).count()
        visits = FieldVisit.objects.filter(lead__customer=cust, status='completed').count()
        cust.total_calls = calls
        cust.total_visits = visits
        if calls or visits:
            cust.last_contact_date = timezone.now() - timedelta(days=random.randint(0, 30))
        cust.save(update_fields=['total_calls','total_visits','last_contact_date'])
    print('   Done.\n')

# ── MAIN ──────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    print('=' * 55)
    print('  BINDU JEWELLERY — Fresh Sample Data Generator')
    print('=' * 55 + '\n')

    clear_data()

    print('🏢 Setting up Branches & Segments...')
    branches = get_or_create_branches()
    segments = get_or_create_segments(branches)

    print('👤 Setting up Users...')
    users = get_or_create_users(branches)

    customers, leads = create_customers_and_leads(branches, segments, users)
    create_call_logs(leads, users)
    create_sales(leads, users)
    create_field_visits(leads, users)
    create_attendance(users, branches)
    update_customer_stats()

    print('=' * 55)
    print('✅  Done! Summary:')
    print(f'   Branches  : {len(branches)}')
    print(f'   Users     : {len(users)}')
    print(f'   Customers : {Customer.objects.count()}')
    print(f'   Leads     : {Lead.objects.count()}')
    print(f'   Call Logs : {CallLog.objects.count()}')
    print(f'   Sales     : {Sale.objects.count()}')
    print(f'   Attendance: {Attendance.objects.count()}')
    print()
    print('🔑 Login Credentials (password: password123):')
    print('   admin@bindujewellery.com        → Owner (sees all branches)')
    print('   manager.mgroad@bindu.com        → Manager, MG Road')
    print('   manager.indiranagar@bindu.com   → Manager, Indiranagar')
    print('   manager.jayanagar@bindu.com     → Manager, Jayanagar')
    print('   staff1.mgroad@bindu.com         → Staff, MG Road')
    print('   tele1@bindu.com                 → Telecaller, MG Road')
    print('   field1@bindu.com                → Field Staff, MG Road')
    print('=' * 55)
