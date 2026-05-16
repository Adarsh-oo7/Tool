from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.db.models import Sum, Count, Q, F, Avg
from django.db.models.functions import Coalesce

from .models import (
    Badge, UserBadge, Leaderboard, LeaderboardEntry, 
    Achievement, UserAchievement, PointsTransaction, GamificationProfile
)
from .serializers import (
    BadgeSerializer, UserBadgeSerializer, LeaderboardSerializer,
    LeaderboardEntrySerializer, AchievementSerializer, UserAchievementSerializer,
    PointsTransactionSerializer, GamificationProfileSerializer
)
from core.permissions import IsManager


class GamificationProfileViewSet(viewsets.ReadOnlyModelViewSet):
    """View gamification profiles and stats"""
    permission_classes = [IsAuthenticated]
    serializer_class = GamificationProfileSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['current_level']

    def get_queryset(self):
        user = self.request.user
        if user.role == 'owner':
            return GamificationProfile.objects.all().select_related('user')
        elif user.role == 'manager':
            return GamificationProfile.objects.filter(user__branch=user.branch).select_related('user')
        else:
            return GamificationProfile.objects.filter(user=user).select_related('user')

    @action(detail=False, methods=['get'], url_path='my-stats')
    def my_stats(self, request):
        """Get current user's gamification stats"""
        profile, created = GamificationProfile.objects.get_or_create(
            user=request.user,
            defaults={
                'total_points': 0,
                'current_level': 1,
                'level_name': 'Beginner'
            }
        )
        
        # Get recent activity
        recent_transactions = PointsTransaction.objects.filter(
            user=request.user
        ).order_by('-created_at')[:10]
        
        # Get badges
        user_badges = UserBadge.objects.filter(
            user=request.user
        ).select_related('badge').order_by('-earned_at')[:5]
        
        # Get achievements
        user_achievements = UserAchievement.objects.filter(
            user=request.user
        ).select_related('achievement').order_by('-unlocked_at')[:5]
        
        return Response({
            'profile': GamificationProfileSerializer(profile).data,
            'recent_transactions': PointsTransactionSerializer(recent_transactions, many=True).data,
            'recent_badges': UserBadgeSerializer(user_badges, many=True).data,
            'recent_achievements': UserAchievementSerializer(user_achievements, many=True).data,
        })


class LeaderboardViewSet(viewsets.ReadOnlyModelViewSet):
    """View leaderboards"""
    permission_classes = [IsAuthenticated]
    serializer_class = LeaderboardSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['period', 'metric']

    def get_queryset(self):
        user = self.request.user
        qs = Leaderboard.objects.filter(is_active=True).prefetch_related('entries__user')
        
        if user.role == 'manager':
            # Filter to show only branch staff
            qs = qs.filter(entries__user__branch=user.branch)
        
        return qs.distinct()

    @action(detail=True, methods=['get'], url_path='entries')
    def entries(self, request, pk=None):
        """Get entries for a specific leaderboard"""
        leaderboard = self.get_object()
        entries = leaderboard.entries.select_related('user').order_by('rank')
        
        # Filter by branch for managers
        if request.user.role == 'manager':
            entries = entries.filter(user__branch=request.user.branch)
        
        return Response(LeaderboardEntrySerializer(entries, many=True).data)

    @action(detail=False, methods=['get'], url_path='current')
    def current_leaderboards(self, request):
        """Get current active leaderboards"""
        today = timezone.localdate()
        
        # Get current period leaderboards
        current_leaderboards = []
        
        # Daily leaderboard
        daily_lb, _ = Leaderboard.objects.get_or_create(
            period='daily',
            metric='sales_count',
            date=today,
            defaults={'is_active': True}
        )
        current_leaderboards.append(daily_lb)
        
        # Weekly leaderboard (current week)
        week_start = today - timezone.timedelta(days=today.weekday())
        weekly_lb, _ = Leaderboard.objects.get_or_create(
            period='weekly',
            metric='sales_count',
            date=week_start,
            defaults={'is_active': True}
        )
        current_leaderboards.append(weekly_lb)
        
        # Monthly leaderboard
        month_start = today.replace(day=1)
        monthly_lb, _ = Leaderboard.objects.get_or_create(
            period='monthly',
            metric='sales_count',
            date=month_start,
            defaults={'is_active': True}
        )
        current_leaderboards.append(monthly_lb)
        
        data = []
        for lb in current_leaderboards:
            entries = lb.entries.select_related('user').order_by('rank')[:10]
            
            # Filter by branch for managers
            if request.user.role == 'manager':
                entries = entries.filter(user__branch=request.user.branch)
            
            data.append({
                'leaderboard': LeaderboardSerializer(lb).data,
                'top_entries': LeaderboardEntrySerializer(entries, many=True).data
            })
        
        return Response(data)


