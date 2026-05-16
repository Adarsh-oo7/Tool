from rest_framework.routers import DefaultRouter
from .views import (
    CampaignViewSet, CampaignLeadViewSet,
    WhatsAppTemplateViewSet, SpecialDayMessageViewSet,
    IntegrationViewSet, IntegrationAnalyticsViewSet,
)

router = DefaultRouter()
router.register(r'campaigns',    CampaignViewSet,          basename='campaign')
router.register(r'leads',        CampaignLeadViewSet,      basename='campaignlead')
router.register(r'templates',    WhatsAppTemplateViewSet,  basename='whatsapp-template')
router.register(r'special-days', SpecialDayMessageViewSet, basename='special-day')
router.register(r'integrations', IntegrationViewSet,      basename='integration')
router.register(r'analytics',    IntegrationAnalyticsViewSet, basename='integration-analytics')

urlpatterns = router.urls
