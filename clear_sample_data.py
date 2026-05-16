import os
import django

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bindu_jewellery_backend.settings.development')
django.setup()

from django.contrib.auth import get_user_model
from branches.models import Company, Branch, Segment
from leads.models import Lead
from sales.models import Sale
from calls.models import CallLog
from campaigns.models import Campaign
from attendance.models import Attendance
from field_visits.models import FieldVisit

User = get_user_model()

def clear_sample_data():
    print("Clearing existing sample data...")
    
    # Clear in reverse order of dependencies
    print("Clearing field visits...")
    FieldVisit.objects.all().delete()
    
    print("Clearing attendance...")
    Attendance.objects.all().delete()
    
    print("Clearing campaigns...")
    Campaign.objects.all().delete()
    
    print("Clearing calls...")
    CallLog.objects.all().delete()
    
    print("Clearing sales...")
    Sale.objects.all().delete()
    
    print("Clearing leads...")
    Lead.objects.all().delete()
    
    print("Clearing users (except owner)...")
    User.objects.filter(role__in=['staff', 'manager', 'telecaller', 'field_staff']).delete()
    
    print("Clearing segments...")
    Segment.objects.all().delete()
    
    print("Clearing branches...")
    Branch.objects.all().delete()
    
    print("Clearing companies...")
    Company.objects.all().delete()
    
    print("\n✅ All sample data cleared successfully!")
    print(f"📊 Remaining data:")
    print(f"   Users: {User.objects.count()}")
    print(f"   Branches: {Branch.objects.count()}")
    print(f"   Leads: {Lead.objects.count()}")
    print(f"   Sales: {Sale.objects.count()}")

if __name__ == '__main__':
    clear_sample_data()
