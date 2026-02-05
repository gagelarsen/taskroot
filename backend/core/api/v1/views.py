from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
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


@extend_schema(tags=["contracts"])
@extend_schema_view(
    list=extend_schema(
        summary="List contracts",
        description="List all contracts with optional filtering, ordering, and pagination.",
        parameters=[
            OpenApiParameter(
                "start_date_from", OpenApiTypes.DATE, description="Filter contracts starting on or after this date"
            ),
            OpenApiParameter(
                "start_date_to", OpenApiTypes.DATE, description="Filter contracts starting on or before this date"
            ),
            OpenApiParameter(
                "end_date_from", OpenApiTypes.DATE, description="Filter contracts ending on or after this date"
            ),
            OpenApiParameter(
                "end_date_to", OpenApiTypes.DATE, description="Filter contracts ending on or before this date"
            ),
            OpenApiParameter("over_budget", OpenApiTypes.BOOL, description="Filter contracts over budget (true/false)"),
            OpenApiParameter(
                "over_expected", OpenApiTypes.BOOL, description="Filter contracts over expected hours (true/false)"
            ),
            OpenApiParameter(
                "order_by",
                OpenApiTypes.STR,
                description="Field to order by (start_date, end_date, id)",
                enum=["start_date", "end_date", "id"],
            ),
            OpenApiParameter("order_dir", OpenApiTypes.STR, description="Order direction", enum=["asc", "desc"]),
        ],
    ),
    create=extend_schema(
        summary="Create a contract",
        description="Create a new contract. Requires manager or admin role.",
        examples=[
            OpenApiExample(
                "Create contract",
                value={
                    "start_date": "2024-01-01",
                    "end_date": "2024-12-31",
                    "budget_hours_total": 1000.0,
                    "status": "active",
                },
                request_only=True,
            ),
        ],
    ),
    retrieve=extend_schema(
        summary="Get a contract", description="Retrieve a single contract by ID with all rollup metrics."
    ),
    update=extend_schema(summary="Update a contract", description="Update a contract. Requires manager or admin role."),
    partial_update=extend_schema(
        summary="Partially update a contract",
        description="Partially update a contract. Requires manager or admin role.",
    ),
    destroy=extend_schema(
        summary="Delete a contract", description="Delete a contract. Requires manager or admin role."
    ),
)
class ContractViewSet(ModelViewSet):
    permission_classes = [ReadOnlyForStaffOtherwiseManagerAdmin]
    serializer_class = ContractSerializer
    filterset_class = ContractFilter

    search_fields = ["name", "client_name"]

    ordering_fields = ["start_date", "end_date", "id", "name"]

    def get_queryset(self):
        return Contract.objects.all().order_by("-id")


@extend_schema(tags=["staff"])
@extend_schema_view(
    list=extend_schema(
        summary="List staff members",
        description="List all staff members with optional search, ordering, and pagination.",
        parameters=[
            OpenApiParameter("q", OpenApiTypes.STR, description="Search by email, first name, or last name"),
            OpenApiParameter("order_by", OpenApiTypes.STR, description="Field to order by", enum=["id"]),
            OpenApiParameter("order_dir", OpenApiTypes.STR, description="Order direction", enum=["asc", "desc"]),
        ],
    ),
    create=extend_schema(
        summary="Create a staff member",
        description="Create a new staff member. Requires admin role.",
        examples=[
            OpenApiExample(
                "Create staff",
                value={
                    "email": "john.doe@example.com",
                    "first_name": "John",
                    "last_name": "Doe",
                    "status": "active",
                    "role": "staff",
                },
                request_only=True,
            ),
        ],
    ),
    retrieve=extend_schema(summary="Get a staff member", description="Retrieve a single staff member by ID."),
    update=extend_schema(summary="Update a staff member", description="Update a staff member. Requires admin role."),
    partial_update=extend_schema(
        summary="Partially update a staff member", description="Partially update a staff member. Requires admin role."
    ),
    destroy=extend_schema(summary="Delete a staff member", description="Delete a staff member. Requires admin role."),
)
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


