from django.urls import path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView

from .views import (
    LoginView, MeView, ChangePasswordView, FCMTokenView,
    UserViewSet, StaffByBranchView, StaffPermissionViewSet, CreateSampleDataView,
    ProfileUpdateRequestViewSet,
)

router = DefaultRouter()
router.register(r'users',             UserViewSet,            basename='user')
router.register(r'staff-permissions', StaffPermissionViewSet, basename='staff-permission')
router.register(r'profile-requests',  ProfileUpdateRequestViewSet, basename='profile-request')

urlpatterns = [
    path('login/',           LoginView.as_view(),          name='auth-login'),
    path('me/',              MeView.as_view(),              name='auth-me'),
    path('change-password/', ChangePasswordView.as_view(),  name='auth-change-password'),
    path('fcm-token/',       FCMTokenView.as_view(),        name='auth-fcm-token'),
    path('token/refresh/',   TokenRefreshView.as_view(),    name='token-refresh'),
    path('token/verify/',    TokenVerifyView.as_view(),     name='token-verify'),
    path('staff/',           StaffByBranchView.as_view(),   name='staff-by-branch'),
    path('create-sample-data/', CreateSampleDataView.as_view(), name='create-sample-data'),
] + router.urls
