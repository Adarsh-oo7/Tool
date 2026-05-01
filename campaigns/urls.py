from rest_framework.routers import DefaultRouter
from .views import CampaignViewSet, CampaignLeadViewSet

router = DefaultRouter()
router.register(r'',      CampaignViewSet,     basename='campaign')
router.register(r'leads', CampaignLeadViewSet, basename='campaignlead')

urlpatterns = router.urls
