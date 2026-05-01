from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from core.mixins import BranchScopedMixin
from core.permissions import IsManager, IsOwner

from .models import Company, Branch, Segment
from .serializers import CompanySerializer, BranchSerializer, SegmentSerializer


class CompanyViewSet(viewsets.ModelViewSet):
    """Owner-only — only one company typically exists."""
    permission_classes = [IsAuthenticated, IsOwner]
    queryset           = Company.objects.all()
    serializer_class   = CompanySerializer


class BranchViewSet(BranchScopedMixin, viewsets.ModelViewSet):
    """Owner sees all branches; Manager/Staff see own branch."""
    permission_classes = [IsAuthenticated]
    queryset           = Branch.objects.all().select_related('company').prefetch_related('segments')
    serializer_class   = BranchSerializer
    filter_backends    = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields   = ['is_active', 'company']
    search_fields      = ['name']

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsAuthenticated(), IsOwner()]
        return [IsAuthenticated()]


class SegmentViewSet(viewsets.ModelViewSet):
    """Segments scoped to their branch; owners manage, others read-only."""
    permission_classes = [IsAuthenticated]
    serializer_class   = SegmentSerializer
    filter_backends    = [DjangoFilterBackend]
    filterset_fields   = ['branch', 'name', 'is_active']

    def get_queryset(self):
        user = self.request.user
        qs   = Segment.objects.all().select_related('branch')
        if user.role == 'owner':
            return qs
        if user.branch:
            return qs.filter(branch=user.branch)
        return qs.none()

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsAuthenticated(), IsOwner()]
        return [IsAuthenticated()]
