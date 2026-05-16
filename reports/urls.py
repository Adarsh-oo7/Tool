from django.urls import path
from .views import ReportListView, BranchSnapshotView, TriggerEODReportView, DailyReportListView

urlpatterns = [
    path('',              ReportListView.as_view(),       name='report-list'),
    path('daily/',        DailyReportListView.as_view(),  name='dailyreport-list'),
    path('snapshot/',     BranchSnapshotView.as_view(),   name='report-snapshot'),
    path('eod/trigger/',  TriggerEODReportView.as_view(), name='report-eod-trigger'),
]
