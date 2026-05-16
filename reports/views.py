from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend

from core.permissions import IsManager
from .models import Report, DailyReport
from .serializers import ReportSerializer, DailyReportSerializer


class ReportListView(generics.ListAPIView):
    """GET /api/v1/reports/?branch_id=&period=&from=&to="""
    permission_classes = [IsAuthenticated, IsManager]
    serializer_class   = ReportSerializer
    filter_backends    = [DjangoFilterBackend]
    filterset_fields   = ['branch', 'period']
    pagination_class   = None

    def get_queryset(self):
        user = self.request.user
        qs   = Report.objects.select_related('branch').all()
        if user.role != 'owner':
            qs = qs.filter(branch=user.branch)

        from_date = self.request.query_params.get('from')
        to_date   = self.request.query_params.get('to')
        if from_date:
            qs = qs.filter(date__gte=from_date)
        if to_date:
            qs = qs.filter(date__lte=to_date)
        return qs


class BranchSnapshotView(APIView):
    """GET /api/v1/reports/snapshot/?branch_id=&period=daily"""
    permission_classes = [IsAuthenticated, IsManager]

    def get(self, request):
        from branches.models import Branch
        user      = request.user
        period    = request.query_params.get('period', 'daily')
        branch_id = request.query_params.get('branch_id')

        if branch_id:
            branch = Branch.objects.filter(pk=branch_id).first()
            if not branch:
                return Response({'detail': 'Branch not found.'}, status=status.HTTP_404_NOT_FOUND)
        else:
            branch = user.branch

        # If owner and no specific branch, get a summary of all branches
        if not branch and user.role == 'owner':
            from django.db.models import Sum, Count
            from .models import Report
            today = timezone.localdate()
            # Try to get existing aggregate or compute on the fly
            reports = Report.objects.filter(date=today, period='daily')
            if not reports.exists():
                return Response({'detail': 'No reports found for today.'}, status=404)
            
            # Simple aggregation for the owner view
            total_sales_amount = 0
            total_sales_count = 0
            total_leads = 0
            total_calls = 0
            
            for r in reports:
                d = r.data or {}
                sales_data = d.get('sales') or {}
                leads_data = d.get('leads') or {}
                calls_data = d.get('calls') or {}
                
                total_sales_amount += sales_data.get('revenue', 0) or d.get('sales_amount', 0) or 0
                total_sales_count += sales_data.get('count', 0) or d.get('sales_count', 0) or 0
                total_leads += leads_data.get('total', 0) or 0
                total_calls += calls_data.get('total', 0) or 0

            return Response({
                "data": {
                    "leads": total_leads,
                    "calls": total_calls,
                    "sales_count": total_sales_count,
                    "sales_amount": total_sales_amount
                }
            })

        if not branch:
            return Response({'detail': 'Branch not found.'}, status=status.HTTP_404_NOT_FOUND)

        if user.role != 'owner' and branch != user.branch:
            return Response({'detail': 'Access denied.'}, status=status.HTTP_403_FORBIDDEN)

        report = Report.objects.filter(branch=branch, period=period).order_by('-date').first()
        if not report:
            # Instead of 404, return a placeholder with 0s to prevent frontend crashes
            return Response({
                "id": None,
                "branch_name": branch.name,
                "date": str(timezone.localdate()),
                "data": {
                    "leads": {"total": 0, "converted": 0, "conversion_rate": 0},
                    "calls": {"total": 0, "connected": 0},
                    "sales": {"count": 0, "revenue": 0, "weight": 0},
                    "attendance": {"rate": 0, "present": 0, "total_staff": 0},
                    "field_visits": {"total": 0},
                    "followups": {"scheduled": 0, "completed": 0}
                }
            })

        return Response(ReportSerializer(report).data)


class TriggerEODReportView(APIView):
    """POST /api/v1/reports/eod/trigger/"""
    permission_classes = [IsAuthenticated, IsManager]

    def post(self, request):
        user   = request.user
        branch = user.branch
        period = request.data.get('period', 'daily')
        start_date = request.data.get('start_date')
        end_date = request.data.get('end_date')

        if not branch and user.role != 'owner':
            return Response({'detail': 'No branch assigned.'}, status=400)

        try:
            from .tasks import generate_branch_snapshot
            import logging
            task_logger = logging.getLogger('reports')
            
            if user.role == 'owner':
                from branches.models import Branch
                target_branch_id = request.data.get('branch_id')
                if target_branch_id:
                    branches = Branch.objects.filter(id=target_branch_id)
                else:
                    branches = Branch.objects.filter(is_active=True)
                
                success_branches = []
                failed_branches = []
                
                for b in branches:
                    try:
                        # Attempt async, fallback to sync
                        try:
                            generate_branch_snapshot.delay(b.id, period, start_date=start_date, end_date=end_date)
                        except Exception:
                            generate_branch_snapshot(b.id, period, start_date=start_date, end_date=end_date)
                        success_branches.append(b.name)
                    except Exception as e:
                        task_logger.error(f"Manual trigger failed for {b.name}: {e}")
                        failed_branches.append(b.name)
                
                return Response({
                    'status': 'completed' if not failed_branches else 'partial', 
                    'branches': success_branches,
                    'failed': failed_branches
                })
            else:
                try:
                    try:
                        generate_branch_snapshot.delay(branch.id, period, start_date=start_date, end_date=end_date)
                    except Exception:
                        generate_branch_snapshot(branch.id, period, start_date=start_date, end_date=end_date)
                    return Response({'status': 'completed', 'branch': branch.name})
                except Exception as e:
                    task_logger.error(f"Manual trigger failed for {branch.name}: {e}")
                    return Response({'status': 'error', 'detail': str(e)}, status=500)
        except Exception as e:
            return Response({'status': 'error', 'detail': str(e)}, status=500)


class DailyReportListView(generics.ListAPIView):
    """GET /api/v1/reports/daily/ — legacy daily reports."""
    permission_classes = [IsAuthenticated, IsManager]
    serializer_class   = DailyReportSerializer

    def get_queryset(self):
        user = self.request.user
        qs   = DailyReport.objects.select_related('branch').all()
        if user.role != 'owner':
            qs = qs.filter(branch=user.branch)
        return qs
