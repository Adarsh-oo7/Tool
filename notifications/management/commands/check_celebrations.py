import datetime
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from notifications.models import Notification

User = get_user_model()

class Command(BaseCommand):
    help = 'Checks for birthdays and work anniversaries and sends notifications'

    def handle(self, *args, **options):
        today = datetime.date.today()
        month = today.month
        day = today.day

        # 1. Birthdays
        birthday_users = User.objects.filter(
            date_of_birth__month=month,
            date_of_birth__day=day,
            is_active=True
        )
        
        for user in birthday_users:
            # Check if we already sent a birthday notification today to avoid duplicates
            exists = Notification.objects.filter(
                recipient=user,
                notif_type='birthday',
                created_at__date=today
            ).exists()
            
            if not exists:
                Notification.objects.create(
                    recipient=user,
                    notif_type='birthday',
                    title=f"Happy Birthday, {user.full_name}! 🎂",
                    body="Wishing you a fantastic day filled with joy and success. Have a great one!",
                    is_broadcast=False
                )
                self.stdout.write(self.style.SUCCESS(f'Sent birthday notification to {user.full_name}'))

        # 2. Work Anniversaries
        anniversary_users = User.objects.filter(
            join_date__month=month,
            join_date__day=day,
            is_active=True
        ).exclude(join_date=today) # Exclude people who joined today
        
        for user in anniversary_users:
            years = today.year - user.join_date.year
            if years > 0:
                exists = Notification.objects.filter(
                    recipient=user,
                    notif_type='anniversary',
                    created_at__date=today
                ).exists()
                
                if not exists:
                    Notification.objects.create(
                        recipient=user,
                        notif_type='anniversary',
                        title=f"Happy {years} Year Work Anniversary! 🎉",
                        body=f"Congratulations on completing {years} year{'s' if years > 1 else ''} with Bindu Jewellery. We appreciate your hard work and dedication!",
                        is_broadcast=False
                    )
                    self.stdout.write(self.style.SUCCESS(f'Sent anniversary notification to {user.full_name}'))
