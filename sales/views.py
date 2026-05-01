from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from core.mixins import BranchScopedMixin
from core.permissions import IsStaffOrAbove

from .models import Sale
from .serializers import SaleSerializer


class SaleViewSet(BranchScopedMixin, viewsets.ModelViewSet):
    """Record and view sales — branch-scoped."""
    permission_classes = [IsAuthenticated, IsStaffOrAbove]
    serializer_class   = SaleSerializer
    filter_backends    = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields   = ['branch', 'segment', 'staff']
    ordering_fields    = ['created_at', 'amount']
    ordering           = ['-created_at']
    queryset           = Sale.objects.all().select_related('lead', 'branch', 'segment', 'staff', 'campaign')

    def perform_create(self, serializer):
        user = self.request.user
        serializer.save(
            staff=user,
            branch=user.branch or None,   # ← simple: always use user.branch (None for owner = OK after model fix)
        )
