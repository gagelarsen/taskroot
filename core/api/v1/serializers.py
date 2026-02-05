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
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class ContractSerializer(serializers.ModelSerializer):
    # Computed rollup fields (read-only)
    expected_hours_total = serializers.SerializerMethodField()
    actual_hours_total = serializers.SerializerMethodField()
    planned_weeks = serializers.SerializerMethodField()
    elapsed_weeks = serializers.SerializerMethodField()
    expected_hours_per_week = serializers.SerializerMethodField()
    actual_hours_per_week = serializers.SerializerMethodField()
    remaining_budget_hours = serializers.SerializerMethodField()

    # Health flags (read-only)
    is_over_budget = serializers.SerializerMethodField()
    is_over_expected = serializers.SerializerMethodField()

    class Meta:
        model = Contract
        fields = [
            "id",
            "start_date",
            "end_date",
            "budget_hours_total",
            "status",
            "created_at",
            "updated_at",
            # Computed fields
            "expected_hours_total",
            "actual_hours_total",
            "planned_weeks",
            "elapsed_weeks",
            "expected_hours_per_week",
            "actual_hours_per_week",
            "remaining_budget_hours",
            "is_over_budget",
            "is_over_expected",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
            "expected_hours_total",
            "actual_hours_total",
            "planned_weeks",
            "elapsed_weeks",
            "expected_hours_per_week",
            "actual_hours_per_week",
            "remaining_budget_hours",
            "is_over_budget",
            "is_over_expected",
        ]

    @extend_schema_field(
        serializers.FloatField(read_only=True, help_text="Sum of expected hours from all deliverables")
    )
    def get_expected_hours_total(self, obj):
        return obj.get_expected_hours_total()

    @extend_schema_field(serializers.FloatField(read_only=True, help_text="Sum of actual hours from all deliverables"))
    def get_actual_hours_total(self, obj):
        return obj.get_actual_hours_total()

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

    @extend_schema_field(serializers.FloatField(read_only=True, help_text="Expected hours divided by planned weeks"))
    def get_expected_hours_per_week(self, obj):
        return obj.get_expected_hours_per_week()

    @extend_schema_field(serializers.FloatField(read_only=True, help_text="Actual hours divided by elapsed weeks"))
    def get_actual_hours_per_week(self, obj):
        return obj.get_actual_hours_per_week()

    @extend_schema_field(serializers.FloatField(read_only=True, help_text="Remaining budget hours (budget - actual)"))
    def get_remaining_budget_hours(self, obj):
        return obj.get_remaining_budget_hours()

    @extend_schema_field(serializers.BooleanField(read_only=True, help_text="True if actual hours exceed budget"))
    def get_is_over_budget(self, obj):
        return obj.is_over_budget()

    @extend_schema_field(serializers.BooleanField(read_only=True, help_text="True if actual hours exceed expected"))
    def get_is_over_expected(self, obj):
        return obj.is_over_expected()


class DeliverableSerializer(serializers.ModelSerializer):
    # Computed rollup fields (read-only)
    expected_hours_total = serializers.SerializerMethodField()
    actual_hours_total = serializers.SerializerMethodField()
    planned_weeks = serializers.SerializerMethodField()
    elapsed_weeks = serializers.SerializerMethodField()
    expected_hours_per_week = serializers.SerializerMethodField()
    actual_hours_per_week = serializers.SerializerMethodField()
    variance_hours = serializers.SerializerMethodField()

    # Health flags (read-only)
    is_over_expected = serializers.SerializerMethodField()
    is_missing_estimate = serializers.SerializerMethodField()
    is_missing_lead = serializers.SerializerMethodField()

    # Latest status update (read-only)
    latest_status_update = serializers.SerializerMethodField()

    class Meta:
        model = Deliverable
        fields = [
            "id",
            "contract",  # writable FK id
            "name",
            "start_date",
            "due_date",
            "status",
            "created_at",
            "updated_at",
            # Computed fields
            "expected_hours_total",
            "actual_hours_total",
            "planned_weeks",
            "elapsed_weeks",
            "expected_hours_per_week",
            "actual_hours_per_week",
            "variance_hours",
            "is_over_expected",
            "is_missing_estimate",
            "is_missing_lead",
            "latest_status_update",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
            "expected_hours_total",
            "actual_hours_total",
            "planned_weeks",
            "elapsed_weeks",
            "expected_hours_per_week",
            "actual_hours_per_week",
            "variance_hours",
            "is_over_expected",
            "is_missing_estimate",
            "is_missing_lead",
            "latest_status_update",
        ]

    @extend_schema_field(serializers.FloatField(read_only=True, help_text="Sum of expected hours from all assignments"))
    def get_expected_hours_total(self, obj):
        return obj.get_expected_hours_total()

    @extend_schema_field(serializers.FloatField(read_only=True, help_text="Sum of actual hours from all time entries"))
    def get_actual_hours_total(self, obj):
        return obj.get_actual_hours_total()

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

    @extend_schema_field(serializers.FloatField(read_only=True, help_text="Expected hours divided by planned weeks"))
    def get_expected_hours_per_week(self, obj):
        return obj.get_expected_hours_per_week()

    @extend_schema_field(serializers.FloatField(read_only=True, help_text="Actual hours divided by elapsed weeks"))
    def get_actual_hours_per_week(self, obj):
        return obj.get_actual_hours_per_week()

    @extend_schema_field(
        serializers.FloatField(read_only=True, help_text="Variance between actual and expected (actual - expected)")
    )
    def get_variance_hours(self, obj):
        return obj.get_variance_hours()

    @extend_schema_field(serializers.BooleanField(read_only=True, help_text="True if actual hours exceed expected"))
    def get_is_over_expected(self, obj):
        return obj.is_over_expected()

    @extend_schema_field(
        serializers.BooleanField(read_only=True, help_text="True if expected hours is 0 but has assignments")
    )
    def get_is_missing_estimate(self, obj):
        return obj.is_missing_estimate()

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
            "planned_hours",
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
            "expected_hours",
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
    # Make staff optional - perform_create will set it for staff role
    staff = serializers.PrimaryKeyRelatedField(
        queryset=Staff.objects.all(),
        required=False,
        allow_null=False,
    )

    class Meta:
        model = DeliverableTimeEntry
        fields = [
            "id",
            "deliverable",  # writable FK id
            "staff",  # writable FK id (optional, set by perform_create for staff role)
            "entry_date",
            "hours",
            "note",
            "external_source",
            "external_id",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def validate_hours(self, value):
        # Ensure hours <= 0 becomes HTTP 400 consistently.
        # (Even if the model has validators, this guarantees the API behavior.)
        if value <= 0:
            raise serializers.ValidationError("Hours must be greater than 0.")
        return value


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
        ]
        read_only_fields = ["id", "created_at"]
        validators = [
            # Ensures duplicate (deliverable, period_end) becomes HTTP 400 rather than DB 500
            UniqueTogetherValidator(
                queryset=DeliverableStatusUpdate.objects.all(),
                fields=["deliverable", "period_end"],
                message="A status update for this deliverable and period_end already exists.",
            )
        ]
