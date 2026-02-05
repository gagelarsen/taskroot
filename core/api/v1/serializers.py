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
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class DeliverableSerializer(serializers.ModelSerializer):
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
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


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
