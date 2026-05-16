from django.contrib.auth import get_user_model
from rest_framework import generics, status, viewsets, filters
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from django_filters.rest_framework import DjangoFilterBackend

from core.permissions import IsOwner, IsManager, IsStaffOrAbove, HasDynamicPermission
from .models import StaffPermission, ProfileUpdateRequest
from .serializers import (
    ChangePasswordSerializer,
    CustomTokenObtainPairSerializer,
    FCMTokenSerializer,
    StaffListSerializer,
    StaffPermissionSerializer,
    UserCreateSerializer,
    UserSerializer,
    UserUpdateSerializer,
    ProfileUpdateRequestSerializer,
)

User = get_user_model()


# ── Auth endpoints ─────────────────────────────────────────────────────────────

class LoginView(TokenObtainPairView):
    """POST /api/v1/auth/login/"""
    permission_classes = [AllowAny]
    serializer_class   = CustomTokenObtainPairSerializer


class MeView(generics.RetrieveUpdateAPIView):
    """GET/PATCH /api/v1/auth/me/"""
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    def get_serializer_class(self):
        if self.request.method in ('PUT', 'PATCH'):
            return UserUpdateSerializer
        return UserSerializer

    def patch(self, request, *args, **kwargs):
        user = self.get_object()
        
        # Convert QueryDict to standard dict for JSON storage
        data = request.data.dict() if hasattr(request.data, 'dict') else request.data
        
        # If profile is already completed, any further update must be via request
        if user.profile_completed:
            # Check if there's already a pending request
            if ProfileUpdateRequest.objects.filter(user=user, status='pending').exists():
                return Response(
                    {'detail': 'You already have a pending profile update request.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # We filter out files from data to ensure JSON serialization in ProfileUpdateRequest
            serializable_data = {k: v for k, v in data.items() if not hasattr(v, 'read')}
            
            ProfileUpdateRequest.objects.create(
                user=user,
                requested_data=serializable_data
            )
            return Response({
                'detail': 'Profile update request submitted for admin approval.',
                'status': 'pending_approval'
            })

        # First time update: allow direct modification AND create initial approval request
        response = super().patch(request, *args, **kwargs)
        if response.status_code == 200:
            user.profile_completed = True
            user.save(update_fields=['profile_completed'])
            
            # Create an initial request so the manager has something to approve
            if not ProfileUpdateRequest.objects.filter(user=user, status='pending').exists():
                ProfileUpdateRequest.objects.create(
                    user=user,
                    requested_data={'_initial_setup': True}
                )
            
            # Update the response data so the frontend knows it is completed
            if isinstance(response.data, dict):
                response.data['profile_completed'] = True
        return response


class ChangePasswordView(generics.GenericAPIView):
    """POST /api/v1/auth/change-password/"""
    permission_classes = [IsAuthenticated]
    serializer_class   = ChangePasswordSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'detail': 'Password updated successfully.'})


class FCMTokenView(generics.GenericAPIView):
    """POST /api/v1/auth/fcm-token/"""
    permission_classes = [IsAuthenticated]
    serializer_class   = FCMTokenSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        request.user.fcm_token = serializer.validated_data['fcm_token']
        request.user.save(update_fields=['fcm_token'])
        return Response({'detail': 'FCM token updated.'})


# ── User management ────────────────────────────────────────────────────────────

