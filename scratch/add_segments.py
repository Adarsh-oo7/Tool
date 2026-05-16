import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bindu_jewellery_backend.settings')
django.setup()

from branches.models import Branch, Segment

def check_and_add_segments():
    branches = Branch.objects.all()
    if not branches.exists():
        print("No branches found. Please create branches first.")
        return

    segment_choices = [
        ('bridal',     'Bridal Jewellery'),
        ('daily_wear', 'Daily Wear'),
        ('investment', 'Investment Gold'),
        ('diamond',    'Diamond Collection'),
    ]

    for branch in branches:
        for code, name in segment_choices:
            segment, created = Segment.objects.get_or_create(
                branch=branch,
                name=code
            )
            if created:
                print(f"Created segment '{name}' for branch '{branch.name}'")
            else:
                print(f"Segment '{name}' already exists for branch '{branch.name}'")

if __name__ == "__main__":
    check_and_add_segments()
