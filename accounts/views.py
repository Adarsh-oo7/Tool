from django.contrib.auth import get_user_model
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView

from core.mixins import BranchScopedMixin
from core.permissions import IsManager, IsOwner

from .serializers import (
    ChangePasswordSerializer,
    CustomTokenObtainPairSerializer,
    FCMTokenSerializer,
    RegisterSerializer,
    UserListSerializer,
    UserSerializer,
)

User = get_user_model()


class LoginView(TokenObtainPairView):
    """POST /api/v1/auth/login/ — returns JWT pair + user info."""
    permission_classes = [AllowAny]
    serializer_class   = CustomTokenObtainPairSerializer


class RegisterView(generics.CreateAPIView):
    """POST /api/v1/auth/register/ — owner/manager creates new staff."""
    permission_classes = [IsAuthenticated, IsManager]
    serializer_class   = RegisterSerializer


class MeView(generics.RetrieveUpdateAPIView):
    """GET/PATCH /api/v1/auth/me/ — current user's profile."""
    permission_classes = [IsAuthenticated]
    serializer_class   = UserSerializer

    def get_object(self):
        return self.request.user


class ChangePasswordView(generics.GenericAPIView):
    """POST /api/v1/auth/change-password/"""
    permission_classes = [IsAuthenticated]
    serializer_class   = ChangePasswordSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'detail': 'Password updated successfully.'})


class FCMTokenView(generics.GenericAPIView):
    """POST /api/v1/auth/fcm-token/ — update Firebase push token."""
    permission_classes = [IsAuthenticated]
    serializer_class   = FCMTokenSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        request.user.fcm_token = serializer.validated_data['fcm_token']
        request.user.save(update_fields=['fcm_token'])
        return Response({'detail': 'FCM token updated.'})


class UserViewSet(BranchScopedMixin, viewsets.ModelViewSet):
    """
    /api/v1/accounts/users/
    Owner → all users; Manager → branch users; others → read-only self.
    """
    permission_classes = [IsAuthenticated, IsManager]
    branch_field       = 'branch'

    def get_queryset(self):
        return super().get_queryset().select_related('branch')

    # Use default manager queryset source
    queryset = User.objects.all().order_by('full_name')

    def get_serializer_class(self):
        if self.action == 'list':
            return UserListSerializer
        return UserSerializer

    @action(detail=True, methods=['patch'], permission_classes=[IsAuthenticated, IsOwner])
    def deactivate(self, request, pk=None):
        user = self.get_object()
        user.is_active = False
        user.save(update_fields=['is_active'])
        return Response({'detail': f'{user.full_name} deactivated.'})

    @action(detail=True, methods=['patch'], permission_classes=[IsAuthenticated, IsOwner])
    def activate(self, request, pk=None):
        user = self.get_object()
        user.is_active = True
        user.save(update_fields=['is_active'])
        return Response({'detail': f'{user.full_name} activated.'})
