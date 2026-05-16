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
    filterset_fields   = ['lead', 'outcome', 'staff']
    ordering_fields    = ['created_at', 'duration_seconds']
    ordering           = ['-created_at']

    def get_queryset(self):
        user = self.request.user
        qs   = CallLog.objects.select_related('lead', 'staff', 'lead__branch').all()
        
        # Branch scoping
        if user.role in ['owner', 'admin'] or user.is_superuser:
            branch_id = self.request.query_params.get('branch')
            if branch_id:
                qs = qs.filter(lead__branch_id=branch_id)
        elif user.role in ['manager', 'sub_manager']:
            branch_id = self.request.query_params.get('branch')
            if branch_id:
                qs = qs.filter(lead__branch_id=branch_id)
            else:
                qs = qs.filter(lead__branch=user.branch)
        else:
            qs = qs.filter(staff=user)

        # Time-based filtering
        from django.utils import timezone
        from datetime import timedelta
        
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
        
        # Aggregations
        from django.db.models import Count, Avg, Q
        stats = queryset.aggregate(
            total_calls=Count('id'),
            converted_count=Count('id', filter=Q(outcome='converted')),
            avg_duration=Avg('duration_seconds')
        )
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response = self.get_paginated_response(serializer.data)
            response.data.update({
                'total_calls': stats['total_calls'],
                'converted_count': stats['converted_count'],
                'avg_duration': round(stats['avg_duration'] or 0, 1)
            })
            return response

        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'results': serializer.data,
            'total_calls': stats['total_calls'],
            'converted_count': stats['converted_count'],
            'avg_duration': round(stats['avg_duration'] or 0, 1)
        })

    def perform_create(self, serializer):
        call_log = serializer.save(staff=self.request.user)
        
        # Auto-create FollowUp if date is provided
        if call_log.next_followup_date:
            from leads.models import FollowUp
            from django.utils import timezone
            import datetime
            
            # Convert date to datetime (start of day)
            scheduled_dt = timezone.make_aware(
                datetime.datetime.combine(call_log.next_followup_date, datetime.time.min)
            )
            
            FollowUp.objects.create(
                lead=call_log.lead,
                scheduled_date=scheduled_dt,
                followup_type='call',
                note=f"Scheduled after call outcome: {call_log.get_outcome_display()}",
                created_by=self.request.user,
                assigned_to=call_log.staff if call_log.staff.role == 'telecaller' else None
            )

        # Log activity on lead
        from leads.models import LeadActivity
        LeadActivity.objects.create(
            lead=call_log.lead,
            actor=self.request.user,
            action='call_logged',
            detail=f'Call logged: {call_log.get_outcome_display()}. Notes: {call_log.notes[:100]}'
        )

    def perform_update(self, serializer):
        call_log = serializer.save()
        # Log activity on lead
        from leads.models import LeadActivity
        LeadActivity.objects.create(
            lead=call_log.lead,
            actor=self.request.user,
            action='call_updated',
            detail=f'Call log updated: {call_log.get_outcome_display()}.'
        )