@extend_schema(tags=["deliverables"])
@extend_schema_view(
    list=extend_schema(
        summary="List deliverables",
        description="List all deliverables with rollup metrics, optional filtering, ordering, and pagination.",
        parameters=[
            OpenApiParameter("contract_id", OpenApiTypes.INT, description="Filter by contract ID"),
            OpenApiParameter(
                "staff_id", OpenApiTypes.INT, description="Filter deliverables assigned to this staff member"
            ),
            OpenApiParameter(
                "lead_only",
                OpenApiTypes.BOOL,
                description="Filter deliverables where staff is lead (requires staff_id)",
            ),
            OpenApiParameter(
                "start_date_from", OpenApiTypes.DATE, description="Filter deliverables starting on or after this date"
            ),
            OpenApiParameter(
                "start_date_to", OpenApiTypes.DATE, description="Filter deliverables starting on or before this date"
            ),
            OpenApiParameter(
                "due_date_from", OpenApiTypes.DATE, description="Filter deliverables due on or after this date"
            ),
            OpenApiParameter(
                "due_date_to", OpenApiTypes.DATE, description="Filter deliverables due on or before this date"
            ),
            OpenApiParameter(
                "over_expected", OpenApiTypes.BOOL, description="Filter deliverables over expected hours (true/false)"
            ),
            OpenApiParameter(
                "missing_lead",
                OpenApiTypes.BOOL,
                description="Filter deliverables missing a lead assignment (true/false)",
            ),
            OpenApiParameter(
                "missing_estimate", OpenApiTypes.BOOL, description="Filter deliverables missing estimates (true/false)"
            ),
            OpenApiParameter("q", OpenApiTypes.STR, description="Search by deliverable name"),
            OpenApiParameter(
                "order_by", OpenApiTypes.STR, description="Field to order by", enum=["start_date", "due_date", "id"]
            ),
            OpenApiParameter("order_dir", OpenApiTypes.STR, description="Order direction", enum=["asc", "desc"]),
        ],
    ),
    create=extend_schema(
        summary="Create a deliverable",
        description="Create a new deliverable. Requires manager or admin role.",
        examples=[
            OpenApiExample(
                "Create deliverable",
                value={
                    "contract": 1,
                    "name": "API Development",
                    "start_date": "2024-01-01",
                    "due_date": "2024-01-31",
                    "status": "in_progress",
                },
                request_only=True,
            ),
        ],
    ),
    retrieve=extend_schema(
        summary="Get a deliverable", description="Retrieve a single deliverable by ID with all rollup metrics."
    ),
    update=extend_schema(
        summary="Update a deliverable", description="Update a deliverable. Requires manager or admin role."
    ),
    partial_update=extend_schema(
        summary="Partially update a deliverable",
        description="Partially update a deliverable. Requires manager or admin role.",
    ),
    destroy=extend_schema(
        summary="Delete a deliverable", description="Delete a deliverable. Requires manager or admin role."
    ),
)
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


@extend_schema(tags=["tasks"])
@extend_schema_view(
    list=extend_schema(
        summary="List tasks",
        description="List all tasks with optional filtering, ordering, and pagination.",
        parameters=[
            OpenApiParameter("contract_id", OpenApiTypes.INT, description="Filter by contract ID"),
            OpenApiParameter("deliverable_id", OpenApiTypes.INT, description="Filter by deliverable ID"),
            OpenApiParameter("assignee_id", OpenApiTypes.INT, description="Filter by assignee staff ID"),
            OpenApiParameter("unassigned", OpenApiTypes.BOOL, description="Filter unassigned tasks (true/false)"),
            OpenApiParameter("q", OpenApiTypes.STR, description="Search by task title"),
            OpenApiParameter("order_by", OpenApiTypes.STR, description="Field to order by", enum=["id"]),
            OpenApiParameter("order_dir", OpenApiTypes.STR, description="Order direction", enum=["asc", "desc"]),
        ],
    ),
    create=extend_schema(
        summary="Create a task",
        description="Create a new task. Staff can only create tasks assigned to themselves or unassigned.",
        examples=[
            OpenApiExample(
                "Create unassigned task",
                value={
                    "deliverable": 1,
                    "title": "Review API documentation",
                    "assignee": None,
                },
                request_only=True,
            ),
            OpenApiExample(
                "Create assigned task",
                value={
                    "deliverable": 1,
                    "title": "Implement authentication",
                    "assignee": 2,
                },
                request_only=True,
            ),
        ],
    ),
    retrieve=extend_schema(summary="Get a task", description="Retrieve a single task by ID."),
    update=extend_schema(
        summary="Update a task", description="Update a task. Staff can only update tasks assigned to themselves."
    ),
    partial_update=extend_schema(
        summary="Partially update a task",
        description="Partially update a task. Staff can only update tasks assigned to themselves.",
    ),
    destroy=extend_schema(
        summary="Delete a task", description="Delete a task. Staff can only delete tasks assigned to themselves."
    ),
)
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
        # Permission check is handled by CanCreateTaskAsStaff
        # No additional logic needed here
        serializer.save()

    def perform_update(self, serializer):
        role = get_staff_role(self.request)

        if role == "staff":
            # CanEditTaskAsStaff already checked that task is assigned to them
            # But we need to prevent reassignment away from self
            if "assignee" in serializer.validated_data:
                staff = self.request.user.staff
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
            elif action == "create":
                return [CanCreateTaskAsStaff()]
            elif action in ("update", "partial_update", "destroy"):
                # object-level enforcement for update/destroy
                return [CanEditTaskAsStaff()]

        # Managers/Admins and all other cases
        return [ReadOnlyForStaffOtherwiseManagerAdmin()]