class BadgeViewSet(viewsets.ReadOnlyModelViewSet):
    """View available badges and user badges"""
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['badge_type']

    def get_queryset(self):
        if self.action == 'list':
            return Badge.objects.filter(is_active=True)
        return Badge.objects.all()

    def get_serializer_class(self):
        if self.action == 'list':
            return BadgeSerializer
        return UserBadgeSerializer

    @action(detail=False, methods=['get'], url_path='my-badges')
    def my_badges(self, request):
        """Get current user's earned badges"""
        user_badges = UserBadge.objects.filter(
            user=request.user
        ).select_related('badge').order_by('-earned_at')
        
        return Response(UserBadgeSerializer(user_badges, many=True).data)


class PointsTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    """View points transactions"""
    permission_classes = [IsAuthenticated]
    serializer_class = PointsTransactionSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['transaction_type']

    def get_queryset(self):
        user = self.request.user
        if user.role in ['owner', 'manager']:
            # Managers can see their branch staff transactions
            if user.role == 'manager':
                return PointsTransaction.objects.filter(
                    user__branch=user.branch
                ).select_related('user').order_by('-created_at')
            else:
                return PointsTransaction.objects.all().select_related('user').order_by('-created_at')
        else:
            return PointsTransaction.objects.filter(
                user=user
            ).order_by('-created_at')


class AchievementViewSet(viewsets.ReadOnlyModelViewSet):
    """View achievements"""
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['badge']

    def get_queryset(self):
        if self.action == 'list':
            return Achievement.objects.filter(is_active=True)
        return Achievement.objects.all()

    def get_serializer_class(self):
        if self.action == 'list':
            return AchievementSerializer
        return UserAchievementSerializer

    @action(detail=False, methods=['get'], url_path='my-achievements')
    def my_achievements(self, request):
        """Get current user's unlocked achievements"""
        user_achievements = UserAchievement.objects.filter(
            user=request.user
        ).select_related('achievement').order_by('-unlocked_at')
        
        return Response(UserAchievementSerializer(user_achievements, many=True).data)


class GamificationStatsView(APIView):
    """Get comprehensive gamification statistics"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        
        if user.role not in ['owner', 'manager']:
            return Response(
                {'detail': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get date range for stats
        today = timezone.localdate()
        month_start = today.replace(day=1)
        
        # Base queryset for users
        if user.role == 'manager':
            users_queryset = Q(branch=user.branch)
        else:
            users_queryset = Q()
        
        # Calculate stats
        stats = {
            'total_staff': GamificationProfile.objects.filter(users_queryset).count(),
            'total_points_distributed': PointsTransaction.objects.filter(
                transaction_type='earned',
                created_at__date__gte=month_start
            ).aggregate(total=Sum('points'))['total'] or 0,
            'top_performers': self._get_top_performers(users_queryset),
            'badge_distribution': self._get_badge_distribution(users_queryset),
            'level_distribution': self._get_level_distribution(users_queryset),
            'recent_activity': self._get_recent_activity(users_queryset)
        }
        
        return Response(stats)

    def _get_top_performers(self, users_filter):
        """Get top performers this month"""
        from django.db.models import Sum
        
        return GamificationProfile.objects.filter(
            users_filter
        ).select_related('user').order_by('-total_points')[:5]

    def _get_badge_distribution(self, users_filter):
        """Get distribution of badges earned"""
        from django.db.models import Count
        
        return UserBadge.objects.filter(
            user__in=GamificationProfile.objects.filter(users_filter).values('user')
        ).values('badge__badge_type').annotate(
            count=Count('id')
        ).order_by('-count')

    def _get_level_distribution(self, users_filter):
        """Get distribution of user levels"""
        from django.db.models import Count
        
        return GamificationProfile.objects.filter(
            users_filter
        ).values('level_name').annotate(
            count=Count('id')
        ).order_by('-count')

    def _get_recent_activity(self, users_filter):
        """Get recent gamification activity"""
        return PointsTransaction.objects.filter(
            user__in=GamificationProfile.objects.filter(users_filter).values('user')
        ).select_related('user').order_by('-created_at')[:10]
