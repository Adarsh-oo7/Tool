from django.urls import path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView

from .views import (
    LoginView, RegisterView, MeView,
    ChangePasswordView, FCMTokenView, UserViewSet,
)

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')

urlpatterns = [
    path('login/',           LoginView.as_view(),          name='auth-login'),
    path('register/',        RegisterView.as_view(),        name='auth-register'),
    path('me/',              MeView.as_view(),              name='auth-me'),
    path('change-password/', ChangePasswordView.as_view(),  name='auth-change-password'),
    path('fcm-token/',       FCMTokenView.as_view(),        name='auth-fcm-token'),
    path('token/refresh/',   TokenRefreshView.as_view(),    name='token-refresh'),
    path('token/verify/',    TokenVerifyView.as_view(),     name='token-verify'),
] + router.urls
