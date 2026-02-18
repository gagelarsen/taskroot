from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from core.models import (
    Contract,
    Deliverable,
    DeliverableAssignment,
    DeliverableStatusUpdate,
    DeliverableTimeEntry,
    Initiative,
    InitiativeWeeklyUpdate,
    Staff,
    Task,
)


class StaffSerializer(serializers.ModelSerializer):
    class Meta:
        model = Staff
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "status",
            "role",
            "expected_hours_per_week",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class ContractSerializer(serializers.ModelSerializer):
    contract_type_display = serializers.CharField(source="get_contract_type_display", read_only=True)
    tags = serializers.ListField(child=serializers.CharField(max_length=50, allow_blank=True), required=False)

    # Computed rollup fields (read-only)
    assigned_budget_hours = serializers.SerializerMethodField()
    spent_hours = serializers.SerializerMethodField()
    planned_weeks = serializers.SerializerMethodField()
    elapsed_weeks = serializers.SerializerMethodField()
    assigned_budget_hours_per_week = serializers.SerializerMethodField()
    spent_hours_per_week = serializers.SerializerMethodField()
    remaining_budget_hours = serializers.SerializerMethodField()
    unspent_budget_hours = serializers.SerializerMethodField()
    estimated_burn_rate = serializers.SerializerMethodField()
    actual_burn_rate = serializers.SerializerMethodField()
    estimated_percent_complete = serializers.SerializerMethodField()

    # Health flags (read-only)
    is_over_budget = serializers.SerializerMethodField()
    is_overassigned = serializers.SerializerMethodField()

    class Meta:
        model = Contract
        fields = [
            "id",
            "name",
            "client_name",
            "start_date",
            "end_date",
            "budget_hours",
            "contract_type",
            "contract_type_display",
            "status",
            "tags",
            "created_at",
            "updated_at",
            # Computed fields
            "assigned_budget_hours",
            "spent_hours",
            "planned_weeks",
            "elapsed_weeks",
            "assigned_budget_hours_per_week",
            "spent_hours_per_week",
            "remaining_budget_hours",
            "unspent_budget_hours",
            "estimated_burn_rate",
            "actual_burn_rate",
            "estimated_percent_complete",
            "is_over_budget",
            "is_overassigned",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
            "contract_type_display",
            "assigned_budget_hours",
            "spent_hours",
            "planned_weeks",
            "elapsed_weeks",
            "assigned_budget_hours_per_week",
            "spent_hours_per_week",
            "remaining_budget_hours",
            "unspent_budget_hours",
            "estimated_burn_rate",
            "actual_burn_rate",
            "estimated_percent_complete",
            "is_over_budget",
            "is_overassigned",
        ]

    @extend_schema_field(serializers.FloatField(read_only=True, help_text="Sum of budget hours from all deliverables"))
    def get_assigned_budget_hours(self, obj):
        return obj.get_assigned_budget_hours()

    @extend_schema_field(serializers.FloatField(read_only=True, help_text="Sum of spent hours from all deliverables"))
    def get_spent_hours(self, obj):
        return obj.get_spent_hours()

    @extend_schema_field(
        serializers.IntegerField(read_only=True, help_text="Number of planned weeks for this contract")
    )
    def get_planned_weeks(self, obj):
        return obj.get_planned_weeks()

    @extend_schema_field(
        serializers.IntegerField(read_only=True, help_text="Number of elapsed weeks from start to today")
    )
    def get_elapsed_weeks(self, obj):
        return obj.get_elapsed_weeks()

    @extend_schema_field(
        serializers.FloatField(read_only=True, help_text="Sum of assigned budget hours per week from all assignments")
    )
    def get_assigned_budget_hours_per_week(self, obj):
        return obj.get_assigned_budget_hours_per_week()

    @extend_schema_field(serializers.FloatField(read_only=True, help_text="Spent hours divided by elapsed weeks"))
    def get_spent_hours_per_week(self, obj):
        return obj.get_spent_hours_per_week()

    @extend_schema_field(
        serializers.FloatField(read_only=True, help_text="Remaining budget hours (budget - assigned budget hours)")
    )
    def get_remaining_budget_hours(self, obj):
        return obj.get_remaining_budget_hours()

    @extend_schema_field(
        serializers.FloatField(read_only=True, help_text="Unspent budget hours (budget - spent hours)")
    )
    def get_unspent_budget_hours(self, obj):
        return obj.get_unspent_budget_hours()

    @extend_schema_field(
        serializers.FloatField(
            read_only=True,
            help_text="Estimated burn rate (hours per week) based on staff assignments across all deliverables",
        )
    )
    def get_estimated_burn_rate(self, obj):
        return obj.get_estimated_burn_rate()

    @extend_schema_field(
        serializers.FloatField(
            read_only=True,
            help_text="Actual burn rate (hours per week) based on recent time entries (last 4 weeks)",
        )
    )
    def get_actual_burn_rate(self, obj):
        return obj.get_actual_burn_rate(weeks=4)

    @extend_schema_field(
        serializers.FloatField(
            read_only=True,
            help_text="Estimated completion percentage (0-100) rolled up from tasks across deliverables",
        )
    )
    def get_estimated_percent_complete(self, obj):
        return obj.get_estimated_percent_complete()

    @extend_schema_field(serializers.BooleanField(read_only=True, help_text="True if spent hours exceed budget"))
    def get_is_over_budget(self, obj):
        return obj.is_over_budget()

    @extend_schema_field(
        serializers.BooleanField(read_only=True, help_text="True if assigned budget hours exceed contract budget")
    )
    def get_is_overassigned(self, obj):
        return obj.is_overassigned()

    def validate_tags(self, value):
        if value is None:
            return []

        normalized_tags = []
        seen = set()
        for item in value:
            if not isinstance(item, str):
                raise serializers.ValidationError("Each tag must be a string.")
            tag = item.strip()
            if not tag:
                continue
            key = tag.lower()
            if key in seen:
                continue
            seen.add(key)
            normalized_tags.append(tag)

        return normalized_tags


