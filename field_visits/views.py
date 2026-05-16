from django.utils import timezone
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend

from core.permissions import IsFieldStaff, IsManager

from .models import FieldVisit, GPSCheckIn, VisitReport, LocationTracking
from .serializers import FieldVisitSerializer, GPSCheckInSerializer, VisitReportSerializer, LocationTrackingSerializer


class FieldVisitViewSet(viewsets.ModelViewSet):
    """Enhanced GPS-tracked field visits."""
    permission_classes = [IsAuthenticated]
    serializer_class   = FieldVisitSerializer
    filter_backends    = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields   = ['status', 'staff', 'lead', 'branch']
    ordering           = ['-started_at']

    def get_permissions(self):
        if self.action in ['start_visit', 'check_in', 'end_visit']:
            return [IsAuthenticated(), IsFieldStaff()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        qs   = FieldVisit.objects.select_related('lead', 'staff', 'branch').prefetch_related('checkins').all()
        if user.role == 'owner':
            return qs
        if user.role == 'manager':
            # Updated to filter by branch correctly
            return qs.filter(branch=user.branch)
        return qs.filter(staff=user)

    def perform_create(self, serializer):
        # Allow managers/owners to assign visits, otherwise default to current user
        staff = self.request.user
        if self.request.user.role in ['owner', 'manager'] and self.request.data.get('staff'):
            from django.contrib.auth import get_user_model
            User = get_user_model()
            try:
                staff = User.objects.get(id=self.request.data.get('staff'))
            except User.DoesNotExist:
                pass
        
        serializer.save(
            staff=staff,
            branch=staff.branch or self.request.user.branch or None,
        )

    @action(detail=True, methods=['post'], url_path='start')
    def start_visit(self, request, pk=None):
        """Start a field visit with GPS coordinates"""
        visit = self.get_object()
        
        if visit.status != 'active':
            return Response(
                {'detail': 'Visit cannot be started. Current status: ' + visit.status},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update start location
        lat = request.data.get('lat')
        lng = request.data.get('lng')
        
        if lat and lng:
            visit.start_lat = lat
            visit.start_lng = lng
            visit.save(update_fields=['start_lat', 'start_lng'])
        
        return Response({
            'detail': 'Visit started successfully',
            'start_location': {'lat': lat, 'lng': lng}
        })

    @action(detail=True, methods=['post'], url_path='check-in')
    def check_in(self, request, pk=None):
        """Add GPS check-in during visit"""
        visit = self.get_object()
        
        if visit.status != 'active':
            return Response(
                {'detail': 'Cannot check-in to inactive visit'},
                status=status.HTTP_400_BAD_REQUEST
            )

        lat = request.data.get('lat')
        lng = request.data.get('lng')
        address = request.data.get('address', '')
        
        if not lat or not lng:
            return Response(
                {'detail': 'GPS coordinates are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create GPS check-in
        checkin = GPSCheckIn.objects.create(
            visit=visit,
            lat=lat,
            lng=lng,
            address=address
        )

        return Response({
            'detail': 'GPS check-in recorded',
            'checkin_id': checkin.id,
            'timestamp': checkin.timestamp
        })

    @action(detail=True, methods=['post'], url_path='end')
    def end_visit(self, request, pk=None):
        """End visit with final GPS location"""
        visit = self.get_object()
        
        if visit.status != 'active':
            return Response(
                {'detail': 'Visit is not active.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update end location
        lat = request.data.get('lat')
        lng = request.data.get('lng')
        
        visit.status = 'completed'
        visit.ended_at = timezone.now()
        
        if lat and lng:
            visit.end_lat = lat
            visit.end_lng = lng
        
        visit.save()
        
        return Response({
            'detail': 'Visit completed successfully',
            'duration_minutes': visit.duration_minutes,
            'distance_km': visit.distance_km
        })

    @action(detail=True, methods=['patch'], url_path='cancel')
    def cancel_visit(self, request, pk=None):
        visit = self.get_object()
        visit.status   = 'cancelled'
        visit.ended_at = timezone.now()
        visit.save(update_fields=['status', 'ended_at'])
        return Response({'detail': 'Visit cancelled successfully'})

    @action(detail=False, methods=['get'], url_path='live-tracking')
    def live_tracking(self, request):
        """Get live location of all active field staff"""
        user = request.user
        if user.role not in ['owner', 'manager']:
            return Response(
                {'detail': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Get all active visits
        active_visits = FieldVisit.objects.filter(
            status='active'
        ).select_related('staff', 'lead').prefetch_related('checkins')

        tracking_data = []
        for visit in active_visits:
            latest_location = visit.latest_location
            tracking_data.append({
                'visit_id': visit.id,
                'staff_name': visit.staff.full_name,
                'staff_phone': visit.staff.phone,
                'lead_name': visit.lead.name,
                'lead_phone': visit.lead.phone,
                'started_at': visit.started_at,
                'latest_location': latest_location,
                'checkin_count': visit.checkins.count()
            })

        return Response({
            'active_visits': tracking_data,
            'total_active': len(tracking_data)
        })


class LocationTrackingViewSet(viewsets.ModelViewSet):
    """Real-time location tracking for field staff"""
    permission_classes = [IsAuthenticated]
    serializer_class = LocationTrackingSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['user', 'field_visit', 'is_active']
    ordering = ['-timestamp']
    queryset = LocationTracking.objects.all().select_related('user', 'field_visit')
    
    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()
        
        if user.role == 'owner':
            return qs
        elif user.role == 'manager':
            # Managers can see locations of their branch staff
            return qs.filter(user__branch=user.branch)
        else:
            # Staff can only see their own locations
            return qs.filter(user=user)
    
    def perform_create(self, serializer):
        # Deactivate previous locations for this user
        LocationTracking.objects.filter(user=self.request.user, is_active=True).update(is_active=False)
        serializer.save(user=self.request.user, is_active=True)


class LiveTrackingView(APIView):
    """
    Real-time GPS tracking for field staff
    GET /field-visits/live-tracking/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        
        # Only owners and managers can view live tracking
        if user.role not in ['owner', 'manager']:
            return Response(
                {'detail': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Get active locations from LocationTracking
        active_locations = LocationTracking.objects.filter(
            is_active=True
        ).select_related('user', 'field_visit__lead')

        # Filter by branch for managers
        if user.role == 'manager':
            active_locations = active_locations.filter(user__branch=user.branch)

        locations = []
        for location in active_locations:
            location_data = {
                'staff_id': location.user.id,
                'staff_name': location.user.full_name,
                'latitude': float(location.latitude),
                'longitude': float(location.longitude),
                'accuracy': location.accuracy,
                'timestamp': location.timestamp,
                'field_visit_id': location.field_visit.id if location.field_visit else None
            }
            
            if location.field_visit and location.field_visit.lead:
                location_data['lead_name'] = location.field_visit.lead.name
                location_data['lead_phone'] = location.field_visit.lead.phone
                location_data['lead_address'] = location.field_visit.lead.notes if location.field_visit.lead.notes else ''
            
            locations.append(location_data)
        
        return Response({'locations': locations, 'timestamp': timezone.now().isoformat()})


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
