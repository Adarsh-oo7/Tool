from django.utils import timezone
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from core.permissions import IsFieldStaff

from .models import FieldVisit, GPSCheckIn, VisitReport
from .serializers import FieldVisitSerializer, GPSCheckInSerializer, VisitReportSerializer


class FieldVisitViewSet(viewsets.ModelViewSet):
    """GPS-tracked field visits."""
    permission_classes = [IsAuthenticated, IsFieldStaff]
    serializer_class   = FieldVisitSerializer
    filter_backends    = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields   = ['status', 'staff', 'lead', 'branch']
    ordering           = ['-started_at']

    def get_queryset(self):
        user = self.request.user
        qs   = FieldVisit.objects.select_related('lead', 'staff', 'branch').prefetch_related('checkins').all()
        if user.role == 'owner':
            return qs
        if user.role == 'manager':
            return qs.filter(branch=user.branch)
        return qs.filter(staff=user)

    def perform_create(self, serializer):
        serializer.save(
            staff=self.request.user,
            branch=self.request.user.branch or None,   # safe for owner
        )

    @action(detail=True, methods=['patch'], url_path='end')
    def end_visit(self, request, pk=None):
        visit = self.get_object()
        if visit.status != 'active':
            return Response({'detail': 'Visit is not active.'}, status=400)
        visit.status   = 'completed'
        visit.ended_at = timezone.now()
        visit.save(update_fields=['status', 'ended_at'])
        return Response(FieldVisitSerializer(visit).data)

    @action(detail=True, methods=['patch'], url_path='cancel')
    def cancel_visit(self, request, pk=None):
        visit = self.get_object()
        visit.status   = 'cancelled'
        visit.ended_at = timezone.now()
        visit.save(update_fields=['status', 'ended_at'])
        return Response({'detail': 'Visit cancelled.'})


class GPSCheckInViewSet(viewsets.ModelViewSet):
    """Periodic GPS pings from mobile app during a field visit."""
    permission_classes = [IsAuthenticated, IsFieldStaff]
    serializer_class   = GPSCheckInSerializer
    http_method_names  = ['get', 'post', 'head', 'options']
    filter_backends    = [DjangoFilterBackend]
    filterset_fields   = ['visit']

    def get_queryset(self):
        user = self.request.user
        qs   = GPSCheckIn.objects.select_related('visit__staff').all()
        if user.role in ('owner', 'manager'):
            return qs
        return qs.filter(visit__staff=user)


class VisitReportViewSet(viewsets.ModelViewSet):
    """Submit and retrieve visit outcome reports."""
    permission_classes = [IsAuthenticated, IsFieldStaff]
    serializer_class   = VisitReportSerializer
    filter_backends    = [DjangoFilterBackend]
    filterset_fields   = ['visit']

    def get_queryset(self):
        user = self.request.user
        qs   = VisitReport.objects.select_related('visit__staff').all()
        if user.role in ('owner', 'manager'):
            return qs
        return qs.filter(visit__staff=user)
