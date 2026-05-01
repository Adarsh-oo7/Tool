from rest_framework.routers import DefaultRouter
from .views import SaleViewSet

router = DefaultRouter()
router.register(r'', SaleViewSet, basename='sale')

urlpatterns = router.urls
