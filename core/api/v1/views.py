from rest_framework.exceptions import PermissionDenied
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
from core.api.v1.permissions import (
    CanCreateTaskAsStaff,
    CanEditTaskAsStaff,
    IsAdmin,
    IsOwnTimeEntryOrPrivileged,
    ReadAllWriteAdminOnly,
    ReadOnlyForStaffOtherwiseManagerAdmin,
    get_staff_role,
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
    permission_classes = [ReadOnlyForStaffOtherwiseManagerAdmin]
    serializer_class = ContractSerializer
    filterset_class = ContractFilter

    # If you add Contract.name later, update this to ["name"].
    search_fields = ["id"]  # harmless placeholder; q won't be very useful without a text field

    ordering_fields = ["start_date", "end_date", "id"]

    def get_queryset(self):
        return Contract.objects.all().order_by("-id")


class StaffViewSet(ModelViewSet):
    permission_classes = [ReadAllWriteAdminOnly]
    serializer_class = StaffSerializer
    filterset_class = StaffFilter

    search_fields = ["email", "first_name", "last_name"]
    ordering_fields = ["id"]

    # Everyone can read; only admin can write
    def get_permissions(self):
        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            return [ReadOnlyForStaffOtherwiseManagerAdmin()]  # read allowed for all
        return [IsAdmin()]

    def get_queryset(self):
        return Staff.objects.all().order_by("-id")


class DeliverableViewSet(ModelViewSet):
    permission_classes = [ReadOnlyForStaffOtherwiseManagerAdmin]
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

    def perform_create(self, serializer):
        role = get_staff_role(self.request)

        if role == "staff":
            staff = self.request.user.staff
            assignee = serializer.validated_data.get("assignee", None)

            # allow null or self only
            if assignee is not None and assignee.id != staff.id:
                raise PermissionDenied("Staff can only create tasks for themselves or unassigned.")
        serializer.save()

    def perform_update(self, serializer):
        role = get_staff_role(self.request)

        if role == "staff":
            staff = self.request.user.staff
            # must already be assigned to them
            if self.get_object().assignee_id != staff.id:
                raise PermissionDenied("Staff can only update tasks assigned to themselves.")

            # prevent reassignment away from self
            if "assignee" in serializer.validated_data:
                assignee = serializer.validated_data.get("assignee", None)
                if assignee is not None and assignee.id != staff.id:
                    raise PermissionDenied("Staff cannot reassign tasks to other staff.")
        serializer.save()

    def get_permissions(self):
        role = get_staff_role(self.request)
        action = getattr(self, "action", None)

        # Staff: allow reads; writes are limited by special rules
        if role == "staff":
            if action in ("list", "retrieve"):
                return [ReadOnlyForStaffOtherwiseManagerAdmin()]
            if action == "create":
                return [CanCreateTaskAsStaff()]
            if action in ("update", "partial_update", "destroy"):
                # object-level enforcement for update/destroy
                return [CanEditTaskAsStaff()]
            # fallback
            return [ReadOnlyForStaffOtherwiseManagerAdmin()]

        # Managers/Admins: keep your existing policy (likely full CRUD)
        return [ReadOnlyForStaffOtherwiseManagerAdmin()]


class DeliverableAssignmentViewSet(ModelViewSet):
    permission_classes = [ReadOnlyForStaffOtherwiseManagerAdmin]
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

    def perform_create(self, serializer):
        role = get_staff_role(self.request)

        if role == "staff":
            staff = self.request.user.staff
            # Force staff to self regardless of payload
            serializer.save(staff=staff)
            return

        serializer.save()

    def perform_update(self, serializer):
        role = get_staff_role(self.request)

        if role == "staff":
            staff = self.request.user.staff
            obj = self.get_object()
            if obj.staff_id != staff.id:
                raise PermissionDenied("Staff can only edit their own time entries.")

            # Force staff to remain self even if payload tries to spoof
            serializer.save(staff=staff)
            return

        serializer.save()

    def perform_destroy(self, instance):
        role = get_staff_role(self.request)

        if role == "staff":
            staff = self.request.user.staff
            if instance.staff_id != staff.id:
                raise PermissionDenied("Staff can only delete their own time entries.")

        instance.delete()

    def get_permissions(self):
        role = get_staff_role(self.request)
        action = getattr(self, "action", None)

        if role == "staff":
            if action in ("list", "retrieve"):
                return [ReadOnlyForStaffOtherwiseManagerAdmin()]
            if action == "create":
                # Staff can create; perform_create forces staff=self
                from core.api.v1.permissions import CanCreateTimeEntryAsStaff

                return [CanCreateTimeEntryAsStaff()]
            if action in ("update", "partial_update", "destroy"):
                # object-level ownership check
                return [IsOwnTimeEntryOrPrivileged()]
            return [ReadOnlyForStaffOtherwiseManagerAdmin()]

        return [ReadOnlyForStaffOtherwiseManagerAdmin()]


class DeliverableStatusUpdateViewSet(ModelViewSet):
    permission_classes = [ReadOnlyForStaffOtherwiseManagerAdmin]
    serializer_class = DeliverableStatusUpdateSerializer
    filterset_class = DeliverableStatusUpdateFilter

    ordering_fields = ["period_end", "id"]

    def get_queryset(self):
        return (
            DeliverableStatusUpdate.objects.all()
            .select_related("deliverable", "deliverable__contract", "created_by")
            .order_by("-id")
        )
