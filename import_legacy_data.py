"""
Import legacy leads from products.json into Bindu Jewellery CRM.
"""
import os, django, json
from datetime import datetime
from django.utils import timezone
from django.db import transaction

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bindu_jewellery_backend.settings.development')
django.setup()

from leads.models import Lead, Customer, FollowUp
from branches.models import Branch
from django.contrib.auth import get_user_model

User = get_user_model()

def import_legacy_data(json_path):
    print(f"Reading {json_path}...")
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"Found {len(data)} records. Starting import...")
    
    # Create or get the Legacy branch for unverified old data
    company = Company.objects.first()
    legacy_branch, _ = Branch.objects.get_or_create(
        name='LEGACY / OLD DATA',
        defaults={'company': company, 'address': 'Imported from products.json'}
    )
    branch = legacy_branch
    admin_user = User.objects.filter(role='owner').first() or User.objects.first()
    
    count = 0
    skipped = 0
    
    # Use transaction for speed and safety
    with transaction.atomic():
        for item in data:
            try:
                phone = str(item.get('mobile1') or '').strip()
                if not phone:
                    skipped += 1
                    continue
                
                name = item.get('name') or 'Unnamed'
                
                # 1. Get or create Customer
                customer, _ = Customer.objects.get_or_create(
                    phone=phone,
                    defaults={
                        'name': name,
                        'father_name': item.get('fathername'),
                        'house_name': item.get('housename'),
                        'street': item.get('street'),
                        'panchayath': item.get('panchayath'),
                        'village': item.get('village'),
                        'district': item.get('district'),
                        'state': item.get('state'),
                        'mobile2': item.get('mobile2'),
                    }
                )
                
                # 2. Create Lead
                # Check if this legacy ID already exists to avoid duplicates if re-run
                legacy_id = item.get('id')
                if legacy_id and Lead.objects.filter(legacy_id=legacy_id).exists():
                    skipped += 1
                    continue
                
                lead = Lead.objects.create(
                    customer=customer,
                    name=name,
                    phone=phone,
                    branch=branch,
                    assigned_to=admin_user,
                    created_by=admin_user,
                    notes=item.get('description') or '',
                    legacy_id=legacy_id,
                    # Demographics
                    father_name=item.get('fathername'),
                    house_name=item.get('housename'),
                    street=item.get('street'),
                    panchayath=item.get('panchayath'),
                    village=item.get('village'),
                    district=item.get('district'),
                    state=item.get('state'),
                    mobile2=item.get('mobile2'),
                )
                
                # 3. Handle Created At (Backdate)
                created_str = item.get('created_at')
                if created_str:
                    try:
                        # 2026-01-12T05:43:39.000000Z
                        dt = datetime.fromisoformat(created_str.replace('Z', '+00:00'))
                        Lead.objects.filter(pk=lead.pk).update(created_at=dt)
                    except:
                        pass

                # 4. Handle Follow Up Date
                follow_up_str = item.get('followupdate')
                if follow_up_str and follow_up_str != '0000-00-00 00:00:00':
                    try:
                        fdt = datetime.strptime(follow_up_str, '%Y-%m-%d %H:%M:%S')
                        FollowUp.objects.create(
                            lead=lead,
                            scheduled_date=timezone.make_aware(fdt),
                            note="Legacy follow-up date",
                            created_by=admin_user
                        )
                    except:
                        pass
                
                count += 1
                if count % 100 == 0:
                    print(f"Imported {count} leads...")
                    
            except Exception as e:
                print(f"Error importing record {item.get('id')}: {e}")
                skipped += 1

    print(f"\nSUCCESS: Imported {count} leads. Skipped {skipped} records.")

if __name__ == "__main__":
    import_legacy_data('../products.json')
