from rest_framework.routers import DefaultRouter
from django.urls import path
from .views import (
    GamificationProfileViewSet, LeaderboardViewSet, BadgeViewSet,
    PointsTransactionViewSet, AchievementViewSet, GamificationStatsView
)

router = DefaultRouter()
router.register(r'profiles', GamificationProfileViewSet, basename='gamification-profile')
router.register(r'leaderboards', LeaderboardViewSet, basename='leaderboard')
router.register(r'badges', BadgeViewSet, basename='badge')
router.register(r'achievements', AchievementViewSet, basename='achievement')
router.register(r'points', PointsTransactionViewSet, basename='points-transaction')

urlpatterns = [
    path('stats/', GamificationStatsView.as_view(), name='gamification-stats'),
] + router.urls
