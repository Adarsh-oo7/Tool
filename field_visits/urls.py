from rest_framework.routers import DefaultRouter
from django.urls import path
from .views import FieldVisitViewSet, GPSCheckInViewSet, VisitReportViewSet, LocationTrackingViewSet, LiveTrackingView

router = DefaultRouter()
router.register(r'field-visits',  FieldVisitViewSet,  basename='fieldvisit')
router.register(r'gps-checkins',  GPSCheckInViewSet,  basename='gpscheckin')
router.register(r'visit-reports', VisitReportViewSet,  basename='visitreport')
router.register(r'location-tracking', LocationTrackingViewSet, basename='locationtracking')

urlpatterns = [
    path('live-tracking/', LiveTrackingView.as_view(), name='live-tracking'),
] + router.urls
