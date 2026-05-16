from rest_framework.routers import DefaultRouter
from django.urls import path
from .views import (
    AlertTypeViewSet, AlertRuleViewSet, AlertViewSet, AlertSubscriptionViewSet,
    AlertDigestViewSet, SmartSuggestionViewSet, AlertDashboardView
)

router = DefaultRouter()
router.register(r'types', AlertTypeViewSet, basename='alert-type')
router.register(r'rules', AlertRuleViewSet, basename='alert-rule')
router.register(r'alerts', AlertViewSet, basename='alert')
router.register(r'subscriptions', AlertSubscriptionViewSet, basename='alert-subscription')
router.register(r'digests', AlertDigestViewSet, basename='alert-digest')
router.register(r'suggestions', SmartSuggestionViewSet, basename='smart-suggestion')

urlpatterns = [
    path('dashboard/', AlertDashboardView.as_view(), name='alert-dashboard'),
] + router.urls
