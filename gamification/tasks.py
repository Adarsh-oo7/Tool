from celery import shared_task
from django.utils import timezone
from django.db.models import Sum, Count, Q, F, Avg, Max
from django.db.models.functions import Coalesce
from django.contrib.auth import get_user_model
import logging

from .models import (
    Badge, UserBadge, Leaderboard, LeaderboardEntry,
    Achievement, UserAchievement, PointsTransaction, GamificationProfile
)

logger = logging.getLogger('gamification')


@shared_task(bind=True, max_retries=3, name='gamification.tasks.update_leaderboards')
def update_leaderboards(self):
    """Update leaderboards for all periods and metrics"""
    today = timezone.localdate()
    updated_count = 0
    
    # Update daily leaderboards
    metrics = ['sales_count', 'sales_revenue', 'leads_generated', 'leads_converted', 'calls_made']
    
    for metric in metrics:
        # Daily leaderboard
        daily_lb, _ = Leaderboard.objects.get_or_create(
            period='daily',
            metric=metric,
            date=today,
            defaults={'is_active': True}
        )
        if _update_leaderboard_entries(daily_lb, metric, 'daily'):
            updated_count += 1
        
        # Weekly leaderboard
        week_start = today - timezone.timedelta(days=today.weekday())
        weekly_lb, _ = Leaderboard.objects.get_or_create(
            period='weekly',
            metric=metric,
            date=week_start,
            defaults={'is_active': True}
        )
        if _update_leaderboard_entries(weekly_lb, metric, 'weekly'):
            updated_count += 1
        
        # Monthly leaderboard
        month_start = today.replace(day=1)
        monthly_lb, _ = Leaderboard.objects.get_or_create(
            period='monthly',
            metric=metric,
            date=month_start,
            defaults={'is_active': True}
        )
        if _update_leaderboard_entries(monthly_lb, metric, 'monthly'):
            updated_count += 1
    
    logger.info(f'[gamification] Updated {updated_count} leaderboards')
    return {'updated_count': updated_count}


def _update_leaderboard_entries(leaderboard, metric, period):
    """Update entries for a specific leaderboard"""
    from sales.models import Sale
    from leads.models import Lead
    from calls.models import CallLog
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    today = timezone.localdate()
    
    # Calculate date range based on period
    if period == 'daily':
        date_filter = {'created_at__date': today}
    elif period == 'weekly':
        week_start = leaderboard.date
        date_filter = {'created_at__date__gte': week_start}
    elif period == 'monthly':
        month_start = leaderboard.date
        date_filter = {'created_at__date__gte': month_start}
    else:
        return False
    
    # Get staff users
    staff_users = User.objects.filter(role__in=['staff', 'telecaller', 'field_staff'], is_active=True)
    
    # Calculate scores based on metric
    scores = {}
    
    if metric == 'sales_count':
        sales_data = Sale.objects.filter(**date_filter).values('created_by').annotate(
            score=Count('id')
        )
        scores = {item['created_by']: item['score'] for item in sales_data}
    
    elif metric == 'sales_revenue':
        sales_data = Sale.objects.filter(**date_filter).values('created_by').annotate(
            score=Coalesce(Sum('amount'), 0)
        )
        scores = {item['created_by']: float(item['score']) for item in sales_data}
    
    elif metric == 'leads_generated':
        leads_data = Lead.objects.filter(**date_filter).values('created_by').annotate(
            score=Count('id')
        )
        scores = {item['created_by']: item['score'] for item in leads_data}
    
    elif metric == 'leads_converted':
        leads_data = Lead.objects.filter(**date_filter, stage='converted').values('assigned_to').annotate(
            score=Count('id')
        )
        scores = {item['assigned_to']: item['score'] for item in leads_data}
    
    elif metric == 'calls_made':
        calls_data = CallLog.objects.filter(**date_filter).values('created_by').annotate(
            score=Count('id')
        )
        scores = {item['created_by']: item['score'] for item in calls_data}
    
    # Update leaderboard entries
    entries = []
    rank = 1
    
    # Sort users by score (descending)
    sorted_users = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    
    for user_id, score in sorted_users:
        if score > 0:  # Only include users with positive scores
            entry, created = LeaderboardEntry.objects.update_or_create(
                leaderboard=leaderboard,
                user_id=user_id,
                defaults={
                    'rank': rank,
                    'score': score,
                    'value': {'metric': metric, 'score': score}
                }
            )
            
            if not created:
                entry.rank = rank
                entry.score = score
                entry.value = {'metric': metric, 'score': score}
                entry.save()
            
            entries.append(entry)
            rank += 1
    
    # Remove entries for users with zero score
    LeaderboardEntry.objects.filter(leaderboard=leaderboard).exclude(
        user_id__in=scores.keys()
    ).delete()
    
    return len(entries) > 0


