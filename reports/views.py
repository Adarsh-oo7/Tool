from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from core.mixins import BranchScopedMixin
from core.permissions import IsManager

from .models import DailyReport
from .serializers import DailyReportSerializer


class DailyReportViewSet(BranchScopedMixin, viewsets.ReadOnlyModelViewSet):
    """
    Auto-generated daily reports — read-only via API.
    Managers see own branch; Owner sees all.
    """
    permission_classes = [IsAuthenticated, IsManager]
    serializer_class   = DailyReportSerializer
    filter_backends    = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields   = ['branch', 'date']
    ordering_fields    = ['date', 'total_revenue']
    ordering           = ['-date']
    queryset           = DailyReport.objects.all().select_related('branch')
