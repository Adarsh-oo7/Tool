from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.http import HttpResponse
from django_filters.rest_framework import DjangoFilterBackend

from core.mixins import BranchScopedMixin
from core.permissions import IsManager, IsOwner, IsTelecaller

from .models import Campaign, CampaignLead, WhatsAppTemplate, SpecialDayMessage, Integration, IntegrationAnalytics
from .serializers import (
    CampaignSerializer, CampaignListSerializer, CampaignCreateSerializer,
    CampaignLeadSerializer, WhatsAppTemplateSerializer, SpecialDayMessageSerializer,
    IntegrationSerializer, IntegrationCreateSerializer, IntegrationAnalyticsSerializer,
)


class WhatsAppTemplateViewSet(viewsets.ModelViewSet):
    """Owner-only CRUD for reusable WhatsApp message templates."""
    permission_classes = [IsAuthenticated, IsOwner]
    serializer_class   = WhatsAppTemplateSerializer
    filter_backends    = [DjangoFilterBackend]
    filterset_fields   = ['trigger', 'is_active']
    queryset           = WhatsAppTemplate.objects.all().select_related('created_by')

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class SpecialDayMessageViewSet(viewsets.ModelViewSet):
    """Owner-only CRUD for festival/special-day WhatsApp messages."""
    permission_classes = [IsAuthenticated, IsOwner]
    serializer_class   = SpecialDayMessageSerializer
    filter_backends    = [DjangoFilterBackend]
    filterset_fields   = ['is_active', 'send_to_staff', 'send_to_leads']
    queryset           = SpecialDayMessage.objects.all()

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class CampaignViewSet(BranchScopedMixin, viewsets.ModelViewSet):
    """
    WhatsApp campaign management.
    - list/retrieve: Manager/Telecaller
    - create/destroy: Owner only
    - launch action: Owner/Manager
    """
    filter_backends  = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['status', 'branch', 'campaign_type']
    search_fields    = ['name']
    queryset         = Campaign.objects.all().select_related(
        'branch', 'created_by', 'whatsapp_template'
    ).prefetch_related('campaign_leads')

    def get_permissions(self):
        if self.action in ('create', 'destroy'):
            return [IsAuthenticated(), IsOwner()]
        return [IsAuthenticated(), IsTelecaller()]

    def get_serializer_class(self):
        if self.action == 'list':
            return CampaignListSerializer
        if self.action == 'create':
            return CampaignCreateSerializer
        return CampaignSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'], url_path='launch')
    def launch(self, request, pk=None):
        """POST /api/v1/campaigns/{id}/launch/ — queue WhatsApp blast."""
        campaign = self.get_object()
        if campaign.status not in ('draft', 'scheduled'):
            return Response(
                {'detail': 'Campaign must be in draft or scheduled state to launch.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        campaign.status = 'active'
        campaign.save(update_fields=['status'])

        try:
            from celery_app.tasks.campaigns import send_whatsapp_campaign
            send_whatsapp_campaign.delay(campaign.id)
        except Exception as e:
            return Response(
                {'detail': f'Campaign activated but task queue error: {e}'},
                status=status.HTTP_202_ACCEPTED,
            )
        return Response(
            {'detail': f'Campaign "{campaign.name}" queued for sending.', 'status': 'active'},
            status=status.HTTP_202_ACCEPTED,
        )

    @action(detail=True, methods=['post'], url_path='test-send')
    def test_send(self, request, pk=None):
        """POST /api/v1/campaigns/{id}/test-send/ — send test message to manager."""
        campaign = self.get_object()
        from campaigns.whatsapp import WhatsAppService, WhatsAppError
        from leads.models import Lead
        
        # Get a test lead or manager's phone
        test_phone = request.data.get('phone') or request.user.phone
        if not test_phone:
            return Response(
                {'detail': 'No phone number available for testing.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            service = WhatsAppService()
            
            # Determine message content
            if campaign.whatsapp_template:
                # Use a dummy lead for template rendering
                from django.contrib.auth import get_user_model
                User = get_user_model()
                dummy_user = User(full_name='Test User', branch=campaign.branch)
                message = campaign.whatsapp_template.render(dummy_user)
            else:
                message = campaign.message or f"Test message for campaign: {campaign.name}"
            
            service.send_text(test_phone, message)
            
            return Response({
                'detail': f'Test message sent to {test_phone}',
                'message': message
            })
            
        except WhatsAppError as e:
            return Response(
                {'detail': f'WhatsApp error: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=['post'], url_path='auto-target')
    def auto_target(self, request, pk=None):
        """POST /api/v1/campaigns/{id}/auto-target/ — automatically add target leads."""
        campaign = self.get_object()
        from leads.models import Lead
        from .models import CampaignLead
        
        # Determine target criteria based on campaign type
        leads_queryset = Lead.objects.filter(is_active=True)
        
        if campaign.branch:
            leads_queryset = leads_queryset.filter(branch=campaign.branch)
        
        if campaign.segment:
            leads_queryset = leads_queryset.filter(segment=campaign.segment)
        
        # Campaign type specific filtering
        if campaign.campaign_type == 'recovery':
            # Target lost leads (not contacted in 30+ days)
            from django.utils import timezone
            cutoff = timezone.now() - timezone.timedelta(days=30)
            leads_queryset = leads_queryset.filter(updated_at__lt=cutoff)
        elif campaign.campaign_type == 'bridal':
            # Target leads with bridal interest
            leads_queryset = leads_queryset.filter(
                product_interest__icontains='bridal'
            ) | leads_queryset.filter(
                occasion__icontains='wedding'
            )
        elif campaign.campaign_type == 'followup':
            # Target interested leads not converted
            leads_queryset = leads_queryset.filter(
                stage__in=['interested', 'contacted']
            )
        
        # Add leads to campaign
        created_count = 0
        for lead in leads_queryset:
            CampaignLead.objects.get_or_create(
                campaign=campaign,
                lead=lead,
                defaults={'sent': False}
            )
            created_count += 1
        
        return Response({
            'detail': f'Added {created_count} leads to campaign "{campaign.name}"',
            'total_leads': campaign.total_leads
        })

    @action(detail=True, methods=['patch'], url_path='pause')
    def pause(self, request, pk=None):
        campaign = self.get_object()
        campaign.status = 'scheduled'
        campaign.save(update_fields=['status'])
        return Response({'detail': 'Campaign paused.'})

    @action(detail=True, methods=['patch'], url_path='cancel')
    def cancel(self, request, pk=None):
        campaign = self.get_object()
        campaign.status = 'cancelled'
        campaign.save(update_fields=['status'])
        return Response({'detail': 'Campaign cancelled.'})


class CampaignLeadViewSet(viewsets.ModelViewSet):
    """Per-lead delivery tracking within a campaign."""
    permission_classes = [IsAuthenticated, IsTelecaller]
    serializer_class   = CampaignLeadSerializer
    filter_backends    = [DjangoFilterBackend]
    filterset_fields   = ['campaign', 'sent', 'delivered', 'converted']
    http_method_names  = ['get', 'patch', 'head', 'options']  # no create/delete

    def get_queryset(self):
        return CampaignLead.objects.select_related('campaign', 'lead').all()


class IntegrationViewSet(viewsets.ModelViewSet):
    """
    External platform integrations for analytics tracking.
    READ-ONLY access - no posting/publishing permissions.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = IntegrationSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['platform', 'is_connected', 'sync_enabled', 'branch']
    queryset = Integration.objects.all().select_related('branch', 'created_by')

    def get_permissions(self):
        if self.action in ('google_callback', 'meta_callback', 'oauth_url', 'meta_oauth_url'):
            from rest_framework.permissions import AllowAny
            return [AllowAny()]
            
        if self.action in ('create', 'destroy', 'update', 'partial_update'):
            # Owner can manage all integrations
            # Manager can only manage their branch's integrations
            if self.request.user.role == 'owner':
                return [IsAuthenticated()]
            elif self.request.user.role == 'manager':
                return [IsAuthenticated()]
            else:
                return [IsAuthenticated(), IsOwner()]
        return [IsAuthenticated()]

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Managers can see their branch's integrations OR global integrations
        if self.request.user.role == 'manager' and self.request.user.branch:
            from django.db.models import Q
            return queryset.filter(Q(branch=self.request.user.branch) | Q(branch__isnull=True))
        
        # Owners can see all
        return queryset

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return IntegrationCreateSerializer
        return IntegrationSerializer

    def perform_create(self, serializer):
        # Managers can only create integrations for their branch
        if self.request.user.role == 'manager' and self.request.user.branch:
            serializer.save(created_by=self.request.user, branch=self.request.user.branch)
        else:
            serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'], url_path='sync')
    def sync(self, request, pk=None):
        """POST /api/v1/campaigns/integrations/{id}/sync/ — manual sync trigger."""
        integration = self.get_object()
        
        if not integration.is_connected:
            return Response(
                {'detail': 'Integration must be connected to sync.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get the appropriate service
        service = self._get_service(integration)
        
        if not service:
            return Response(
                {'detail': 'Service not available for this platform.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update sync status
        integration.sync_status = 'syncing'
        integration.save(update_fields=['sync_status'])
        
        try:
            # Perform sync
            result = service.sync_analytics()
            
            if result.get('success'):
                return Response({
                    'detail': f'Sync completed successfully. Synced {result.get("synced_count", 0)} days of data.',
                    'result': result
                })
            else:
                integration.sync_status = 'error'
                integration.sync_error = result.get('error', 'Unknown error')
                integration.save(update_fields=['sync_status', 'sync_error'])
                
                return Response(
                    {'detail': f'Sync failed: {result.get("error")}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except Exception as e:
            integration.sync_status = 'error'
            integration.sync_error = str(e)
            integration.save(update_fields=['sync_status', 'sync_error'])
            
            return Response(
                {'detail': f'Sync error: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'], url_path='disconnect')
    def disconnect(self, request, pk=None):
        """POST /api/v1/campaigns/integrations/{id}/disconnect/ — disconnect integration."""
        integration = self.get_object()
        
        integration.is_connected = False
        integration.access_token = ''
        integration.refresh_token = ''
        integration.token_expiry = None
        integration.sync_status = 'idle'
        integration.save()
        
        return Response({'detail': 'Integration disconnected successfully.'})

    @action(detail=False, methods=['get'], url_path='oauth-url')
    def oauth_url(self, request):
        """GET /api/v1/campaigns/integrations/oauth-url/?platform=...&redirect_uri=..."""
        platform = request.query_params.get('platform')
        redirect_uri = request.query_params.get('redirect_uri')
        
        if not platform or not redirect_uri:
            return Response({'detail': 'Platform and redirect_uri are required.'}, status=400)

        from django.conf import settings
        
        if platform == 'google_analytics':
            client_id = getattr(settings, 'GOOGLE_CLIENT_ID', '')
            if not client_id:
                return Response({'detail': 'Google Client ID not configured in settings.'}, status=400)
            
            # Request access to analytics.readonly and optionally other scopes
            scopes = [
                'https://www.googleapis.com/auth/analytics.readonly',
                'https://www.googleapis.com/auth/userinfo.email',
                'https://www.googleapis.com/auth/userinfo.profile',
            ]
            
            params = {
                'client_id': client_id,
                'redirect_uri': redirect_uri,
                'response_type': 'code',
                'scope': ' '.join(scopes),
                'access_type': 'offline',
                'prompt': 'consent',
            }
            from urllib.parse import urlencode
            url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
            return Response({'url': url})
            
        return Response({'detail': f'OAuth not implemented for {platform}.'}, status=400)

    @action(detail=False, methods=['get'], url_path='meta/oauth-url')
    def meta_oauth_url(self, request):
        """GET /api/v1/campaigns/integrations/meta/oauth-url/ — get Meta OAuth login link."""
        from django.conf import settings
        from campaigns.integrations.meta.auth_service import MetaAuthService
        
        try:
            branch_id = request.query_params.get('branch_id', '')
            redirect_uri = getattr(settings, 'META_REDIRECT_URI', '')
            app_id = getattr(settings, 'META_APP_ID', '')
            
            if not app_id or app_id == "YOUR_META_APP_ID":
                return Response({'detail': 'Meta App ID is not configured in backend settings.'}, status=400)
            
            if not redirect_uri:
                return Response({'detail': 'Meta Redirect URI is not configured in backend settings.'}, status=400)
            
            # State can include branch_id for multi-branch support
            state = f"branch_id={branch_id}"
            
            auth_url = MetaAuthService.get_auth_url(redirect_uri, state=state)
            return Response({'url': auth_url})
        except Exception as e:
            return Response({'detail': f"Failed to generate OAuth URL: {str(e)}"}, status=500)

    @action(detail=False, methods=['post'], url_path='meta/callback')
    def meta_callback(self, request):
        """POST /api/v1/campaigns/integrations/meta/callback/ — handle Meta OAuth callback."""
        code = request.data.get('code')
        state = request.data.get('state', '')
        redirect_uri = request.data.get('redirect_uri')
        
        # Parse branch_id from state
        branch_id = None
        if state and 'branch_id=' in state:
            try:
                branch_id = state.split('branch_id=')[1].split('&')[0]
                if not branch_id: branch_id = None
            except:
                branch_id = None
            
        if not code:
            return Response({'detail': 'Authorization code is required.'}, status=400)
            
        from django.conf import settings
        from campaigns.integrations.meta.auth_service import MetaAuthService
        
        auth = MetaAuthService()
        
        try:
            # 1. Exchange code for short-lived token
            token_data = auth.exchange_code_for_token(code, redirect_uri)
            short_token = token_data['access_token']
            
            # 2. Exchange for long-lived user token (60 days)
            long_token = auth.get_long_lived_token(short_token)
            
            # 3. Save or update integration
            integration, created = Integration.objects.update_or_create(
                platform='facebook_ads',
                branch_id=branch_id,
                defaults={
                    'account_name': 'Meta Business Account',
                    'is_connected': True,
                    'created_by': request.user if request.user.is_authenticated else None,
                    'sync_status': 'idle',
                }
            )
            
            integration.set_access_token(long_token)
            integration.save()
            
            return Response(IntegrationSerializer(integration).data)
        except Exception as e:
            return Response({'detail': f"Meta Connection Failed: {str(e)}"}, status=400)

    @action(detail=False, methods=['get', 'post'], url_path='webhook/meta', permission_classes=[AllowAny])
    def meta_webhook(self, request):
        """Handle Meta Webhooks (GET for verification, POST for data)."""
        from campaigns.integrations.meta.webhook_service import MetaWebhookService
        service = MetaWebhookService()

        # 1. Handle Verification (GET)
        if request.method == 'GET':
            mode = request.query_params.get('hub.mode')
            token = request.query_params.get('hub.verify_token')
            challenge = request.query_params.get('hub.challenge')
            
            if mode == 'subscribe' and token == 'bindu_jewellery_meta_verify_token':
                return HttpResponse(challenge)
            return Response({'detail': 'Verification failed'}, status=403)

        # 2. Handle Data (POST)
        try:
            signature = request.headers.get('X-Hub-Signature')
            if not service.verify_signature(request.body, signature):
                return Response({'detail': 'Invalid signature'}, status=401)
                
            service.handle_lead_webhook(request.data)
            return Response({'status': 'received'})
        except Exception as e:
            return Response({'detail': str(e)}, status=400)
            
    @action(detail=True, methods=['get'], url_path='meta/pages')
    def meta_pages(self, request, pk=None):
        """GET /api/v1/campaigns/integrations/{id}/meta/pages/ — list Meta pages."""
        integration = self.get_object()
        
        if not integration.is_connected:
            return Response({'detail': 'Integration not connected.'}, status=400)
            
        from campaigns.integrations.meta.auth_service import MetaAuthService
        auth = MetaAuthService()
        
        try:
            pages = auth.get_pages(integration.get_access_token())
            return Response(pages)
        except Exception as e:
            return Response({'detail': f"Failed to fetch pages: {str(e)}"}, status=400)

    @action(detail=False, methods=['post'], url_path='google-callback')
    def google_callback(self, request):
        """POST /api/v1/campaigns/integrations/google-callback/ — handle OAuth code exchange."""
        code = request.data.get('code')
        redirect_uri = request.data.get('redirect_uri')
        branch_id = request.data.get('branch')
        
        if not code or not redirect_uri:
            return Response({'detail': 'Authorization code and redirect_uri are required.'}, status=400)
            
        print(f"DEBUG: Google Callback hit. Code: {code[:10]}... Redirect: {redirect_uri} Branch: {branch_id}")
            
        from django.conf import settings
        from campaigns.integrations.google.analytics import GoogleAnalyticsService
        
        # Initialize a temporary integration to use the service
        temp_integration = Integration(platform='google_analytics')
        service = GoogleAnalyticsService(temp_integration)
        
        try:
            # Exchange code for token and account info
            try:
                token_data = service.connect(code, redirect_uri)
            except Exception as e:
                # If it fails, try without the trailing slash as a backup
                if redirect_uri.endswith('/'):
                    alt_uri = redirect_uri[:-1]
                    print(f"DEBUG: Retrying with alt URI: {alt_uri}")
                    token_data = service.connect(code, alt_uri)
                else:
                    raise e
            
            # Save or update integration
            # We use platform as the primary key here since platform is unique in the model
            integration, created = Integration.objects.update_or_create(
                platform='google_analytics',
                defaults={
                    'account_name': token_data.get('account_name') or 'Google Analytics (Connected)',
                    'account_id': token_data.get('account_id') or 'pending_config',
                    'token_expiry': token_data.get('token_expiry'),
                    'is_connected': True,
                    'created_by': request.user if request.user.is_authenticated else None,
                    'sync_status': 'idle',
                    'branch_id': branch_id if branch_id else None,
                }
            )
            
            # Securely store tokens
            integration.set_access_token(token_data.get('access_token'))
            if token_data.get('refresh_token'):
                integration.set_refresh_token(token_data.get('refresh_token'))
            integration.save()
            
            print(f"DEBUG: Successfully saved integration. ID: {integration.id}")
            return Response(IntegrationSerializer(integration).data)
        except Exception as e:
            print(f"DEBUG: Google Callback Error: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response({'detail': f"Google Connection Failed: {str(e)}"}, status=400)

    @action(detail=True, methods=['get'], url_path='analytics')
    def analytics(self, request, pk=None):
        """GET /api/v1/campaigns/integrations/{id}/analytics/ — get analytics summary."""
        integration = self.get_object()
        
        days = int(request.query_params.get('days', 30))
        
        service = self._get_service(integration)
        if not service:
            return Response(
                {'detail': 'Service not available for this platform.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            summary = service.get_analytics_summary(days=days)
            return Response(summary)
        except Exception as e:
            return Response(
                {'detail': f'Failed to fetch analytics: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'], url_path='analytics-history')
    def analytics_history(self, request, pk=None):
        """GET /api/v1/campaigns/integrations/{id}/analytics-history/ — get historical analytics."""
        integration = self.get_object()
        
        days = int(request.query_params.get('days', 30))
        from django.utils import timezone
        from datetime import timedelta
        
        since = timezone.now().date() - timedelta(days=days)
        
        analytics_qs = IntegrationAnalytics.objects.filter(
            integration=integration,
            date__gte=since
        ).order_by('-date')
        
        serializer = IntegrationAnalyticsSerializer(analytics_qs, many=True)
        return Response(serializer.data)


    def _get_service(self, integration):
        """Get the appropriate service class for the platform."""
        from campaigns.integrations.google.analytics import GoogleAnalyticsService
        from campaigns.integrations.google.ads import GoogleAdsService
        from campaigns.integrations.meta.service import FacebookAdsService
        # For now, we use FacebookAdsService for both if unified
        from campaigns.integrations.meta.service import FacebookAdsService as InstagramInsightsService
        from campaigns.integrations.youtube.analytics import YouTubeAnalyticsService
        from campaigns.integrations.whatsapp.analytics import WhatsAppBusinessAnalyticsService
        from campaigns.integrations.email.mailchimp import MailchimpService
        from campaigns.integrations.email.brevo import BrevoService
        from campaigns.integrations.email.sendgrid import SendGridService
        
        services = {
            'google_analytics': GoogleAnalyticsService,
            'google_ads': GoogleAdsService,
            'facebook_ads': FacebookAdsService,
            'instagram_insights': InstagramInsightsService,
            'youtube_analytics': YouTubeAnalyticsService,
            'whatsapp_business': WhatsAppBusinessAnalyticsService,
            'mailchimp': MailchimpService,
            'brevo': BrevoService,
            'sendgrid': SendGridService,
        }
        
        service_class = services.get(integration.platform)
        if service_class:
            return service_class(integration)
        return None


class IntegrationAnalyticsViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only view for integration analytics data.
    """
    permission_classes = [IsAuthenticated, IsOwner]
    serializer_class = IntegrationAnalyticsSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['integration', 'date']
    queryset = IntegrationAnalytics.objects.all().select_related('integration')