@shared_task(bind=True, max_retries=3, name='gamification.tasks.check_and_award_badges')
def check_and_award_badges(self):
    """Check for badge eligibility and award badges"""
    User = get_user_model()
    today = timezone.localdate()
    awarded_count = 0
    
    # Get all active badges
    badges = Badge.objects.filter(is_active=True)
    
    for badge in badges:
        # Check each user for badge eligibility
        staff_users = User.objects.filter(role__in=['staff', 'telecaller', 'field_staff'], is_active=True)
        
        for user in staff_users:
            if _check_badge_eligibility(user, badge):
                # Award badge
                user_badge, created = UserBadge.objects.get_or_create(
                    user=user,
                    badge=badge,
                    defaults={
                        'points_earned': badge.points
                    }
                )
                
                if created:
                    # Add points to user's profile
                    profile, _ = GamificationProfile.objects.get_or_create(user=user)
                    profile.add_points(badge.points, f'Badge earned: {badge.name}', f'badge_{badge.id}')
                    profile.badges_count += 1
                    profile.save(update_fields=['badges_count'])
                    
                    awarded_count += 1
                    logger.info(f'[gamification] {user.full_name} earned badge: {badge.name}')
    
    logger.info(f'[gamification] Awarded {awarded_count} badges')
    return {'awarded_count': awarded_count}


def _check_badge_eligibility(user, badge):
    """Check if user is eligible for a badge"""
    from sales.models import Sale
    from leads.models import Lead
    from calls.models import CallLog
    from attendance.models import Attendance
    
    criteria = badge.criteria
    today = timezone.localdate()
    
    try:
        if badge.badge_type == 'sales':
            # Check sales criteria
            if 'total_sales' in criteria:
                sales_count = Sale.objects.filter(created_by=user).count()
                if sales_count >= criteria['total_sales']:
                    return True
            
            if 'monthly_sales' in criteria:
                month_start = today.replace(day=1)
                monthly_sales = Sale.objects.filter(
                    created_by=user,
                    created_at__date__gte=month_start
                ).count()
                if monthly_sales >= criteria['monthly_sales']:
                    return True
        
        elif badge.badge_type == 'leads':
            # Check lead criteria
            if 'total_leads' in criteria:
                leads_count = Lead.objects.filter(created_by=user).count()
                if leads_count >= criteria['total_leads']:
                    return True
            
            if 'conversion_rate' in criteria:
                total_leads = Lead.objects.filter(assigned_to=user).count()
                converted_leads = Lead.objects.filter(assigned_to=user, stage='converted').count()
                if total_leads > 0:
                    conversion_rate = (converted_leads / total_leads) * 100
                    if conversion_rate >= criteria['conversion_rate']:
                        return True
        
        elif badge.badge_type == 'attendance':
            # Check attendance criteria
            if 'perfect_week' in criteria:
                week_start = today - timezone.timedelta(days=today.weekday())
                attendance_days = Attendance.objects.filter(
                    user=user,
                    date__gte=week_start,
                    status='present'
                ).count()
                if attendance_days >= 5:  # Perfect week
                    return True
            
            if 'streak_days' in criteria:
                profile, _ = GamificationProfile.objects.get_or_create(user=user)
                if profile.streak_days >= criteria['streak_days']:
                    return True
        
        elif badge.badge_type == 'conversion':
            # Check conversion criteria
            if 'daily_conversion' in criteria:
                converted_today = Lead.objects.filter(
                    assigned_to=user,
                    stage='converted',
                    updated_at__date=today
                ).count()
                if converted_today >= criteria['daily_conversion']:
                    return True
        
        elif badge.badge_type == 'special':
            # Check special criteria
            if 'first_sale' in criteria:
                first_sale = Sale.objects.filter(created_by=user).first()
                if first_sale and criteria['first_sale']:
                    return True
            
            if 'top_performer' in criteria:
                # Check if user is in top 3 for current month
                month_start = today.replace(day=1)
                leaderboard = Leaderboard.objects.filter(
                    period='monthly',
                    metric='sales_count',
                    date=month_start
                ).first()
                
                if leaderboard:
                    top_entries = leaderboard.entries.filter(rank__lte=3)
                    user_entry = top_entries.filter(user=user).first()
                    if user_entry:
                        return True
    
    except Exception as e:
        logger.error(f'[gamification] Error checking badge eligibility for {user.full_name}: {e}')
    
    return False


@shared_task(bind=True, max_retries=3, name='gamification.tasks.update_gamification_profiles')
def update_gamification_profiles(self):
    """Update gamification profiles for all users"""
    User = get_user_model()
    updated_count = 0
    
    staff_users = User.objects.filter(role__in=['staff', 'telecaller', 'field_staff'], is_active=True)
    
    for user in staff_users:
        profile, created = GamificationProfile.objects.get_or_create(user=user)
        
        # Update streak
        profile.update_streak()
        
        # Update counts
        profile.badges_count = UserBadge.objects.filter(user=user).count()
        profile.achievements_count = UserAchievement.objects.filter(user=user).count()
        
        profile.save(update_fields=['streak_days', 'last_activity_date', 'badges_count', 'achievements_count'])
        updated_count += 1
    
    logger.info(f'[gamification] Updated {updated_count} gamification profiles')
    return {'updated_count': updated_count}


@shared_task(bind=True, max_retries=3, name='gamification.tasks.award_points_for_activity')
def award_points_for_activity(self, user_id, points, description, reference_id=''):
    """Award points to a user for specific activities"""
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    
    try:
        user = User.objects.get(id=user_id)
        profile, _ = GamificationProfile.objects.get_or_create(user=user)
        
        profile.add_points(points, description, reference_id)
        
        logger.info(f'[gamification] Awarded {points} points to {user.full_name} for {description}')
        return {'user_id': user_id, 'points': points, 'description': description}
        
    except User.DoesNotExist:
        logger.error(f'[gamification] User {user_id} not found for points award')
        return {'error': 'User not found'}
    except Exception as e:
        logger.error(f'[gamification] Error awarding points: {e}')
        return {'error': str(e)}
