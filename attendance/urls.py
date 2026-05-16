from rest_framework.routers import DefaultRouter
from django.urls import path
from .views import AttendanceViewSet, BranchLocationView, AttendanceScheduleViewSet

router = DefaultRouter()
router.register(r'attendance', AttendanceViewSet, basename='attendance')
router.register(r'schedules', AttendanceScheduleViewSet, basename='attendance-schedule')

urlpatterns = [
    path('branch-location/', BranchLocationView.as_view(), name='branch-location'),
] + router.urls
