from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.db.models import Q, Count, Sum, Avg, F
from django.db.models.functions import Coalesce

from .models import (
    AlertType, AlertRule, Alert, AlertSubscription, AlertDigest, SmartSuggestion
)
from .serializers import (
    AlertTypeSerializer, AlertRuleSerializer, AlertSerializer,
    AlertSubscriptionSerializer, AlertDigestSerializer, SmartSuggestionSerializer
)
from core.permissions import IsManager


class AlertTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """View available alert types"""
    permission_classes = [IsAuthenticated]
    serializer_class = AlertTypeSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['category', 'severity']
    search_fields = ['name', 'description']

    def get_queryset(self):
        return AlertType.objects.filter(default_enabled=True)


class AlertRuleViewSet(viewsets.ModelViewSet):
    """Manage alert rules"""
    permission_classes = [IsAuthenticated, IsManager]
    serializer_class = AlertRuleSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['alert_type', 'metric', 'condition', 'is_active']
    search_fields = ['name', 'alert_type__name']

    def get_queryset(self):
        user = self.request.user
        qs = AlertRule.objects.all().select_related('alert_type', 'created_by').prefetch_related('target_users')
        
        if user.role == 'manager':
            return qs.filter(
                Q(target_roles__contains=[user.role]) |
                Q(target_users=user) |
                Q(created_by=user)
            ).distinct()
        
        return qs.filter(created_by=user)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'], url_path='test')
    def test_rule(self, request, pk=None):
        """Test an alert rule with current data"""
        rule = self.get_object()
        
        try:
            # Check if rule would trigger now
            current_value = self._get_metric_value(rule.metric, rule.time_period_hours)
            threshold = rule.threshold_value if rule.threshold_value is not None else rule.threshold_text
            
            would_trigger = self._evaluate_condition(current_value, rule.condition, threshold)
            
            return Response({
                'rule_name': rule.name,
                'current_value': current_value,
                'threshold': threshold,
                'condition': rule.condition,
                'would_trigger': would_trigger,
                'message': f"Rule {'would' if would_trigger else 'would not'} trigger with current data"
            })
            
        except Exception as e:
            return Response(
                {'detail': f'Error testing rule: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _get_metric_value(self, metric, time_period_hours):
        """Get current value for a metric"""
        from datetime import timedelta
        from sales.models import Sale
        from leads.models import Lead
        from calls.models import CallLog
        from attendance.models import Attendance
        
        cutoff_time = timezone.now() - timedelta(hours=time_period_hours)
        
        if metric == 'sales_count':
            return Sale.objects.filter(created_at__gte=cutoff_time).count()
        elif metric == 'sales_revenue':
            return float(Sale.objects.filter(created_at__gte=cutoff_time).aggregate(
                total=Coalesce(Sum('amount'), 0)
            )['total'] or 0)
        elif metric == 'leads_count':
            return Lead.objects.filter(created_at__gte=cutoff_time).count()
        elif metric == 'leads_converted':
            return Lead.objects.filter(
                stage='converted',
                updated_at__gte=cutoff_time
            ).count()
        elif metric == 'calls_made':
            return CallLog.objects.filter(created_at__gte=cutoff_time).count()
        elif metric == 'conversion_rate':
            total_leads = Lead.objects.filter(created_at__gte=cutoff_time).count()
            converted_leads = Lead.objects.filter(
                stage='converted',
                updated_at__gte=cutoff_time
            ).count()
            return (converted_leads / total_leads * 100) if total_leads > 0 else 0
        elif metric == 'attendance_rate':
            today = timezone.localdate()
            total_staff = Attendance.objects.filter(date=today).count()
            present_staff = Attendance.objects.filter(date=today, status='present').count()
            return (present_staff / total_staff * 100) if total_staff > 0 else 0
        else:
            return 0

    def _evaluate_condition(self, current_value, condition, threshold):
        """Evaluate if condition is met"""
        if condition == 'gt':
            return current_value > threshold
        elif condition == 'lt':
            return current_value < threshold
        elif condition == 'eq':
            return current_value == threshold
        elif condition == 'gte':
            return current_value >= threshold
        elif condition == 'lte':
            return current_value <= threshold
        elif condition == 'contains':
            return str(threshold).lower() in str(current_value).lower()
        elif condition == 'not_contains':
            return str(threshold).lower() not in str(current_value).lower()
        elif condition == 'is_null':
            return current_value is None
        elif condition == 'is_not_null':
            return current_value is not None
        else:
            return False


class AlertViewSet(viewsets.ModelViewSet):
    """View and manage alerts"""
    permission_classes = [IsAuthenticated]
    serializer_class = AlertSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status', 'severity', 'alert_type']
    ordering = ['-triggered_at']

    def get_queryset(self):
        user = self.request.user
        qs = Alert.objects.filter(recipients=user).select_related('rule', 'alert_type', 'acknowledged_by', 'resolved_by')
        
        if user.role == 'manager':
            # Managers can see alerts for their branch
            return qs.filter(
                Q(recipients=user) |
                Q(rule__target_roles__contains=[user.role])
            ).distinct()
        
        return qs

    @action(detail=True, methods=['post'], url_path='acknowledge')
    def acknowledge(self, request, pk=None):
        """Acknowledge an alert"""
        alert = self.get_object()
        
        if alert.status != 'active':
            return Response(
                {'detail': 'Alert cannot be acknowledged'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        alert.acknowledge(request.user)
        return Response({'detail': 'Alert acknowledged successfully'})

    @action(detail=True, methods=['post'], url_path='resolve')
    def resolve(self, request, pk=None):
        """Resolve an alert"""
        alert = self.get_object()
        
        if alert.status not in ['active', 'acknowledged']:
            return Response(
                {'detail': 'Alert cannot be resolved'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        alert.resolve(request.user)
        return Response({'detail': 'Alert resolved successfully'})

    @action(detail=True, methods=['post'], url_path='dismiss')
    def dismiss(self, request, pk=None):
        """Dismiss an alert"""
        alert = self.get_object()
        alert.dismiss(request.user)
        return Response({'detail': 'Alert dismissed successfully'})

    @action(detail=False, methods=['get'], url_path='my-alerts')
    def my_alerts(self, request):
        """Get alerts for current user with filtering options"""
        user = request.user
        status_filter = request.query_params.get('status', 'active')
        severity_filter = request.query_params.get('severity', None)
        
        queryset = Alert.objects.filter(recipients=user)
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        if severity_filter:
            queryset = queryset.filter(severity=severity_filter)
        
        queryset = queryset.select_related('alert_type', 'rule').order_by('-triggered_at')
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='statistics')
    def statistics(self, request):
        """Get alert statistics"""
        user = request.user
        
        # Base queryset
        queryset = Alert.objects.filter(recipients=user)
        
        # Statistics
        stats = {
            'total_alerts': queryset.count(),
            'active_alerts': queryset.filter(status='active').count(),
            'acknowledged_alerts': queryset.filter(status='acknowledged').count(),
            'resolved_alerts': queryset.filter(status='resolved').count(),
            'critical_alerts': queryset.filter(severity='critical', status='active').count(),
            'high_alerts': queryset.filter(severity='high', status='active').count(),
            'medium_alerts': queryset.filter(severity='medium', status='active').count(),
            'low_alerts': queryset.filter(severity='low', status='active').count(),
        }
        
        # Recent alerts (last 24 hours)
        yesterday = timezone.now() - timezone.timedelta(hours=24)
        stats['recent_alerts'] = queryset.filter(triggered_at__gte=yesterday).count()
        
        # Alerts by category
        stats['by_category'] = list(
            queryset.values('alert_type__category').annotate(
                count=Count('id')
            ).order_by('-count')
        )
        
        return Response(stats)


class AlertSubscriptionViewSet(viewsets.ModelViewSet):
    """Manage alert subscriptions"""
    permission_classes = [IsAuthenticated]
    serializer_class = AlertSubscriptionSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['is_subscribed']

    def get_queryset(self):
        return AlertSubscription.objects.filter(user=self.request.user).select_related('alert_type')

    @action(detail=False, methods=['post'], url_path='bulk-update')
    def bulk_update(self, request):
        """Bulk update alert subscriptions"""
        subscriptions = request.data.get('subscriptions', [])
        
        updated_count = 0
        for sub_data in subscriptions:
            alert_type_id = sub_data.get('alert_type_id')
            is_subscribed = sub_data.get('is_subscribed', True)
            channels = sub_data.get('notification_channels', {'in_app': True})
            
            try:
                subscription, created = AlertSubscription.objects.update_or_create(
                    user=request.user,
                    alert_type_id=alert_type_id,
                    defaults={
                        'is_subscribed': is_subscribed,
                        'notification_channels': channels
                    }
                )
                
                if not created:
                    subscription.is_subscribed = is_subscribed
                    subscription.notification_channels = channels
                    subscription.save(update_fields=['is_subscribed', 'notification_channels'])
                
                updated_count += 1
                
            except Exception as e:
                continue
        
        return Response({
            'detail': f'Updated {updated_count} subscriptions',
            'updated_count': updated_count
        })


class AlertDigestViewSet(viewsets.ReadOnlyModelViewSet):
    """View alert digests"""
    permission_classes = [IsAuthenticated]
    serializer_class = AlertDigestSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['period']
    ordering = ['-digest_date']

    def get_queryset(self):
        return AlertDigest.objects.filter(user=self.request.user).order_by('-digest_date')

    @action(detail=False, methods=['get'], url_path='current')
    def current_digest(self, request):
        """Get current period digest"""
        from datetime import date
        
        today = date.today()
        
        # Get or create current digests
        digests = []
        
        # Daily digest
        daily_digest, _ = AlertDigest.objects.get_or_create(
            user=request.user,
            period='daily',
            digest_date=today,
            defaults={'alert_count': 0}
        )
        
        # Weekly digest (current week)
        week_start = today - timezone.timedelta(days=today.weekday())
        weekly_digest, _ = AlertDigest.objects.get_or_create(
            user=request.user,
            period='weekly',
            digest_date=week_start,
            defaults={'alert_count': 0}
        )
        
        digests.extend([daily_digest, weekly_digest])
        
        return Response(AlertDigestSerializer(digests, many=True).data)


class SmartSuggestionViewSet(viewsets.ModelViewSet):
    """View and manage smart suggestions"""
    permission_classes = [IsAuthenticated]
    serializer_class = SmartSuggestionSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['category', 'priority', 'is_implemented']
    ordering = ['-created_at']

    def get_queryset(self):
        user = self.request.user
        qs = SmartSuggestion.objects.filter(target_users=user)
        
        if user.role == 'manager':
            return qs.filter(
                Q(target_users=user) |
                Q(category__in=['sales', 'leads', 'operations'])
            ).distinct()
        
        return qs

    @action(detail=True, methods=['post'], url_path='implement')
    def implement(self, request, pk=None):
        """Implement a suggestion"""
        suggestion = self.get_object()
        
        if suggestion.is_implemented:
            return Response(
                {'detail': 'Suggestion already implemented'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        suggestion.implement(request.user)
        return Response({'detail': 'Suggestion marked as implemented'})

    @action(detail=True, methods=['post'], url_path='feedback')
    def feedback(self, request, pk=None):
        """Provide feedback on a suggestion"""
        suggestion = self.get_object()
        
        feedback_score = request.data.get('feedback_score')
        feedback_notes = request.data.get('feedback_notes', '')
        
        if feedback_score and 1 <= feedback_score <= 5:
            suggestion.feedback_score = feedback_score
            suggestion.feedback_notes = feedback_notes
            suggestion.save(update_fields=['feedback_score', 'feedback_notes'])
        
        return Response({'detail': 'Feedback recorded successfully'})

    @action(detail=False, methods=['get'], url_path='my-suggestions')
    def my_suggestions(self, request):
        """Get suggestions for current user"""
        user = request.user
        category_filter = request.query_params.get('category', None)
        priority_filter = request.query_params.get('priority', None)
        
        queryset = SmartSuggestion.objects.filter(target_users=user)
        
        if category_filter:
            queryset = queryset.filter(category=category_filter)
        
        if priority_filter:
            queryset = queryset.filter(priority=priority_filter)
        
        queryset = queryset.order_by('-priority', '-created_at')
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class AlertDashboardView(APIView):
    """Get comprehensive alert dashboard data"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        
        # Get recent alerts
        recent_alerts = Alert.objects.filter(
            recipients=user,
            triggered_at__gte=timezone.now() - timezone.timedelta(hours=24)
        ).select_related('alert_type').order_by('-triggered_at')
        
        # Get alert statistics
        stats = {
            'total_active': Alert.objects.filter(recipients=user, status='active').count(),
            'critical_count': Alert.objects.filter(
                recipients=user, 
                status='active', 
                severity='critical'
            ).count(),
            'high_count': Alert.objects.filter(
                recipients=user, 
                status='active', 
                severity='high'
            ).count(),
            'recent_count': recent_alerts.count(),
        }
        
        # Get top alert types
        top_alert_types = Alert.objects.filter(
            recipients=user,
            triggered_at__gte=timezone.now() - timezone.timedelta(days=7)
        ).values('alert_type__name').annotate(
            count=Count('id')
        ).order_by('-count')[:5]
        
        # Get smart suggestions
        suggestions = SmartSuggestion.objects.filter(
            target_users=user,
            is_implemented=False
        ).order_by('-priority', '-created_at')[:5]
        
        return Response({
            'stats': stats,
            'recent_alerts': AlertSerializer(recent_alerts[:10], many=True).data,
            'top_alert_types': list(top_alert_types),
            'suggestions': SmartSuggestionSerializer(suggestions, many=True).data,
        })