class UserViewSet(viewsets.ModelViewSet):
    """
    /api/v1/accounts/users/
    - list/retrieve: IsManager — owner sees all, manager sees own branch
    - create:        IsOwner only
    - update:        IsOwner only
    - destroy:       IsOwner only → soft delete
    """
    filter_backends  = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['branch', 'is_active', 'staff_type']
    search_fields    = ['full_name', 'email', 'phone', 'employee_id']
    ordering_fields  = ['full_name', 'created_at']
    
    permission_map = {
        'list':    'staff:view',
        'retrieve':'staff:view',
        'create':  'staff:create',
        'update':  'staff:edit',
        'partial_update': 'staff:edit',
        'destroy': 'staff:delete',
    }

    def get_queryset(self):
        user = self.request.user
        qs   = User.objects.all().select_related('branch')
        
        # Handle comma-separated roles
        roles = self.request.query_params.get('role')
        if roles:
            role_list = roles.split(',')
            if len(role_list) > 1:
                qs = qs.filter(role__in=role_list)
            else:
                qs = qs.filter(role=role_list[0])
        
        if user.role == 'owner':
            return qs
            
        if not user.has_permission('staff:view'):
            return qs.none()
            
        return qs.filter(branch=user.branch)

    def get_serializer_class(self):
        if self.action == 'list':
            return StaffListSerializer
        if self.action == 'create':
            return UserCreateSerializer
        if self.action in ('update', 'partial_update'):
            return UserUpdateSerializer
        return UserSerializer

    def get_permissions(self):
        # Always check dynamic permissions first for staff/manager roles
        perms = [IsAuthenticated(), HasDynamicPermission()]
        
        if self.action == 'destroy':
            perms.append(IsOwner())
        elif self.action in ('create', 'update', 'partial_update'):
            perms.append(IsManager())
        else:
            perms.append(IsStaffOrAbove())
        return perms

    def perform_destroy(self, instance):
        """Soft delete — never actually delete users."""
        instance.is_active = False
        instance.save(update_fields=['is_active'])

    @action(detail=True, methods=['post'], url_path='set-role', permission_classes=[IsAuthenticated, IsOwner])
    def set_role(self, request, pk=None):
        """POST /api/v1/accounts/users/{id}/set-role/  body: {"role": "manager"}"""
        VALID_ROLES = [r[0] for r in User.ROLE_CHOICES]
        role = request.data.get('role')
        if role not in VALID_ROLES:
            return Response(
                {'detail': f'Invalid role. Choices: {VALID_ROLES}'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user = self.get_object()
        user.role = role
        user.save(update_fields=['role'])
        return Response({'detail': f'Role set to {role}.', 'user': UserSerializer(user).data})

    @action(detail=True, methods=['patch'], url_path='activate', permission_classes=[IsAuthenticated, IsOwner])
    def activate(self, request, pk=None):
        user = self.get_object()
        user.is_active = True
        user.save(update_fields=['is_active'])
        return Response({'detail': f'{user.full_name} activated.'})

    @action(detail=True, methods=['post'], url_path='set-branch', permission_classes=[IsAuthenticated, IsOwner])
    def set_branch(self, request, pk=None):
        branch_id = request.data.get('branch_id')
        user = self.get_object()
        user.branch_id = branch_id
        user.save(update_fields=['branch'])
        return Response({'detail': f'Branch updated.', 'user': UserSerializer(user).data})

    @action(detail=True, methods=['post'], url_path='terminate', permission_classes=[IsAuthenticated, IsOwner])
    def terminate(self, request, pk=None):
        reason = request.data.get('reason', 'No reason provided')
        user = self.get_object()
        user.is_active = False
        # Append termination reason to notes
        user.notes = (user.notes or "") + f"\n[TERMINATION REASON]: {reason}"
        user.save(update_fields=['is_active', 'notes'])
        return Response({'detail': f'User {user.full_name} terminated.', 'user': UserSerializer(user).data})


class StaffByBranchView(generics.ListAPIView):
    """GET /api/v1/accounts/staff/?branch_id=1"""
    permission_classes = [IsAuthenticated, IsManager]
    serializer_class   = StaffListSerializer

    def get_queryset(self):
        branch_id = self.request.query_params.get('branch_id')
        qs        = User.objects.filter(is_active=True).select_related('branch')
        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        elif self.request.user.role != 'owner':
            qs = qs.filter(branch=self.request.user.branch)
        return qs


class StaffPermissionViewSet(viewsets.ModelViewSet):
    """
    /api/v1/accounts/staff-permissions/
    - list/retrieve: IsManager (staff can read their own record only)
    - create/update/destroy: IsOwner
    """
    serializer_class   = StaffPermissionSerializer
    filter_backends    = [DjangoFilterBackend]
    filterset_fields   = ['user']

    def get_queryset(self):
        user = self.request.user
        qs = StaffPermission.objects.select_related('user', 'modified_by')
        # Staff can only see their own permission record
        if user.role not in ('owner', 'admin', 'manager', 'sub_manager') and not user.is_superuser:
            return qs.filter(user=user)
        return qs.all()

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsAuthenticated(), IsOwner()]
        # Allow any authenticated user to read (queryset handles data scoping)
        return [IsAuthenticated()]

    def perform_update(self, serializer):
        serializer.save(modified_by=self.request.user)


class ProfileUpdateRequestViewSet(viewsets.ModelViewSet):
    """
    Admins/Managers only.
    List, approve, reject profile update requests.
    """
    queryset = ProfileUpdateRequest.objects.all()
    serializer_class = ProfileUpdateRequestSerializer
    permission_classes = [IsAuthenticated, IsManager]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'owner':
            return ProfileUpdateRequest.objects.all().select_related('user')
        return ProfileUpdateRequest.objects.filter(user__branch=user.branch).select_related('user')

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsManager])
    def approve(self, request, pk=None):
        obj = self.get_object()
        if obj.status != 'pending':
            return Response({'detail': 'Request is already processed.'}, status=400)
        
        user = obj.user
        data = obj.requested_data
        
        # Apply changes to user
        for field, value in data.items():
            if hasattr(user, field):
                setattr(user, field, value)
        
        user.is_profile_verified = True
        user.save()
        
        obj.status = 'approved'
        obj.admin_note = request.data.get('admin_note', '')
        obj.save()
        
        return Response({'detail': 'Profile update approved and applied.'})

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsManager])
    def reject(self, request, pk=None):
        obj = self.get_object()
        if obj.status != 'pending':
            return Response({'detail': 'Request is already processed.'}, status=400)
        
        obj.status = 'rejected'
        obj.admin_note = request.data.get('admin_note', '')
        obj.save()
        
        return Response({'detail': 'Profile update rejected.'})


