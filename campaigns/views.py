from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from core.mixins import BranchScopedMixin
from core.permissions import IsManager, IsTelecaller

from .models import Campaign, CampaignLead
from .serializers import CampaignSerializer, CampaignLeadSerializer


class CampaignViewSet(BranchScopedMixin, viewsets.ModelViewSet):
    """
    WhatsApp campaign management.
    - Owners/Managers: full CRUD
    - Telecallers: read-only + can trigger send
    """
    permission_classes = [IsAuthenticated, IsTelecaller]
    serializer_class   = CampaignSerializer
    filter_backends    = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields   = ['status', 'branch']
    search_fields      = ['name']
    queryset = Campaign.objects.all().select_related('branch', 'created_by').prefetch_related('campaign_leads')

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsAuthenticated(), IsManager()]
        return [IsAuthenticated(), IsTelecaller()]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'], url_path='send')
    def send_campaign(self, request, pk=None):
        """
        POST /api/v1/campaigns/{id}/send/
        Triggers async WhatsApp blast via Celery.
        """
        campaign = self.get_object()
        if campaign.status not in ('draft', 'paused'):
            return Response({'detail': 'Campaign is already active or completed.'}, status=400)
        campaign.status = 'active'
        campaign.save(update_fields=['status'])

        # Celery task — imported here to avoid circular imports
        try:
            from campaigns.tasks import send_whatsapp_campaign
            send_whatsapp_campaign.delay(campaign.id)
        except ImportError:
            pass  # Task not yet implemented

        return Response({'detail': f'Campaign "{campaign.name}" queued for sending.'})

    @action(detail=True, methods=['patch'], url_path='pause')
    def pause_campaign(self, request, pk=None):
        campaign = self.get_object()
        campaign.status = 'paused'
        campaign.save(update_fields=['status'])
        return Response({'detail': 'Campaign paused.'})


class CampaignLeadViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only view of per-lead send status within a campaign."""
    permission_classes = [IsAuthenticated, IsTelecaller]
    serializer_class   = CampaignLeadSerializer
    filter_backends    = [DjangoFilterBackend]
    filterset_fields   = ['campaign', 'sent', 'delivered']

    def get_queryset(self):
        return CampaignLead.objects.select_related('campaign', 'lead').all()
