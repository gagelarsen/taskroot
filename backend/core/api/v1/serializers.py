from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from core.models import (
    Contract,
    Deliverable,
    DeliverableAssignment,
    DeliverableStatusUpdate,
    DeliverableTimeEntry,
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
    # Computed rollup fields (read-only)
    assigned_budget_hours = serializers.SerializerMethodField()
    spent_hours = serializers.SerializerMethodField()
    planned_weeks = serializers.SerializerMethodField()
    elapsed_weeks = serializers.SerializerMethodField()
    assigned_budget_hours_per_week = serializers.SerializerMethodField()
    spent_hours_per_week = serializers.SerializerMethodField()
    remaining_budget_hours = serializers.SerializerMethodField()
    unspent_budget_hours = serializers.SerializerMethodField()

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
            "is_over_budget",
            "is_overassigned",
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
        serializers.FloatField(read_only=True, help_text="Assigned budget hours divided by planned weeks")
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

    @extend_schema_field(serializers.BooleanField(read_only=True, help_text="True if spent hours exceed budget"))
    def get_is_over_budget(self, obj):
        return obj.is_over_budget()

    @extend_schema_field(
        serializers.BooleanField(read_only=True, help_text="True if assigned budget hours exceed contract budget")
    )
    def get_is_overassigned(self, obj):
        return obj.is_overassigned()


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
        fields = ["id", "title", "assignee", "assignee_name", "budget_hours", "status", "created_at", "updated_at"]
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
        serializers.FloatField(read_only=True, help_text="Assigned budget hours divided by planned weeks")
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
            read_only=True, help_text="Variance between spent and assigned budget hours (spent - assigned budget)"
        )
    )
    def get_variance_hours(self, obj):
        return obj.get_variance_hours()

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
