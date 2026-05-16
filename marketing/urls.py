from rest_framework.routers import DefaultRouter
from django.urls import path
from .views import (
    GeofenceViewSet, LocationBasedCampaignViewSet, CustomerLocationViewSet,
    ProximityTargetViewSet, NearbyCustomerAlertViewSet, LocationTrackingView
)

router = DefaultRouter()
router.register(r'geofences', GeofenceViewSet, basename='geofence')
router.register(r'location-campaigns', LocationBasedCampaignViewSet, basename='location-campaign')
router.register(r'customer-locations', CustomerLocationViewSet, basename='customer-location')
router.register(r'proximity-targets', ProximityTargetViewSet, basename='proximity-target')
router.register(r'nearby-alerts', NearbyCustomerAlertViewSet, basename='nearby-alert')

urlpatterns = [
    path('location-tracking/', LocationTrackingView.as_view(), name='location-tracking'),
] + router.urls
