from rest_framework.routers import DefaultRouter
from .views import CustomerViewSet, LeadViewSet, LeadActivityViewSet, FollowUpViewSet

router = DefaultRouter()
router.register(r'customers',  CustomerViewSet,     basename='customer')
router.register(r'leads',      LeadViewSet,         basename='lead')
router.register(r'activities', LeadActivityViewSet, basename='lead-activity')
router.register(r'followups',  FollowUpViewSet,     basename='followup')

urlpatterns = router.urls
