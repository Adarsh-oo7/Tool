from rest_framework.routers import DefaultRouter
from .views import LeadViewSet, LeadActivityViewSet, FollowUpViewSet

router = DefaultRouter()
router.register(r'',          LeadViewSet,         basename='lead')
router.register(r'activities', LeadActivityViewSet, basename='lead-activity')
router.register(r'followups',  FollowUpViewSet,     basename='followup')

urlpatterns = router.urls
