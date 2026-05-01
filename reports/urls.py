from rest_framework.routers import DefaultRouter
from .views import DailyReportViewSet

router = DefaultRouter()
router.register(r'', DailyReportViewSet, basename='dailyreport')

urlpatterns = router.urls
