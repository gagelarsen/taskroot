from rest_framework.routers import DefaultRouter

from core.api.v1 import views

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

urlpatterns = router.urls
