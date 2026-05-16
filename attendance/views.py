from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone

from django.core.exceptions import ValidationError as DjangoValidationError
from core.permissions import IsManager
from .models import Attendance, AttendanceBreak, AttendanceSchedule
from .serializers import (
    AttendanceSerializer, GPSCheckInSerializer, AttendanceBreakSerializer,
    AttendanceScheduleSerializer
)


class AttendanceViewSet(viewsets.ModelViewSet):
    """
    Enhanced GPS + photo check-in system.
    - Staff/Field: create own check-in (one per day enforced by model unique_together)
    - Manager/Owner: view branch records + approve/reject
    """
    permission_classes = [IsAuthenticated]
    serializer_class   = AttendanceSerializer
    filter_backends    = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields   = ['status', 'user', 'date', 'check_in_type', 'branch']
    ordering           = ['-date']

    def get_queryset(self):
        user = self.request.user
        qs   = Attendance.objects.select_related('user', 'approved_by', 'branch').all()
        if user.role == 'owner':
            branch_id = self.request.query_params.get('branch')
            if branch_id:
                qs = qs.filter(branch_id=branch_id)
            return qs
        if user.role == 'manager':
            return qs.filter(user__branch=user.branch)
        return qs.filter(user=user)

    def perform_create(self, serializer):
        from rest_framework.exceptions import ValidationError
        today = timezone.localdate()
        if Attendance.objects.filter(user=self.request.user, date=today).exists():
            raise ValidationError({'detail': 'You have already checked in today.'})
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['post'], url_path='gps-checkin')
    def gps_checkin(self, request):
        """
        GPS-based check-in with location validation
        POST /attendance/attendance/gps-checkin/
        Body: {"lat": 8.1234, "lng": 76.5678, "notes": "Optional notes"}
        """
        from rest_framework.exceptions import ValidationError
        from django.core.exceptions import ValidationError as DjangoValidationError
        
        today = timezone.localdate()
        
        # Check if already checked in today
        if Attendance.objects.filter(user=request.user, date=today).exists():
            return Response(
                {'detail': 'You have already checked in today.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Create attendance record with GPS validation
            attendance = Attendance.objects.create(
                user=request.user,
                date=today,
                check_in_type='gps',
                check_in_lat=request.data.get('lat'),
                check_in_lng=request.data.get('lng'),
                notes=request.data.get('notes', ''),
                check_in_time=timezone.now()
            )
            
            # Return response with distance info
            response_data = {
                'id': attendance.id,
                'status': attendance.status,
                'distance_from_branch': attendance.distance_from_branch,
                'is_within_branch_radius': attendance.is_within_branch_radius(),
                'message': 'GPS check-in recorded successfully'
            }
            
            if attendance.status == 'present':
                response_data['message'] = 'GPS check-in approved automatically (within branch radius)'
            elif attendance.status == 'pending_approval':
                response_data['message'] = 'GPS check-in requires manager approval (outside branch radius)'
            
            return Response(response_data, status=status.HTTP_201_CREATED)
            
        except DjangoValidationError as e:
            msg = e.messages[0] if hasattr(e, 'messages') else str(e)
            return Response({'detail': msg}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='photo-checkin')
    def photo_checkin(self, request):
        """
        Photo-based check-in for manual verification
        POST /attendance/attendance/photo-checkin/
        Body: FormData with 'photo' file and optional 'notes'
        """
        from rest_framework.exceptions import ValidationError
        
        today = timezone.localdate()
        
        # Check if already checked in today
        if Attendance.objects.filter(user=request.user, date=today).exists():
            return Response(
                {'detail': 'You have already checked in today.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        photo = request.FILES.get('photo')
        if not photo:
            return Response(
                {'detail': 'Photo is required for photo check-in.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            attendance = Attendance.objects.create(
                user=request.user,
                date=today,
                check_in_type='photo',
                photo=photo,
                notes=request.data.get('notes', ''),
                check_in_time=timezone.now()
            )
            
            return Response({
                'id': attendance.id,
                'status': attendance.status,
                'message': 'Photo check-in recorded successfully, awaiting manager approval'
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {'detail': f'Error processing photo: {str(e)}'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['get'], url_path='today')
    def today(self, request):
        """Get today's attendance record for the logged-in user"""
        today = timezone.localdate()
        attendance = Attendance.objects.filter(user=request.user, date=today).first()
        if not attendance:
            return Response({'detail': 'No record found', 'checked_in': False})
        
        serializer = self.get_serializer(attendance)
        data = serializer.data
        data['checked_in'] = True
        data['id'] = attendance.id # Ensure ID is always there for keys
        data['on_break'] = attendance.breaks.filter(end_time__isnull=True).exists()
        return Response(data)

    @action(detail=False, methods=['post'], url_path='checkout')
    def checkout(self, request):
        """
        Check-out for the day with optional GPS
        POST /attendance/attendance/checkout/
        """
        today = timezone.localdate()
        try:
            attendance = Attendance.objects.get(user=request.user, date=today)
            
            if attendance.check_out_time:
                return Response(
                    {'detail': 'You have already checked out today.'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # If on break, auto-end it
            active_break = attendance.breaks.filter(end_time__isnull=True).first()
            if active_break:
                active_break.end_time = timezone.now()
                active_break.save()

            attendance.check_out_time = timezone.now()
            attendance.check_out_lat  = request.data.get('lat')
            attendance.check_out_lng  = request.data.get('lng')
            attendance.save()
            
            return Response({
                'message': 'Check-out successful',
                'check_out_time': attendance.check_out_time
            })
            
        except Attendance.DoesNotExist:
            return Response(
                {'detail': 'No check-in record found for today.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except DjangoValidationError as e:
            msg = e.messages[0] if hasattr(e, 'messages') else str(e)
            return Response({'detail': msg}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='break-start')
    def break_start(self, request):
        """Start a break"""
        today = timezone.localdate()
        try:
            attendance = Attendance.objects.get(user=request.user, date=today)
            if attendance.check_out_time:
                return Response({'detail': 'Already checked out'}, status=400)
            
            if attendance.breaks.filter(end_time__isnull=True).exists():
                return Response({'detail': 'Already on break'}, status=400)
                
            AttendanceBreak.objects.create(
                attendance=attendance,
                reason=request.data.get('reason', 'Lunch/Tea Break')
            )
            return Response({'message': 'Break started'})
        except Attendance.DoesNotExist:
            return Response({'detail': 'Not checked in'}, status=400)

    @action(detail=False, methods=['post'], url_path='break-end')
    def break_end(self, request):
        """End a break"""
        today = timezone.localdate()
        try:
            attendance = Attendance.objects.get(user=request.user, date=today)
            active_break = attendance.breaks.filter(end_time__isnull=True).first()
            if not active_break:
                return Response({'detail': 'Not on break'}, status=400)
            
            active_break.end_time = timezone.now()
            active_break.save()
            return Response({'message': 'Break ended'})
        except Attendance.DoesNotExist:
            return Response({'detail': 'Not checked in'}, status=400)

    @action(detail=True, methods=['patch'], url_path='approve', permission_classes=[IsAuthenticated, IsManager])
    def approve(self, request, pk=None):
        record = self.get_object()
        record.status = 'present'
        record.approved_by = request.user
        record.save(update_fields=['status', 'approved_by'])
        return Response({'detail': 'Attendance approved.'})

    @action(detail=True, methods=['patch'], url_path='reject', permission_classes=[IsAuthenticated, IsManager])
    def reject(self, request, pk=None):
        record = self.get_object()
        record.status = 'rejected'
        record.approved_by = request.user
        record.save(update_fields=['status', 'approved_by'])
        return Response({'detail': 'Attendance rejected.'})


class BranchLocationView(APIView):
    """
    Get branch location for GPS validation
    GET /attendance/branch-location/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if not user.branch:
            return Response(
                {'detail': 'No branch assigned to user.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        branch = user.branch
        return Response({
            'branch_name': branch.name,
            'branch_address': branch.address,
            'lat': float(branch.lat) if branch.lat else None,
            'lng': float(branch.lng) if branch.lng else None,
            'allowed_radius_meters': 100  # Configurable radius
        })


class AttendanceScheduleViewSet(viewsets.ModelViewSet):
    """
    CRUD for attendance shifts and reminder schedules.
    Only accessible by Manager/Owner.
    """
    permission_classes = [IsAuthenticated, IsManager]
    serializer_class   = AttendanceScheduleSerializer
    queryset           = AttendanceSchedule.objects.all()

    def get_queryset(self):
        user = self.request.user
        if user.role == 'owner':
            return self.queryset
        return self.queryset.filter(branch=user.branch)