@extend_schema(tags=["deliverable-assignments"])
@extend_schema_view(
    list=extend_schema(
        summary="List deliverable assignments",
        description="List all deliverable assignments with optional filtering, ordering, and pagination.",
        parameters=[
            OpenApiParameter("deliverable_id", OpenApiTypes.INT, description="Filter by deliverable ID"),
            OpenApiParameter("staff_id", OpenApiTypes.INT, description="Filter by staff ID"),
            OpenApiParameter("is_lead", OpenApiTypes.BOOL, description="Filter by lead assignments (true/false)"),
            OpenApiParameter("order_by", OpenApiTypes.STR, description="Field to order by", enum=["id"]),
            OpenApiParameter("order_dir", OpenApiTypes.STR, description="Order direction", enum=["asc", "desc"]),
        ],
    ),
    create=extend_schema(
        summary="Create a deliverable assignment",
        description="Assign a staff member to a deliverable. Requires manager or admin role.",
        examples=[
            OpenApiExample(
                "Create assignment with lead",
                value={
                    "deliverable": 1,
                    "staff": 2,
                    "expected_hours": 40.0,
                    "is_lead": True,
                },
                request_only=True,
            ),
        ],
    ),
    retrieve=extend_schema(
        summary="Get a deliverable assignment", description="Retrieve a single deliverable assignment by ID."
    ),
    update=extend_schema(
        summary="Update a deliverable assignment",
        description="Update a deliverable assignment. Requires manager or admin role.",
    ),
    partial_update=extend_schema(
        summary="Partially update a deliverable assignment",
        description="Partially update a deliverable assignment. Requires manager or admin role.",
    ),
    destroy=extend_schema(
        summary="Delete a deliverable assignment",
        description="Delete a deliverable assignment. Requires manager or admin role.",
    ),
)
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