class CreateSampleDataView(APIView):
    """Create sample data for testing"""
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            from django.contrib.auth import get_user_model
            from branches.models import Branch, Company
            from datetime import datetime
            import random

            User = get_user_model()

            # Create company
            company, created = Company.objects.get_or_create(
                name='Bindu Jewellery',
                defaults={
                    'address': 'Bangalore, Karnataka',
                    'phone': '+918012345678',
                    'email': 'info@bindujewellery.com'
                }
            )

            # Create admin user
            admin, created = User.objects.get_or_create(
                email='admin@bindujewellery.com',
                defaults={
                    'full_name': 'Admin User',
                    'phone': '+918011111111',
                    'role': 'owner',
                    'is_active': True,
                    'is_staff': True,
                    'is_superuser': True
                }
            )

            if created:
                admin.set_password('password123')
                admin.save()

            # Create branch
            branch, created = Branch.objects.get_or_create(
                name='Main Branch - MG Road',
                defaults={
                    'company': company,
                    'address': '123 MG Road, Bangalore',
                    'phone': '+918012345678',
                    'lat': 12.9716,
                    'lng': 77.5946,
                    'is_active': True
                }
            )

            # Assign branch to admin user
            admin.branch = branch
            admin.save()

            # Create gamification profile for admin
            from gamification.models import GamificationProfile
            try:
                profile, profile_created = GamificationProfile.objects.get_or_create(
                    user=admin,
                    defaults={
                        'total_points': 100,
                        'current_level': 2,
                        'level_name': 'Intermediate',
                        'badges_count': 0,
                        'achievements_count': 0,
                        'streak_days': 0
                    }
                )
            except Exception as e:
                print(f"Error creating gamification profile: {e}")
                # Continue without gamification profile

            # Create additional sample users
            users_data = [
                {
                    'email': 'manager1@bindujewellery.com',
                    'full_name': 'Manager One',
                    'phone': '+918022222222',
                    'role': 'manager',
                    'branch': branch,
                    'is_staff': True
                },
                {
                    'email': 'staff1@bindujewellery.com',
                    'full_name': 'Staff One',
                    'phone': '+918033333333',
                    'role': 'staff',
                    'branch': branch
                },
                {
                    'email': 'telecaller1@bindujewellery.com',
                    'full_name': 'Telecaller One',
                    'phone': '+918055555555',
                    'role': 'telecaller',
                    'branch': branch
                }
            ]

            for user_data in users_data:
                user, created = User.objects.get_or_create(
                    email=user_data['email'],
                    defaults={
                        **user_data,
                        'is_active': True
                    }
                )
                if created:
                    user.set_password('password123')
                    user.save()
                    print(f'Created user: {user.full_name}')

            # Create sample tasks
            from tasks.models import Task
            tasks_data = [
                {
                    'title': 'Follow up with lead Rahul',
                    'description': 'Contact Rahul Sharma regarding gold necklace inquiry',
                    'assigned_to': User.objects.get(email='staff1@bindujewellery.com'),
                    'branch': branch,
                    'priority': 'high',
                    'status': 'pending',
                    'created_by': admin
                },
                {
                    'title': 'Prepare sales report',
                    'description': 'Generate weekly sales report for management',
                    'assigned_to': User.objects.get(email='manager1@bindujewellery.com'),
                    'branch': branch,
                    'priority': 'medium',
                    'status': 'in_progress',
                    'created_by': admin
                }
            ]

            for task_data in tasks_data:
                task, created = Task.objects.get_or_create(
                    title=task_data['title'],
                    defaults=task_data
                )
                if created:
                    print(f'Created task: {task.title}')

            # Create sample leads for the branch
            from leads.models import Lead
            leads_data = [
                {
                    'name': 'Rahul Sharma',
                    'phone': '+918012345678',
                    'email': 'rahul@email.com',
                    'source': 'website',
                    'stage': 'interested',
                    'branch': branch,
                    'assigned_to': User.objects.get(email='staff1@bindujewellery.com'),
                    'created_by': admin
                },
                {
                    'name': 'Priya Patel',
                    'phone': '+918098765432',
                    'email': 'priya@email.com',
                    'source': 'referral',
                    'stage': 'negotiation',
                    'branch': branch,
                    'assigned_to': User.objects.get(email='manager1@bindujewellery.com'),
                    'created_by': admin
                }
            ]

            for lead_data in leads_data:
                lead, created = Lead.objects.get_or_create(
                    phone=lead_data['phone'],
                    defaults=lead_data
                )
                if created:
                    print(f'Created lead: {lead.name}')

            # Create sample sales for the branch
            from sales.models import Sale
            sales_data = [
                {
                    'lead': Lead.objects.get(phone='+918012345678'),
                    'branch': branch,
                    'staff': User.objects.get(email='staff1@bindujewellery.com'),
                    'amount': 25000,
                    'product_name': 'Gold Necklace',
                    'notes': '22ct gold necklace with pendant'
                },
                {
                    'lead': Lead.objects.get(phone='+918098765432'),
                    'branch': branch,
                    'staff': User.objects.get(email='manager1@bindujewellery.com'),
                    'amount': 45000,
                    'product_name': 'Diamond Ring',
                    'notes': '18ct diamond ring with platinum band'
                }
            ]

            for sale_data in sales_data:
                sale, created = Sale.objects.get_or_create(
                    lead=sale_data['lead'],
                    defaults=sale_data
                )
                if created:
                    print(f'Created sale: {sale.amount}')

            # Create sample attendance records
            from attendance.models import Attendance
            from django.utils import timezone
            attendance_data = [
                {
                    'user': User.objects.get(email='staff1@bindujewellery.com'),
                    'branch': branch,
                    'date': timezone.localdate(),
                    'check_in_time': timezone.now().replace(hour=9, minute=30),
                    'status': 'present',
                    'check_in_type': 'gps'
                },
                {
                    'user': User.objects.get(email='manager1@bindujewellery.com'),
                    'branch': branch,
                    'date': timezone.localdate(),
                    'check_in_time': timezone.now().replace(hour=9, minute=0),
                    'status': 'present',
                    'check_in_type': 'gps'
                }
            ]

            for attendance_data in attendance_data:
                attendance, created = Attendance.objects.get_or_create(
                    user=attendance_data['user'],
                    date=attendance_data['date'],
                    defaults=attendance_data
                )
                if created:
                    print(f'Created attendance for: {attendance.user.full_name}')

            # Create sample field visits
            from field_visits.models import FieldVisit
            field_visits_data = [
                {
                    'lead': Lead.objects.get(phone='+918012345678'),
                    'staff': User.objects.get(email='staff1@bindujewellery.com'),
                    'branch': branch,
                    'status': 'completed',
                    'started_at': timezone.now().replace(hour=10, minute=0),
                    'ended_at': timezone.now().replace(hour=11, minute=30),
                    'duration_minutes': 90
                },
                {
                    'lead': Lead.objects.get(phone='+918098765432'),
                    'staff': User.objects.get(email='manager1@bindujewellery.com'),
                    'branch': branch,
                    'status': 'active',
                    'started_at': timezone.now().replace(hour=14, minute=0),
                    'duration_minutes': 30
                }
            ]

            for visit_data in field_visits_data:
                visit, created = FieldVisit.objects.get_or_create(
                    lead=visit_data['lead'],
                    staff=visit_data['staff'],
                    defaults=visit_data
                )
                if created:
                    print(f'Created field visit: {visit.lead.name}')

            return Response({
                'success': True,
                'message': 'Sample data created successfully',
                'login_credentials': {
                    'username': 'admin',
                    'password': 'password123'
                }
            })

        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=400)
