from rest_framework.viewsets import ModelViewSet

from core.api.v1.filters import (
    ContractFilter,
    DeliverableAssignmentFilter,
    DeliverableFilter,
    DeliverableStatusUpdateFilter,
    DeliverableTimeEntryFilter,
    StaffFilter,
    TaskFilter,
)
from core.api.v1.serializers import (
    ContractSerializer,
    DeliverableAssignmentSerializer,
    DeliverableSerializer,
    DeliverableStatusUpdateSerializer,
    DeliverableTimeEntrySerializer,
    StaffSerializer,
    TaskSerializer,
)
from core.models import (
    Contract,
    Deliverable,
    DeliverableAssignment,
    DeliverableStatusUpdate,
    DeliverableTimeEntry,
    Staff,
    Task,
)


class ContractViewSet(ModelViewSet):
    serializer_class = ContractSerializer
    filterset_class = ContractFilter

    # If you add Contract.name later, update this to ["name"].
    search_fields = ["id"]  # harmless placeholder; q won't be very useful without a text field

    ordering_fields = ["start_date", "end_date", "id"]

    def get_queryset(self):
        return Contract.objects.all().order_by("-id")


class StaffViewSet(ModelViewSet):
    serializer_class = StaffSerializer
    filterset_class = StaffFilter

    search_fields = ["email", "first_name", "last_name"]
    ordering_fields = ["id"]

    def get_queryset(self):
        return Staff.objects.all().order_by("-id")


class DeliverableViewSet(ModelViewSet):
    serializer_class = DeliverableSerializer
    filterset_class = DeliverableFilter

    # Canonical search uses ?q=... via CanonicalSearchFilter
    search_fields = ["name"]

    # Canonical ordering uses ?order_by=<field>&order_dir=asc|desc
    ordering_fields = ["start_date", "due_date", "id"]

    def get_queryset(self):
        # select_related prevents N+1 when serializing contract id etc.
        # prefetch_related prevents N+1 for assignments when filters/search expand later.
        return Deliverable.objects.all().select_related("contract").prefetch_related("assignments").order_by("-id")


class TaskViewSet(ModelViewSet):
    serializer_class = TaskSerializer
    filterset_class = TaskFilter

    # Canonical search: ?q=...
    search_fields = ["title"]

    # Canonical ordering: ?order_by=<field>&order_dir=...
    # If you later add Task.due_date, change ordering_fields to ["due_date", "id"] and adjust filters.
    ordering_fields = ["id"]

    def get_queryset(self):
        return Task.objects.all().select_related("deliverable", "deliverable__contract", "assignee").order_by("-id")


class DeliverableAssignmentViewSet(ModelViewSet):
    serializer_class = DeliverableAssignmentSerializer
    filterset_class = DeliverableAssignmentFilter

    ordering_fields = ["id"]

    def get_queryset(self):
        return (
            DeliverableAssignment.objects.all()
            .select_related("deliverable", "deliverable__contract", "staff")
            .order_by("-id")
        )


class DeliverableTimeEntryViewSet(ModelViewSet):
    serializer_class = DeliverableTimeEntrySerializer
    filterset_class = DeliverableTimeEntryFilter

    ordering_fields = ["entry_date", "id"]

    def get_queryset(self):
        return (
            DeliverableTimeEntry.objects.all()
            .select_related("deliverable", "deliverable__contract", "staff")
            .order_by("-id")
        )


class DeliverableStatusUpdateViewSet(ModelViewSet):
    serializer_class = DeliverableStatusUpdateSerializer
    filterset_class = DeliverableStatusUpdateFilter

    ordering_fields = ["period_end", "id"]

    def get_queryset(self):
        return (
            DeliverableStatusUpdate.objects.all()
            .select_related("deliverable", "deliverable__contract", "created_by")
            .order_by("-id")
        )
