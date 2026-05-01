from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from core.mixins import BranchScopedMixin
from core.permissions import IsManager

from .models import Attendance
from .serializers import AttendanceSerializer


class AttendanceViewSet(BranchScopedMixin, viewsets.ModelViewSet):
    """
    GPS + photo check-in system.
    - Staff/Field: create own check-in (one per day enforced by model unique_together)
    - Manager/Owner: view branch records + approve/reject
    """
    permission_classes = [IsAuthenticated]
    serializer_class   = AttendanceSerializer
    filter_backends    = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields   = ['status', 'user', 'date']
    ordering           = ['-checked_in_at']
    branch_field       = 'user__branch'
    queryset           = Attendance.objects.all().select_related('user', 'approved_by')

    def get_queryset(self):
        user = self.request.user
        qs   = Attendance.objects.select_related('user', 'approved_by').all()
        if user.role == 'owner':
            return qs
        if user.role == 'manager':
            return qs.filter(user__branch=user.branch)
        return qs.filter(user=user)

    def perform_create(self, serializer):
        serializer.save(
            user=self.request.user,
            branch=self.request.user.branch    # ← add this line
        )

    @action(detail=True, methods=['patch'], url_path='approve', permission_classes=[IsAuthenticated, IsManager])
    def approve(self, request, pk=None):
        record = self.get_object()
        record.status      = 'approved'
        record.approved_by = request.user
        record.save(update_fields=['status', 'approved_by'])
        return Response({'detail': 'Attendance approved.'})

    @action(detail=True, methods=['patch'], url_path='reject', permission_classes=[IsAuthenticated, IsManager])
    def reject(self, request, pk=None):
        record = self.get_object()
        record.status      = 'rejected'
        record.approved_by = request.user
        record.save(update_fields=['status', 'approved_by'])
        return Response({'detail': 'Attendance rejected.'})
