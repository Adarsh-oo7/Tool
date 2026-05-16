import os
import django

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bindu_jewellery_backend.settings.development')
django.setup()

from branches.models import Company, Branch
from django.contrib.auth import get_user_model

User = get_user_model()

def setup_actual_data():
    print("Setting up actual branch data for Bindu Jewellery...")
    
    # 1. Create Company
    company, created = Company.objects.get_or_create(
        name="Bindu Jewellery",
        defaults={
            "address": "Mangaluru, Karnataka",
            "email": "bindujewellerymangalore@gmail.com"
        }
    )
    if created:
        print(f"Created Company: {company.name}")
    else:
        print(f"Company {company.name} already exists.")

    # Get a manager (superuser or owner)
    admin_user = User.objects.filter(is_superuser=True).first() or User.objects.filter(role='owner').first()

    # 2. Create Branches
    branches_data = [
        {
            "name": "SULLIA",
            "address": "Opposite Police Station, Sullia-574239",
            "phone": "8113929916",
        },
        {
            "name": "MANGALURU",
            "address": "Near SCS Hospital, Bendore, Mangaluru",
            "phone": "8296120400",
        },
        {
            "name": "KASARAGOD",
            "address": "NH-17, Ashwini Nagar, Kasaragod 671121",
            "phone": "9847020400",
        }
    ]

    for data in branches_data:
        branch, b_created = Branch.objects.get_or_create(
            name=data['name'],
            company=company,
            defaults={
                "address": data['address'],
                "phone": data['phone'],
                "manager": admin_user
            }
        )
        if b_created:
            print(f"Created Branch: {branch.name}")
        else:
            # Update existing branch
            branch.address = data['address']
            branch.phone = data['phone']
            branch.save()
            print(f"Updated Branch: {branch.name}")

    print("\n✅ Actual data setup successfully!")

if __name__ == '__main__':
    setup_actual_data()
