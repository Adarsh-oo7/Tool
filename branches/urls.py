from rest_framework.routers import DefaultRouter
from .views import CompanyViewSet, BranchViewSet, SegmentViewSet

router = DefaultRouter()
router.register(r'companies', CompanyViewSet, basename='company')
router.register(r'branches',  BranchViewSet,  basename='branch')
router.register(r'segments',  SegmentViewSet, basename='segment')

urlpatterns = router.urls
