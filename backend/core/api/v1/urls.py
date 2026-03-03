from django.urls import path
from rest_framework.routers import DefaultRouter

from core.api.v1 import bulk_import, export_views, report_views, views

router = DefaultRouter()
router.register(r"staff", views.StaffViewSet, basename="staff")
router.register(r"charge-codes", views.ChargeCodeViewSet, basename="charge-code")
router.register(r"contracts", views.ContractViewSet, basename="contract")
router.register(r"deliverables", views.DeliverableViewSet, basename="deliverable")
router.register(r"tasks", views.TaskViewSet, basename="task")
router.register(r"deliverable-assignments", views.DeliverableAssignmentViewSet, basename="deliverable-assignment")
router.register(r"deliverable-time-entries", views.DeliverableTimeEntryViewSet, basename="deliverable-time-entry")
router.register(r"contract-invoice-updates", views.ContractInvoiceUpdateViewSet, basename="contract-invoice-update")
router.register(
    r"deliverable-status-updates", views.DeliverableStatusUpdateViewSet, basename="deliverable-status-update"
)
router.register(r"initiatives", views.InitiativeViewSet, basename="initiative")
router.register(r"initiative-weekly-updates", views.InitiativeWeeklyUpdateViewSet, basename="initiative-weekly-update")
router.register(r"future-work", views.FutureWorkViewSet, basename="future-work")

# Reporting endpoints
router.register(r"reports/contracts", report_views.ContractReportViewSet, basename="report-contract")
router.register(r"reports/deliverables", report_views.DeliverableReportViewSet, basename="report-deliverable")
router.register(r"reports/staff", report_views.StaffReportViewSet, basename="report-staff")
router.register(r"reports/charge-codes", report_views.ChargeCodeReportViewSet, basename="report-charge-code")

# Export endpoints (non-ViewSet, so we add them manually)
export_patterns = [
    path("exports/time-entries.csv", export_views.TimeEntriesCSVExport.as_view(), name="export-time-entries"),
    path("exports/contract-burn.csv", export_views.ContractBurnCSVExport.as_view(), name="export-contract-burn"),
    path("exports/contracts.csv", export_views.ContractsCSVExport.as_view(), name="export-contracts"),
    path("exports/deliverables.csv", export_views.DeliverablesCSVExport.as_view(), name="export-deliverables"),
    path("exports/tasks.csv", export_views.TasksCSVExport.as_view(), name="export-tasks"),
    path("exports/initiatives.csv", export_views.InitiativesCSVExport.as_view(), name="export-initiatives"),
    path(
        "exports/initiative-weekly-updates.csv",
        export_views.InitiativeWeeklyUpdatesCSVExport.as_view(),
        name="export-initiative-weekly-updates",
    ),
]

# Bulk import endpoints
import_patterns = [
    path("bulk-import/", bulk_import.bulk_import_view, name="bulk-import"),
    path("bulk-import/time-entries/", bulk_import.bulk_import_time_entries_view, name="bulk-import-time-entries"),
    path("bulk-import/invoices/", bulk_import.bulk_import_invoice_updates_view, name="bulk-import-invoices"),
]

urlpatterns = router.urls + export_patterns + import_patterns
