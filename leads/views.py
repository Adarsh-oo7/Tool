from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from core.mixins import BranchScopedMixin
from core.permissions import IsManager, IsStaffOrAbove

from .models import Lead, LeadActivity, FollowUp
from .serializers import (
    LeadSerializer, LeadListSerializer,
    LeadActivitySerializer, FollowUpSerializer,
)


class LeadViewSet(BranchScopedMixin, viewsets.ModelViewSet):
    """
    Full CRUD on leads with role-based scoping:
    - Owner: all leads
    - Manager: branch leads
    - Staff/Telecaller: only their assigned leads
    """
    permission_classes = [IsAuthenticated, IsStaffOrAbove]
    filter_backends    = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields   = ['stage', 'source', 'segment', 'assigned_to']
    search_fields      = ['name', 'phone', 'email']
    ordering_fields    = ['created_at', 'score', 'name']
    ordering           = ['-created_at']

    def get_queryset(self):
        user = self.request.user
        qs   = Lead.objects.all().select_related('branch', 'segment', 'assigned_to', 'created_by')

        if user.role == 'owner':
            return qs
        if user.role == 'manager':
            return qs.filter(branch=user.branch)
        # staff / telecaller / field_staff see only assigned leads
        return qs.filter(assigned_to=user)

    def get_serializer_class(self):
        if self.action == 'list':
            return LeadListSerializer
        return LeadSerializer

    def perform_create(self, serializer):
        serializer.save(
            created_by=self.request.user,
            branch=self.request.user.branch if not self.request.user.is_owner else serializer.validated_data.get('branch'),
        )

    @action(detail=True, methods=['patch'], url_path='stage')
    def change_stage(self, request, pk=None):
        """PATCH /api/v1/leads/{id}/stage/ — {'stage': 'converted'}"""
        lead  = self.get_object()
        stage = request.data.get('stage')
        valid_stages = [s[0] for s in Lead.STAGE_CHOICES]
        if stage not in valid_stages:
            return Response({'detail': f'Invalid stage. Choices: {valid_stages}'}, status=400)
        old_stage  = lead.stage
        lead.stage = stage
        lead.save(update_fields=['stage'])
        LeadActivity.objects.create(
            lead=lead,
            actor=request.user,
            action='stage_change',
            detail=f'Stage changed from {old_stage} to {stage}',
        )
        return Response(LeadSerializer(lead).data)

    @action(detail=True, methods=['post'], url_path='assign')
    def assign(self, request, pk=None):
        """POST /api/v1/leads/{id}/assign/ — {'assigned_to': <user_id>}"""
        from django.contrib.auth import get_user_model
        User  = get_user_model()
        lead  = self.get_object()
        uid   = request.data.get('assigned_to')
        try:
            staff = User.objects.get(pk=uid, branch=request.user.branch)
        except User.DoesNotExist:
            return Response({'detail': 'User not found in your branch.'}, status=400)
        lead.assigned_to = staff
        lead.save(update_fields=['assigned_to'])
        LeadActivity.objects.create(
            lead=lead,
            actor=request.user,
            action='assigned',
            detail=f'Lead assigned to {staff.full_name}',
        )
        return Response({'detail': f'Assigned to {staff.full_name}.'})


class LeadActivityViewSet(viewsets.ModelViewSet):
    """Activities for a specific lead."""
    permission_classes = [IsAuthenticated, IsStaffOrAbove]
    serializer_class   = LeadActivitySerializer
    filter_backends    = [DjangoFilterBackend]
    filterset_fields   = ['lead', 'activity_type']

    def get_queryset(self):
        return LeadActivity.objects.select_related('lead', 'created_by').all()

    def perform_create(self, serializer):
        serializer.save(actor=self.request.user)


class FollowUpViewSet(viewsets.ModelViewSet):
    """Follow-up scheduling and completion."""
    permission_classes = [IsAuthenticated, IsStaffOrAbove]
    serializer_class   = FollowUpSerializer
    filter_backends    = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields   = ['lead', 'completed']
    ordering_fields    = ['scheduled_date']
    ordering           = ['scheduled_date']

    def get_queryset(self):
        user = self.request.user
        qs   = FollowUp.objects.select_related('lead', 'created_by').all()
        if user.role == 'owner':
            return qs
        if user.role == 'manager':
            return qs.filter(lead__branch=user.branch)
        return qs.filter(created_by=user)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['patch'], url_path='done')
    def mark_done(self, request, pk=None):
        from django.utils import timezone
        followup = self.get_object()
        followup.completed    = True
        followup.completed_at = timezone.now()
        followup.save(update_fields=['completed', 'completed_at'])
        return Response({'detail': 'Follow-up marked as done.'})
