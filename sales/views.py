from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from core.mixins import BranchScopedMixin
from core.permissions import IsStaffOrAbove

from .models import Sale
from .serializers import SaleSerializer


class SaleViewSet(BranchScopedMixin, viewsets.ModelViewSet):
    """Record and view sales — branch-scoped."""
    permission_classes = [IsAuthenticated, IsStaffOrAbove]
    serializer_class   = SaleSerializer
    filter_backends    = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields   = ['branch', 'segment', 'staff']
    ordering_fields    = ['created_at', 'amount']
    ordering           = ['-created_at']
    def get_queryset(self):
        qs = Sale.objects.all().select_related('lead', 'branch', 'segment', 'staff', 'campaign')
        
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
        from django.db.models import Sum
        totals = queryset.aggregate(
            total_weight=Sum('weight_grams'),
            total_amount=Sum('amount')
        )
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response = self.get_paginated_response(serializer.data)
            response.data['total_weight'] = totals['total_weight'] or 0
            response.data['total_amount'] = totals['total_amount'] or 0
            return response

        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'results': serializer.data,
            'total_weight': totals['total_weight'] or 0,
            'total_amount': totals['total_amount'] or 0
        })

    def perform_create(self, serializer):
        user = self.request.user
        staff = serializer.validated_data.get('staff')
        if not staff:
            staff = user
            
        serializer.save(
            staff=staff,
            branch=user.branch or None,   # ← simple: always use user.branch (None for owner = OK after model fix)
        )