class DeliverableAssignmentNestedSerializer(serializers.ModelSerializer):
    """Nested serializer for assignments with staff details."""

    staff_name = serializers.SerializerMethodField()

    class Meta:
        model = DeliverableAssignment
        fields = ["id", "staff", "staff_name", "budget_hours", "is_lead", "created_at"]
        read_only_fields = ["id", "created_at"]

    def get_staff_name(self, obj):
        return f"{obj.staff.first_name} {obj.staff.last_name}"


class TaskNestedSerializer(serializers.ModelSerializer):
    """Nested serializer for tasks with assignee details."""

    assignee_name = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = [
            "id",
            "title",
            "assignee",
            "assignee_name",
            "budget_hours",
            "percent_complete",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_assignee_name(self, obj):
        if obj.assignee:
            return f"{obj.assignee.first_name} {obj.assignee.last_name}"
        return None


class DeliverableSerializer(serializers.ModelSerializer):
    # Computed rollup fields (read-only)
    assigned_budget_hours = serializers.SerializerMethodField()
    spent_hours = serializers.SerializerMethodField()
    planned_weeks = serializers.SerializerMethodField()
    elapsed_weeks = serializers.SerializerMethodField()
    assigned_budget_hours_per_week = serializers.SerializerMethodField()
    spent_hours_per_week = serializers.SerializerMethodField()
    remaining_budget_hours = serializers.SerializerMethodField()
    unspent_budget_hours = serializers.SerializerMethodField()
    variance_hours = serializers.SerializerMethodField()
    estimated_burn_rate = serializers.SerializerMethodField()
    actual_burn_rate = serializers.SerializerMethodField()
    estimated_percent_complete = serializers.SerializerMethodField()

    # Health flags (read-only)
    is_over_budget = serializers.SerializerMethodField()
    is_overassigned = serializers.SerializerMethodField()
    is_missing_budget = serializers.SerializerMethodField()
    is_missing_lead = serializers.SerializerMethodField()

    # Latest status update (read-only)
    latest_status_update = serializers.SerializerMethodField()

    # Nested related objects (read-only)
    assignments = DeliverableAssignmentNestedSerializer(many=True, read_only=True)
    tasks = TaskNestedSerializer(many=True, read_only=True)

    class Meta:
        model = Deliverable
        fields = [
            "id",
            "contract",  # writable FK id
            "name",
            "charge_code",
            "budget_hours",
            "target_completion_date",
            "status",
            "created_at",
            "updated_at",
            # Computed fields
            "assigned_budget_hours",
            "spent_hours",
            "planned_weeks",
            "elapsed_weeks",
            "assigned_budget_hours_per_week",
            "spent_hours_per_week",
            "remaining_budget_hours",
            "unspent_budget_hours",
            "variance_hours",
            "estimated_burn_rate",
            "actual_burn_rate",
            "estimated_percent_complete",
            "is_over_budget",
            "is_overassigned",
            "is_missing_budget",
            "is_missing_lead",
            "latest_status_update",
            # Nested related objects
            "assignments",
            "tasks",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
            "assigned_budget_hours",
            "spent_hours",
            "planned_weeks",
            "elapsed_weeks",
            "assigned_budget_hours_per_week",
            "spent_hours_per_week",
            "remaining_budget_hours",
            "unspent_budget_hours",
            "variance_hours",
            "estimated_burn_rate",
            "actual_burn_rate",
            "estimated_percent_complete",
            "is_over_budget",
            "is_overassigned",
            "is_missing_budget",
            "is_missing_lead",
            "latest_status_update",
            "assignments",
            "tasks",
        ]

    @extend_schema_field(serializers.FloatField(read_only=True, help_text="Sum of budget hours from all tasks"))
    def get_assigned_budget_hours(self, obj):
        return obj.get_assigned_budget_hours()

    @extend_schema_field(serializers.FloatField(read_only=True, help_text="Sum of spent hours from all time entries"))
    def get_spent_hours(self, obj):
        return obj.get_spent_hours()

    @extend_schema_field(
        serializers.IntegerField(read_only=True, help_text="Number of planned weeks for this deliverable")
    )
    def get_planned_weeks(self, obj):
        return obj.get_planned_weeks()

    @extend_schema_field(
        serializers.IntegerField(read_only=True, help_text="Number of elapsed weeks from start to today")
    )
    def get_elapsed_weeks(self, obj):
        return obj.get_elapsed_weeks()

    @extend_schema_field(
        serializers.FloatField(read_only=True, help_text="Sum of assigned budget hours per week from all assignments")
    )
    def get_assigned_budget_hours_per_week(self, obj):
        return obj.get_assigned_budget_hours_per_week()

    @extend_schema_field(serializers.FloatField(read_only=True, help_text="Spent hours divided by elapsed weeks"))
    def get_spent_hours_per_week(self, obj):
        return obj.get_spent_hours_per_week()

    @extend_schema_field(
        serializers.FloatField(read_only=True, help_text="Remaining budget hours (budget - assigned budget hours)")
    )
    def get_remaining_budget_hours(self, obj):
        return obj.get_remaining_budget_hours()

    @extend_schema_field(
        serializers.FloatField(read_only=True, help_text="Unspent budget hours (budget - spent hours)")
    )
    def get_unspent_budget_hours(self, obj):
        return obj.get_unspent_budget_hours()

    @extend_schema_field(
        serializers.FloatField(
            read_only=True,
            help_text="Variance in hours per week (spent_hours_per_week - assigned_budget_hours_per_week)."
            " Positive = over pace, negative = under pace",
        )
    )
    def get_variance_hours(self, obj):
        return obj.get_variance_hours()

    @extend_schema_field(
        serializers.FloatField(
            read_only=True,
            help_text="Estimated burn rate (hours per week) based on staff assignments",
        )
    )
    def get_estimated_burn_rate(self, obj):
        return obj.get_estimated_burn_rate()

    @extend_schema_field(
        serializers.FloatField(
            read_only=True,
            help_text="Actual burn rate (hours per week) based on recent time entries (last 4 weeks)",
        )
    )
    def get_actual_burn_rate(self, obj):
        return obj.get_actual_burn_rate(weeks=4)

    @extend_schema_field(
        serializers.FloatField(
            read_only=True,
            help_text="Estimated completion percentage (0-100) rolled up from tasks",
        )
    )
    def get_estimated_percent_complete(self, obj):
        return obj.get_estimated_percent_complete()

    @extend_schema_field(
        serializers.BooleanField(read_only=True, help_text="True if spent hours exceed deliverable budget")
    )
    def get_is_over_budget(self, obj):
        return obj.is_over_budget()

    @extend_schema_field(
        serializers.BooleanField(read_only=True, help_text="True if assigned budget hours exceed deliverable budget")
    )
    def get_is_overassigned(self, obj):
        return obj.is_overassigned()

    @extend_schema_field(serializers.BooleanField(read_only=True, help_text="True if budget hours is 0 but has tasks"))
    def get_is_missing_budget(self, obj):
        return obj.is_missing_budget()

    @extend_schema_field(serializers.BooleanField(read_only=True, help_text="True if no assignment has is_lead=True"))
    def get_is_missing_lead(self, obj):
        return obj.is_missing_lead()

    @extend_schema_field(
        serializers.DictField(read_only=True, allow_null=True, help_text="Most recent status update by period_end")
    )
    def get_latest_status_update(self, obj):
        latest = obj.get_latest_status_update()
        if latest:
            return {
                "id": latest.id,
                "period_end": latest.period_end,
                "status": latest.status,
                "summary": latest.summary,
                "created_by": latest.created_by_id,
                "created_at": latest.created_at,
            }
        return None


class TaskSerializer(serializers.ModelSerializer):
    # Ensure nullable FK behaves the way we want at the API boundary:
    # - required=False allows omitted field on create/update
    # - allow_null=True allows explicit null
    assignee = serializers.PrimaryKeyRelatedField(
        queryset=Staff.objects.all(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Task
        fields = [
            "id",
            "deliverable",  # writable FK id
            "assignee",  # nullable FK id
            "title",
            "budget_hours",
            "percent_complete",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class DeliverableAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliverableAssignment
        fields = [
            "id",
            "deliverable",  # writable FK id
            "staff",  # writable FK id
            "budget_hours",
            "is_lead",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]
        validators = [
            # Ensures duplicate (deliverable, staff) becomes HTTP 400 rather than DB 500
            UniqueTogetherValidator(
                queryset=DeliverableAssignment.objects.all(),
                fields=["deliverable", "staff"],
                message="This staff member is already assigned to this deliverable.",
            )
        ]


class DeliverableTimeEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliverableTimeEntry
        fields = [
            "id",
            "deliverable",  # writable FK id
            "entry_date",
            "hours",
            "note",
            "external_source",
            "external_id",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        """
        Validate idempotency fields.
        If external_source is provided, external_id must also be provided.
        """
        external_source = attrs.get("external_source", "")
        external_id = attrs.get("external_id", "")

        if external_source and not external_id:
            raise serializers.ValidationError(
                {"external_id": "external_id is required when external_source is provided."}
            )

        if external_id and not external_source:
            raise serializers.ValidationError(
                {"external_source": "external_source is required when external_id is provided."}
            )

        return attrs


class DeliverableStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliverableStatusUpdate
        fields = [
            "id",
            "deliverable",  # writable FK id
            "period_end",
            "status",
            "summary",
            "created_by",  # writable FK id (nullable if model allows)
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
        validators = [
            # Ensures duplicate (deliverable, period_end) becomes HTTP 400 rather than DB 500
            UniqueTogetherValidator(
                queryset=DeliverableStatusUpdate.objects.all(),
                fields=["deliverable", "period_end"],
                message="A status update for this deliverable and period_end already exists.",
            )
        ]


class InitiativeWeeklyUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = InitiativeWeeklyUpdate
        fields = [
            "id",
            "initiative",
            "period_end",
            "percent_complete",
            "summary",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
        validators = [
            UniqueTogetherValidator(
                queryset=InitiativeWeeklyUpdate.objects.all(),
                fields=["initiative", "period_end"],
                message="A weekly update for this initiative and period_end already exists.",
            )
        ]


class InitiativeSerializer(serializers.ModelSerializer):
    owner_name = serializers.SerializerMethodField()
    current_percent_complete = serializers.SerializerMethodField()
    latest_update = serializers.SerializerMethodField()
    is_update_stale = serializers.SerializerMethodField()
    tags = serializers.ListField(child=serializers.CharField(max_length=50, allow_blank=True), required=False)

    class Meta:
        model = Initiative
        fields = [
            "id",
            "name",
            "owner",
            "owner_name",
            "status",
            "tags",
            "target_date",
            "notes",
            "created_at",
            "updated_at",
            "current_percent_complete",
            "latest_update",
            "is_update_stale",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
            "owner_name",
            "current_percent_complete",
            "latest_update",
            "is_update_stale",
        ]

    def get_owner_name(self, obj):
        if obj.owner:
            return f"{obj.owner.first_name} {obj.owner.last_name}".strip()
        return None

    @extend_schema_field(
        serializers.FloatField(read_only=True, help_text="Current completion percentage from the latest weekly update")
    )
    def get_current_percent_complete(self, obj):
        return obj.get_current_percent_complete()

    @extend_schema_field(InitiativeWeeklyUpdateSerializer(allow_null=True))
    def get_latest_update(self, obj):
        latest = obj.get_latest_update()
        if not latest:
            return None
        return InitiativeWeeklyUpdateSerializer(latest).data

    @extend_schema_field(
        serializers.BooleanField(read_only=True, help_text="True if latest weekly update is older than 7 days")
    )
    def get_is_update_stale(self, obj):
        return obj.is_update_stale(days=7)

    def validate_tags(self, value):
        if value is None:
            return []

        normalized_tags = []
        seen = set()
        for item in value:
            if not isinstance(item, str):
                raise serializers.ValidationError("Each tag must be a string.")
            tag = item.strip()
            if not tag:
                continue
            key = tag.lower()
            if key in seen:
                continue
            seen.add(key)
            normalized_tags.append(tag)

        return normalized_tags
