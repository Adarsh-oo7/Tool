from rest_framework.routers import DefaultRouter
from .views import CompanyViewSet, BranchViewSet, SegmentViewSet

router = DefaultRouter()
router.register(r'companies', CompanyViewSet, basename='company')
router.register(r'segments',  SegmentViewSet, basename='segment')
router.register(r'',          BranchViewSet,  basename='branch')

urlpatterns = router.urls
