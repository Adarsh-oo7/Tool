from django.utils import timezone
from datetime import timedelta
from django.db.models import Q
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from core.mixins import BranchScopedMixin
from core.permissions import IsManager, IsStaffOrAbove

from .models import Customer, Lead, LeadActivity, FollowUp
from .serializers import (
    CustomerSerializer, CustomerDetailSerializer,
    LeadSerializer, LeadListSerializer,
    LeadActivitySerializer, FollowUpSerializer,
)


class CustomerViewSet(viewsets.ModelViewSet):
    """
    Customer profile management by phone number.
    Owner/Manager: full access
    Staff: read-only access
    """
    permission_classes = [IsAuthenticated, IsStaffOrAbove]
    filter_backends    = [DjangoFilterBackend, filters.SearchFilter]
    search_fields      = ['phone', 'name', 'email']
    filterset_fields   = ['gender', 'location']

    def get_queryset(self):
        user = self.request.user
        qs = Customer.objects.all().prefetch_related('preferred_segments', 'leads')
        
        if user.role in ['owner', 'admin'] or user.is_superuser:
            return qs
        if user.role in ['manager', 'sub_manager']:
            # Managers see customers who have leads in their branch
            return qs.filter(leads__branch=user.branch).distinct()
        # Staff can only read
        return qs

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return CustomerDetailSerializer
        return CustomerSerializer

    def get_permissions(self):
        if self.action == 'destroy':
            # Only owner/manager can delete
            user = self.request.user
            if user.role not in ['owner', 'admin', 'manager', 'sub_manager'] and not user.is_superuser:
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied("Only owners and managers can delete customer profiles")
        return super().get_permissions()

    @action(detail=False, methods=['get'], url_path='by-phone/(?P<phone>[^/]+)')
    def by_phone(self, request, phone=None):
        """GET /api/v1/leads/customers/by-phone/{phone}/ - Find customer by phone number"""
        try:
            customer = Customer.objects.get(phone=phone)
            serializer = CustomerDetailSerializer(customer)
            return Response(serializer.data)
        except Customer.DoesNotExist:
            return Response({'detail': 'Customer not found', 'exists': False}, status=200)

    @action(detail=True, methods=['post'], url_path='add-timeline-event')
    def add_timeline_event(self, request, pk=None):
        """POST /api/v1/leads/customers/{id}/add-timeline-event/ - Add event to timeline"""
        customer = self.get_object()
        event_type = request.data.get('event_type')
        details = request.data.get('details')
        
        if not event_type or not details:
            return Response({'detail': 'event_type and details are required'}, status=400)
        
        customer.add_timeline_event(event_type, details)
        serializer = CustomerSerializer(customer)
        return Response(serializer.data)


