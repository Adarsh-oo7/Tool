from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from core.permissions import IsTelecaller

from .models import CallLog
from .serializers import CallLogSerializer


class CallLogViewSet(viewsets.ModelViewSet):
    """Telecallers create call logs; Managers/Owners can view all branch logs."""
    permission_classes = [IsAuthenticated, IsTelecaller]
    serializer_class   = CallLogSerializer
    filter_backends    = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields   = ['lead', 'outcome']
    ordering_fields    = ['created_at', 'duration_seconds']
    ordering           = ['-created_at']

    def get_queryset(self):
        user = self.request.user
        qs   = CallLog.objects.select_related('lead', 'staff').all()
        if user.role == 'owner':
            return qs
        if user.role == 'manager':
            return qs.filter(lead__branch=user.branch)
        return qs.filter(staff=user)

    def perform_create(self, serializer):
        serializer.save(staff=self.request.user)
