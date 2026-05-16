from rest_framework.routers import DefaultRouter
from .views import CallLogViewSet

router = DefaultRouter()
router.register(r'call-logs', CallLogViewSet, basename='calllog')

urlpatterns = router.urls
