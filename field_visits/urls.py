from rest_framework.routers import DefaultRouter
from .views import FieldVisitViewSet, GPSCheckInViewSet, VisitReportViewSet

router = DefaultRouter()
router.register(r'',        FieldVisitViewSet,  basename='fieldvisit')
router.register(r'checkins', GPSCheckInViewSet,  basename='gpscheckin')
router.register(r'reports',  VisitReportViewSet, basename='visitreport')

urlpatterns = router.urls