@extend_schema(tags=["deliverable-time-entries"])
@extend_schema_view(
    list=extend_schema(
        summary="List deliverable time entries",
        description="List all time entries with optional filtering, ordering, and pagination.",
        parameters=[
            OpenApiParameter("deliverable_id", OpenApiTypes.INT, description="Filter by deliverable ID"),
            OpenApiParameter("staff_id", OpenApiTypes.INT, description="Filter by staff ID"),
            OpenApiParameter("entry_date_from", OpenApiTypes.DATE, description="Filter entries on or after this date"),
            OpenApiParameter("entry_date_to", OpenApiTypes.DATE, description="Filter entries on or before this date"),
            OpenApiParameter("order_by", OpenApiTypes.STR, description="Field to order by", enum=["entry_date", "id"]),
            OpenApiParameter("order_dir", OpenApiTypes.STR, description="Order direction", enum=["asc", "desc"]),
        ],
    ),
    create=extend_schema(
        summary="Create a time entry",
        description=(
            "Create a new time entry. Staff can only create entries for themselves (staff field is auto-set). "
            "\n\n**Idempotency**: If external_source and external_id are provided, the API will check for an existing "
            "entry with the same (external_source, external_id). If found, the existing entry is returned (200 OK) "
            "instead of creating a duplicate. This ensures safe retries for integration systems."
        ),
        examples=[
            OpenApiExample(
                "Create time entry",
                value={
                    "deliverable": 1,
                    "entry_date": "2024-01-15",
                    "hours": 8.0,
                },
                request_only=True,
            ),
            OpenApiExample(
                "Create time entry with idempotency key",
                value={
                    "deliverable": 1,
                    "staff": 2,
                    "entry_date": "2024-01-15",
                    "hours": 8.0,
                    "note": "Development work",
                    "external_source": "jira",
                    "external_id": "PROJ-123",
                },
                request_only=True,
            ),
        ],
    ),
    retrieve=extend_schema(summary="Get a time entry", description="Retrieve a single time entry by ID."),
    update=extend_schema(
        summary="Update a time entry", description="Update a time entry. Staff can only update their own entries."
    ),
    partial_update=extend_schema(
        summary="Partially update a time entry",
        description="Partially update a time entry. Staff can only update their own entries.",
    ),
    destroy=extend_schema(
        summary="Delete a time entry", description="Delete a time entry. Staff can only delete their own entries."
    ),
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

    def create(self, request, *args, **kwargs):
        """
        Create a new time entry with idempotency support.

        If external_source and external_id are provided, check if an entry
        with the same (external_source, external_id) already exists.
        If found, return the existing entry (200 OK) instead of creating a duplicate.
        """
        # Check for idempotency key
        external_source = request.data.get("external_source", "")
        external_id = request.data.get("external_id", "")

        if external_source and external_id:
            # Try to find existing entry with same idempotency key
            existing = DeliverableTimeEntry.objects.filter(
                external_source=external_source, external_id=external_id
            ).first()

            if existing:
                # Return existing entry (idempotent behavior)
                serializer = self.get_serializer(existing)
                return Response(serializer.data, status=status.HTTP_200_OK)

        # No existing entry found, proceed with normal creation
        return super().create(request, *args, **kwargs)

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
            # IsOwnTimeEntryOrPrivileged already checked ownership
            # Force staff to remain self even if payload tries to spoof
            staff = self.request.user.staff
            serializer.save(staff=staff)
            return

        serializer.save()

    def perform_destroy(self, instance):
        # IsOwnTimeEntryOrPrivileged already checked ownership
        # No additional logic needed here
        instance.delete()

    def get_permissions(self):
        role = get_staff_role(self.request)
        action = getattr(self, "action", None)

        if role == "staff":
            if action in ("list", "retrieve"):
                return [ReadOnlyForStaffOtherwiseManagerAdmin()]
            elif action == "create":
                # Staff can create; perform_create forces staff=self
                from core.api.v1.permissions import CanCreateTimeEntryAsStaff

                return [CanCreateTimeEntryAsStaff()]
            elif action in ("update", "partial_update", "destroy"):
                # object-level ownership check
                return [IsOwnTimeEntryOrPrivileged()]

        # Managers/Admins and all other cases
        return [ReadOnlyForStaffOtherwiseManagerAdmin()]


@extend_schema(tags=["deliverable-status-updates"])
@extend_schema_view(
    list=extend_schema(
        summary="List deliverable status updates",
        description="List all status updates with optional filtering, ordering, and pagination.",
        parameters=[
            OpenApiParameter("deliverable_id", OpenApiTypes.INT, description="Filter by deliverable ID"),
            OpenApiParameter(
                "period_end_from",
                OpenApiTypes.DATE,
                description="Filter updates with period ending on or after this date",
            ),
            OpenApiParameter(
                "period_end_to",
                OpenApiTypes.DATE,
                description="Filter updates with period ending on or before this date",
            ),
            OpenApiParameter(
                "status",
                OpenApiTypes.STR,
                description="Filter by status",
                enum=["on_track", "at_risk", "blocked", "complete"],
            ),
            OpenApiParameter("order_by", OpenApiTypes.STR, description="Field to order by", enum=["period_end", "id"]),
            OpenApiParameter("order_dir", OpenApiTypes.STR, description="Order direction", enum=["asc", "desc"]),
        ],
    ),
    create=extend_schema(
        summary="Create a status update",
        description="Create a new status update for a deliverable. Requires manager or admin role.",
        examples=[
            OpenApiExample(
                "Create status update",
                value={
                    "deliverable": 1,
                    "period_end": "2024-01-31",
                    "status": "on_track",
                    "summary": "All tasks completed on schedule.",
                },
                request_only=True,
            ),
        ],
    ),
    retrieve=extend_schema(summary="Get a status update", description="Retrieve a single status update by ID."),
    update=extend_schema(
        summary="Update a status update", description="Update a status update. Requires manager or admin role."
    ),
    partial_update=extend_schema(
        summary="Partially update a status update",
        description="Partially update a status update. Requires manager or admin role.",
    ),
    destroy=extend_schema(
        summary="Delete a status update", description="Delete a status update. Requires manager or admin role."
    ),
)
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
