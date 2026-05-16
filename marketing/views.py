from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.db.models import Q, F

from .models import (
    Geofence, LocationBasedCampaign, CustomerLocation, LocationTrigger,
    ProximityTarget, NearbyCustomerAlert
)
from .serializers import (
    GeofenceSerializer, LocationBasedCampaignSerializer, CustomerLocationSerializer,
    LocationTriggerSerializer, ProximityTargetSerializer, NearbyCustomerAlertSerializer
)
from core.permissions import IsManager
from campaigns.whatsapp import WhatsAppService, WhatsAppError


class GeofenceViewSet(viewsets.ModelViewSet):
    """Manage geofences for location-based marketing"""
    permission_classes = [IsAuthenticated, IsManager]
    serializer_class = GeofenceSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['branch', 'is_active']
    search_fields = ['name']

    def get_queryset(self):
        user = self.request.user
        qs = Geofence.objects.all().select_related('branch')
        if user.role == 'manager':
            return qs.filter(branch=user.branch)
        return qs

    def perform_create(self, serializer):
        serializer.save()


class LocationBasedCampaignViewSet(viewsets.ModelViewSet):
    """Manage location-based marketing campaigns"""
    permission_classes = [IsAuthenticated, IsManager]
    serializer_class = LocationBasedCampaignSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['geofence', 'trigger_type', 'status']
    search_fields = ['name']

    def get_queryset(self):
        user = self.request.user
        qs = LocationBasedCampaign.objects.all().select_related('geofence', 'geofence__branch', 'created_by')
        if user.role == 'manager':
            return qs.filter(geofence__branch=user.branch)
        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'], url_path='test')
    def test_campaign(self, request, pk=None):
        """Test campaign with a sample message"""
        campaign = self.get_object()
        
        try:
            service = WhatsAppService()
            test_phone = request.data.get('phone') or request.user.phone
            
            if not test_phone:
                return Response(
                    {'detail': 'Test phone number required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            service.send_text(test_phone, campaign.message)
            
            return Response({
                'detail': f'Test message sent to {test_phone}',
                'message': campaign.message
            })
            
        except WhatsAppError as e:
            return Response(
                {'detail': f'WhatsApp error: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'], url_path='toggle-status')
    def toggle_status(self, request, pk=None):
        """Toggle campaign status between active and paused"""
        campaign = self.get_object()
        
        if campaign.status == 'active':
            campaign.status = 'paused'
        elif campaign.status == 'paused':
            campaign.status = 'active'
        else:
            return Response(
                {'detail': 'Can only toggle between active and paused status'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        campaign.save(update_fields=['status'])
        return Response({'detail': f'Campaign status changed to {campaign.status}'})


class CustomerLocationViewSet(viewsets.ModelViewSet):
    """Track customer locations"""
    permission_classes = [IsAuthenticated]
    serializer_class = CustomerLocationSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['lead', 'source']
    ordering = ['-timestamp']

    def get_queryset(self):
        user = self.request.user
        qs = CustomerLocation.objects.all().select_related('lead')
        
        if user.role == 'manager':
            return qs.filter(lead__branch=user.branch)
        elif user.role not in ['owner']:
            return qs.filter(lead__assigned_to=user)
        
        return qs

    @action(detail=False, methods=['post'], url_path='update-location')
    def update_location(self, request):
        """Update customer location and check for triggers"""
        lead_id = request.data.get('lead_id')
        lat = request.data.get('lat')
        lng = request.data.get('lng')
        accuracy = request.data.get('accuracy')
        source = request.data.get('source', 'mobile_app')
        
        if not all([lead_id, lat, lng]):
            return Response(
                {'detail': 'lead_id, lat, and lng are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from leads.models import Lead
            lead = Lead.objects.get(id=lead_id)
            
            # Create location record
            location = CustomerLocation.objects.create(
                lead=lead,
                lat=lat,
                lng=lng,
                accuracy=accuracy,
                source=source
            )
            
            # Check for geofence triggers
            triggers_created = self._check_geofence_triggers(lead, lat, lng)
            
            return Response({
                'detail': 'Location updated successfully',
                'location_id': location.id,
                'triggers_created': triggers_created
            })
            
        except Lead.DoesNotExist:
            return Response(
                {'detail': 'Lead not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'detail': f'Error updating location: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _check_geofence_triggers(self, lead, lat, lng):
        """Check if location triggers any geofence campaigns"""
        triggers_created = 0
        
        # Get all active geofences
        geofences = Geofence.objects.filter(is_active=True)
        
        for geofence in geofences:
            was_inside = self._was_inside_geofence(lead, geofence)
            is_inside = geofence.contains_point(lat, lng)
            
            # Check for enter trigger
            if not was_inside and is_inside:
                campaigns = LocationBasedCampaign.objects.filter(
                    geofence=geofence,
                    trigger_type='enter',
                    status='active'
                )
                
                for campaign in campaigns:
                    if campaign.is_active_now():
                        self._create_trigger(lead, campaign, geofence, 'enter', lat, lng)
                        triggers_created += 1
            
            # Check for exit trigger
            elif was_inside and not is_inside:
                campaigns = LocationBasedCampaign.objects.filter(
                    geofence=geofence,
                    trigger_type='exit',
                    status='active'
                )
                
                for campaign in campaigns:
                    if campaign.is_active_now():
                        self._create_trigger(lead, campaign, geofence, 'exit', lat, lng)
                        triggers_created += 1
        
        return triggers_created

    def _was_inside_geofence(self, lead, geofence):
        """Check if lead was previously inside the geofence"""
        last_location = CustomerLocation.objects.filter(
            lead=lead
        ).order_by('-timestamp').first()
        
        if last_location:
            return geofence.contains_point(last_location.lat, last_location.lng)
        
        return False

    def _create_trigger(self, lead, campaign, geofence, trigger_type, lat, lng):
        """Create a location trigger"""
        from django.utils import timezone
        
        # Check daily send limit
        today = timezone.localdate()
        sends_today = LocationTrigger.objects.filter(
            lead=lead,
            campaign=campaign,
            created_at__date=today,
            status='sent'
        ).count()
        
        if sends_today >= campaign.max_sends_per_day:
            return None
        
        # Create trigger
        scheduled_time = timezone.now() + timezone.timedelta(minutes=campaign.delay_minutes)
        
        trigger = LocationTrigger.objects.create(
            lead=lead,
            campaign=campaign,
            geofence=geofence,
            trigger_type=trigger_type,
            status='pending',
            location_at_trigger={'lat': float(lat), 'lng': float(lng)},
            scheduled_send_time=scheduled_time
        )
        
        return trigger


class ProximityTargetViewSet(viewsets.ReadOnlyModelViewSet):
    """View customers in proximity to branches"""
    permission_classes = [IsAuthenticated]
    serializer_class = ProximityTargetSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['branch', 'is_active']
    ordering = ['distance_meters']

    def get_queryset(self):
        user = self.request.user
        qs = ProximityTarget.objects.all().select_related('lead', 'branch')
        
        if user.role == 'manager':
            return qs.filter(branch=user.branch)
        elif user.role not in ['owner']:
            return qs.filter(lead__assigned_to=user)
        
        return qs

    @action(detail=False, methods=['get'], url_path='nearby-customers')
    def nearby_customers(self, request):
        """Get customers within 2km of branches"""
        radius_meters = request.query_params.get('radius', 2000)
        
        queryset = self.get_queryset().filter(
            distance_meters__lte=radius_meters,
            is_active=True
        )
        
        return Response(ProximityTargetSerializer(queryset, many=True).data)


class NearbyCustomerAlertViewSet(viewsets.ReadOnlyModelViewSet):
    """View alerts for nearby customers"""
    permission_classes = [IsAuthenticated]
    serializer_class = NearbyCustomerAlertSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['branch', 'message_sent']
    ordering = ['-created_at']

    def get_queryset(self):
        user = self.request.user
        qs = NearbyCustomerAlert.objects.all().select_related('lead', 'branch', 'campaign_used')
        
        if user.role == 'manager':
            return qs.filter(branch=user.branch)
        elif user.role not in ['owner']:
            return qs.filter(lead__assigned_to=user)
        
        return qs


class LocationTrackingView(APIView):
    """API for location tracking and targeting"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Process location update and return targeting info"""
        lead_id = request.data.get('lead_id')
        lat = request.data.get('lat')
        lng = request.data.get('lng')
        
        if not all([lead_id, lat, lng]):
            return Response(
                {'detail': 'lead_id, lat, and lng are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from leads.models import Lead
            lead = Lead.objects.get(id=lead_id)
            
            # Update location
            location = CustomerLocation.objects.create(
                lead=lead,
                lat=lat,
                lng=lng,
                source=request.data.get('source', 'api')
            )
            
            # Check proximity to branches
            from branches.models import Branch
            branches = Branch.objects.all()
            
            nearby_branches = []
            for branch in branches:
                if branch.lat and branch.lng:
                    distance = self._calculate_distance(
                        float(lat), float(lng),
                        float(branch.lat), float(branch.lng)
                    )
                    
                    if distance <= 2000:  # Within 2km
                        # Update or create proximity target
                        proximity_target, created = ProximityTarget.objects.update_or_create(
                            branch=branch,
                            lead=lead,
                            defaults={'distance_meters': distance}
                        )
                        
                        if not created:
                            proximity_target.distance_meters = distance
                            proximity_target.save(update_fields=['distance_meters'])
                        
                        nearby_branches.append({
                            'branch_id': branch.id,
                            'branch_name': branch.name,
                            'distance_meters': distance,
                            'within_500m': distance <= 500,
                            'within_100m': distance <= 100
                        })
                        
                        # Create nearby alert if very close
                        if distance <= 100:
                            NearbyCustomerAlert.objects.get_or_create(
                                lead=lead,
                                branch=branch,
                                defaults={'distance_meters': distance}
                            )
            
            return Response({
                'location_id': location.id,
                'nearby_branches': nearby_branches,
                'total_nearby': len(nearby_branches)
            })
            
        except Lead.DoesNotExist:
            return Response(
                {'detail': 'Lead not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    def _calculate_distance(self, lat1, lng1, lat2, lng2):
        """Calculate distance between two points in meters"""
        import math
        
        R = 6371000  # Earth's radius in meters
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lng = math.radians(lng2 - lng1)
        
        a = (math.sin(delta_lat/2)**2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lng/2)**2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