class LeadViewSet(BranchScopedMixin, viewsets.ModelViewSet):
    """
    Full CRUD on leads with role-based scoping:
    - Owner: all leads
    - Manager: branch leads
    - Staff/Telecaller: only their assigned leads
    """
    permission_classes = [IsAuthenticated, IsStaffOrAbove]
    filter_backends    = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields   = ['stage', 'source', 'segment', 'assigned_to', 'branch']
    search_fields      = ['name', 'phone', 'email']
    ordering_fields    = ['created_at', 'score', 'name']
    ordering           = ['-created_at']

    def get_queryset(self):
        user = self.request.user
        qs   = Lead.objects.all().select_related('branch', 'segment', 'assigned_to', 'created_by', 'customer')

        if user.role not in ['owner', 'admin'] and not user.is_superuser:
            if user.role in ['manager', 'sub_manager']:
                qs = qs.filter(branch=user.branch)
            else:
                from django.db.models import Q
                qs = qs.filter(Q(assigned_to=user) | Q(created_by=user))

        # Time-based filtering (applied to all roles)
        time_range = self.request.query_params.get('time_range')
        if time_range == 'today':
            qs = qs.filter(created_at__date=timezone.now().date())
        elif time_range == 'week':
            week_ago = timezone.now() - timedelta(days=7)
            qs = qs.filter(created_at__gte=week_ago)
        elif time_range == 'month':
            month_ago = timezone.now() - timedelta(days=30)
            qs = qs.filter(created_at__gte=month_ago)
        elif time_range == 'custom':
            start_date = self.request.query_params.get('start_date')
            end_date   = self.request.query_params.get('end_date')
            if start_date:
                qs = qs.filter(created_at__date__gte=start_date)
            if end_date:
                qs = qs.filter(created_at__date__lte=end_date)
        
        return qs

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response = self.get_paginated_response(serializer.data)
            
            # Add custom metadata for the dashboard
            from django.db.models import Count, Q
            total_count = queryset.count()
            total_converted = queryset.filter(stage='converted').count()
            total_hot = queryset.filter(Q(is_hot=True) | Q(customer__temperature='hot')).count()
            
            response.data['total_converted'] = total_converted
            response.data['total_hot'] = total_hot
            response.data['conversion_rate'] = round((total_converted / total_count * 100), 1) if total_count > 0 else 0
            
            return response

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def get_serializer_class(self):
        if self.action == 'list':
            return LeadListSerializer
        return LeadSerializer

    def perform_create(self, serializer):
        # Auto-create or link to Customer profile based on phone
        from .models import Customer
        phone = serializer.validated_data.get('phone')
        customer = None
        
        branch_obj = serializer.validated_data.get('branch')
        
        if phone:
            try:
                customer = Customer.objects.get(phone=phone)
            except Customer.DoesNotExist:
                # Create new customer profile
                customer = Customer.objects.create(
                    phone=phone,
                    name=serializer.validated_data.get('name', ''),
                    email=serializer.validated_data.get('email', ''),
                    age=serializer.validated_data.get('age'),
                    gender=serializer.validated_data.get('gender') or 'not_specified',
                    location=serializer.validated_data.get('location', ''),
                )
                
            # Add timeline event for lead creation
            branch_id_for_log = None
            if branch_obj:
                branch_id_for_log = getattr(branch_obj, 'id', branch_obj)
                
            customer.add_timeline_event('lead_created', {
                'source': serializer.validated_data.get('source'),
                'branch_id': branch_id_for_log,
            })
        
        # Determine branch if not explicitly provided
        branch = branch_obj
        user = self.request.user
        if not branch:
            if user.role not in ['owner', 'admin'] and not user.is_superuser:
                branch = user.branch
            else:
                # Owners/Admins should select a branch, but if they don't, pick the first one
                from branches.models import Branch
                branch = Branch.objects.first()

        # Auto-assign to staff creator if not provided
        assigned_to = serializer.validated_data.get('assigned_to')
        if not assigned_to and user.role not in ['owner', 'admin', 'manager', 'sub_manager'] and not user.is_superuser:
            assigned_to = user

        lead = serializer.save(
            created_by=user,
            assigned_to=assigned_to,
            branch=branch,
            customer=customer,
        )
        
        # Log activity
        from .models import LeadActivity
        LeadActivity.objects.create(
            lead=lead,
            actor=user,
            action='lead_created',
            detail=f'Lead created via {lead.get_source_display()}. Assigned to: {lead.assigned_to.full_name if lead.assigned_to else "Unassigned"}'
        )

        # Follow-up auto creation
        followup_choice = self.request.data.get('followup_choice')
        if followup_choice:
            from datetime import timedelta
            from django.utils import timezone
            from .models import FollowUp
            
            days = 0
            if followup_choice == '7_days': days = 7
            elif followup_choice == '1_month': days = 30
            elif followup_choice == '6_months': days = 180
            
            if days > 0:
                scheduled_date = timezone.now() + timedelta(days=days)
                FollowUp.objects.create(
                    lead=lead,
                    scheduled_date=scheduled_date,
                    followup_type='call',
                    note="Initial follow-up scheduled at lead creation",
                    created_by=self.request.user
                )
            elif followup_choice == 'custom':
                custom_date = self.request.data.get('followup_date')
                if custom_date:
                    from dateutil import parser
                    try:
                        parsed_date = parser.parse(custom_date)
                        if timezone.is_naive(parsed_date):
                            parsed_date = timezone.make_aware(parsed_date)
                    except (ValueError, TypeError):
                        # Fallback if parsing fails
                        parsed_date = timezone.now() + timedelta(days=1)
                        
                    FollowUp.objects.create(
                        lead=lead,
                        scheduled_date=parsed_date,
                        followup_type='call',
                        note="Custom follow-up scheduled at lead creation",
                        created_by=self.request.user
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
        uid   = request.data.get('assigned_to') or request.data.get('user_id')
        try:
            staff = User.objects.get(pk=uid)
        except (User.DoesNotExist, TypeError, ValueError):
            return Response({'detail': 'User not found.'}, status=400)
        lead.assigned_to = staff
        lead.save(update_fields=['assigned_to'])
        LeadActivity.objects.create(
            lead=lead,
            actor=request.user,
            action='assigned',
            detail=f'Lead assigned to {staff.full_name}',
        )
        return Response({'detail': f'Assigned to {staff.full_name}.'})


    @action(detail=False, methods=['get'], url_path='summary')
    def summary(self, request):
        """GET /api/v1/leads/leads/summary/ - Source-wise conversion stats"""
        from django.db.models import Count, Q
        # Use the same filtering logic as the list view
        qs = self.filter_queryset(self.get_queryset())
        
        stats = qs.values('source').annotate(
            total=Count('id'),
            converted=Count('id', filter=Q(stage='converted'))
        ).order_by('source')
        
        return Response(list(stats))


class LeadActivityViewSet(viewsets.ModelViewSet):
    """Activities for a specific lead."""
    permission_classes = [IsAuthenticated, IsStaffOrAbove]
    serializer_class   = LeadActivitySerializer
    filter_backends    = [DjangoFilterBackend]
    filterset_fields   = ['lead', 'action']  # model field is 'action' not 'activity_type'
    http_method_names  = ['get', 'post', 'head', 'options']  # activity log: no edit/delete

    def get_queryset(self):
        return LeadActivity.objects.select_related('lead', 'actor').all()

    def perform_create(self, serializer):
        serializer.save(actor=self.request.user)


class FollowUpViewSet(viewsets.ModelViewSet):
    """Follow-up scheduling and completion."""
    permission_classes = [IsAuthenticated, IsStaffOrAbove]
    serializer_class   = FollowUpSerializer
    filter_backends    = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields   = ['lead', 'completed', 'status', 'priority', 'assigned_to', 'followup_type']
    search_fields      = ['lead__name', 'lead__phone', 'note']
    ordering_fields    = ['scheduled_date', 'priority', 'created_at']
    ordering           = ['scheduled_date']

    def get_queryset(self):
        user = self.request.user
        qs   = FollowUp.objects.select_related('lead', 'created_by', 'assigned_to').all()
        
        # Time-frame filtering
        today = timezone.localdate()
        time_frame = self.request.query_params.get('time_frame')
        
        if time_frame == 'today':
            qs = qs.filter(scheduled_date__date=today)
        elif time_frame == 'tomorrow':
            qs = qs.filter(scheduled_date__date=today + timedelta(days=1))
        elif time_frame == 'upcoming':
            qs = qs.filter(scheduled_date__date__gt=today)
        elif time_frame == 'overdue':
            qs = qs.filter(scheduled_date__date__lt=today, completed=False)
            
        if user.role == 'owner':
            return qs
        if user.role in ['manager', 'sub_manager']:
            return qs.filter(lead__branch=user.branch)
        return qs.filter(Q(created_by=user) | Q(assigned_to=user))

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['patch'], url_path='done')
    def mark_done(self, request, pk=None):
        followup = self.get_object()
        outcome = request.data.get('outcome', '')
        status_reason = request.data.get('status_reason', '')
        
        try:
            followup.completed    = True
            followup.completed_at = timezone.now()
            followup.status = 'completed'
            followup.outcome = outcome
            followup.status_reason = status_reason
            followup.save()
            
            # Log activity on lead
            LeadActivity.objects.create(
                lead=followup.lead,
                actor=request.user,
                action='followup_completed',
                detail=f'Follow-up ({followup.get_followup_type_display()}) completed. Outcome: {outcome}'
            )
            
            # Schedule Next Follow-up if requested
            next_date = request.data.get('next_followup_date')
            if next_date:
                # Use flexible parsing for different date formats (DD-MM-YYYY vs YYYY-MM-DD)
                try:
                    from dateutil import parser
                    parsed_date = parser.parse(next_date, dayfirst=True)
                    # Handle timezone awareness (fix for offset-naive error)
                    if timezone.is_naive(parsed_date):
                        parsed_date = timezone.make_aware(parsed_date)
                except (ImportError, ValueError, TypeError):
                    # Fallback to simple normalization if parser fails
                    if isinstance(next_date, str):
                        parsed_date = next_date.replace('T', ' ')
                    else:
                        parsed_date = next_date
                
                FollowUp.objects.create(
                    lead=followup.lead,
                    scheduled_date=parsed_date,
                    followup_type=request.data.get('next_followup_type', followup.followup_type),
                    note=request.data.get('next_followup_note', 'Scheduled after previous follow-up'),
                    created_by=request.user,
                    assigned_to=followup.assigned_to or request.user,
                    priority=request.data.get('next_followup_priority', 'medium')
                )
                
            return Response({'detail': 'Follow-up marked as done.'})
        except Exception as e:
            # Print for server logs
            import traceback
            print(f"ERROR in mark_done: {str(e)}")
            traceback.print_exc()
            return Response({'detail': f'Validation Error: {str(e)}'}, status=400)

    @action(detail=False, methods=['post'], url_path='bulk-auto-assign')
    def bulk_auto_assign(self, request):
        """POST /api/v1/leads/followups/bulk-auto-assign/"""
        if request.user.role not in ['owner', 'manager', 'sub_manager']:
            return Response({'detail': 'Permission denied.'}, status=403)
            
        date_str = request.data.get('date')
        if not date_str:
            # Default to tomorrow
            target_date = timezone.localdate() + timedelta(days=1)
        else:
            try:
                from dateutil import parser
                target_date = parser.parse(date_str).date()
            except:
                target_date = timezone.localdate() + timedelta(days=1)

        # Get unassigned follow-ups for that date
        unassigned_followups = FollowUp.objects.filter(
            scheduled_date__date=target_date,
            assigned_to__isnull=True,
            completed=False
        )
        
        count = 0
        for followup in unassigned_followups:
            lead = followup.lead
            # Pass type context for smarter auto_assign logic
            assigned_staff = lead.auto_assign(task_type=followup.followup_type)
            
            if assigned_staff:
                lead.save()
                followup.assigned_to = assigned_staff
                followup.save()
                count += 1
                
        return Response({
            'detail': f'Successfully assigned {count} follow-ups for {target_date}.',
            'count': count
        })

    @action(detail=True, methods=['post'], url_path='assign')
    def assign(self, request, pk=None):
        """POST /api/v1/leads/followups/{id}/assign/ — {'assigned_to': <user_id>}"""
        if request.user.role not in ['owner', 'manager', 'sub_manager']:
            return Response({'detail': 'Permission denied.'}, status=403)
            
        from django.contrib.auth import get_user_model
        User  = get_user_model()
        followup = self.get_object()
        uid = request.data.get('assigned_to')
        
        if not uid:
            # Smart Auto-Assign with type context
            staff = followup.lead.auto_assign(task_type=followup.followup_type)
            if not staff:
                return Response({'detail': 'No suitable staff found for auto-assignment.'}, status=400)
            followup.assigned_to = staff
            followup.save(update_fields=['assigned_to'])
            return Response({'detail': f'Smart assigned to {staff.full_name}.', 'assigned_to': staff.id})

        try:
            staff = User.objects.get(pk=uid)
        except (User.DoesNotExist, TypeError, ValueError):
            return Response({'detail': 'User not found.'}, status=400)
            
        followup.assigned_to = staff
        followup.save(update_fields=['assigned_to'])
        
        # Optionally update the lead's assignment as well
        if request.data.get('update_lead', True):
            lead = followup.lead
            lead.assigned_to = staff
            lead.save(update_fields=['assigned_to'])
            
            # Log activity on lead
            from .models import LeadActivity
            LeadActivity.objects.create(
                lead=lead,
                actor=request.user,
                action='assigned',
                detail=f'Lead re-assigned to {staff.full_name} via follow-up assignment'
            )
        
        return Response({'detail': f'Follow-up assigned to {staff.full_name}.'})
