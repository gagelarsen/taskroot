from django.urls import path
from rest_framework.routers import DefaultRouter

from core.api.v1 import export_views, report_views, views

router = DefaultRouter()
router.register(r"staff", views.StaffViewSet, basename="staff")
router.register(r"contracts", views.ContractViewSet, basename="contract")
router.register(r"deliverables", views.DeliverableViewSet, basename="deliverable")
router.register(r"tasks", views.TaskViewSet, basename="task")
router.register(r"deliverable-assignments", views.DeliverableAssignmentViewSet, basename="deliverable-assignment")
router.register(r"deliverable-time-entries", views.DeliverableTimeEntryViewSet, basename="deliverable-time-entry")
router.register(
    r"deliverable-status-updates", views.DeliverableStatusUpdateViewSet, basename="deliverable-status-update"
)

# Reporting endpoints
router.register(r"reports/contracts", report_views.ContractReportViewSet, basename="report-contract")
router.register(r"reports/deliverables", report_views.DeliverableReportViewSet, basename="report-deliverable")
router.register(r"reports/staff", report_views.StaffReportViewSet, basename="report-staff")

# Export endpoints (non-ViewSet, so we add them manually)
export_patterns = [
    path("exports/time-entries.csv", export_views.TimeEntriesCSVExport.as_view(), name="export-time-entries"),
    path("exports/contract-burn.csv", export_views.ContractBurnCSVExport.as_view(), name="export-contract-burn"),
]

urlpatterns = router.urls + export_patterns
