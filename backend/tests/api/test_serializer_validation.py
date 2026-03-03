"""
Tests for serializer validation edge cases.
"""

import pytest
from rest_framework import serializers
from rest_framework.test import APIClient

from core.api.v1.serializers import (
    ContractSerializer,
    FutureWorkSerializer,
    FutureWorkToContractSerializer,
    InitiativeSerializer,
)
from core.models import FutureWork, Initiative


@pytest.mark.django_db
class TestTimeEntryValidation:
    """Test time entry serializer validation."""

    def test_hours_must_be_positive(self, staff_user, staff_profile, deliverable):
        """Test that hours must be greater than 0."""
        client = APIClient()
        client.force_authenticate(user=staff_user)

        # Try to create time entry with negative hours
        response = client.post(
            "/api/v1/deliverable-time-entries/",
            {
                "deliverable": deliverable.id,
                "entry_date": "2026-01-15",
                "hours": "-5.0",
            },
            format="json",
        )
        assert response.status_code == 400
        assert "hours" in response.data
        # Check that validation error is present (either model or serializer validation)
        assert len(response.data["hours"]) > 0

    def test_hours_cannot_be_zero(self, staff_user, staff_profile, deliverable):
        """Test that hours cannot be 0."""
        client = APIClient()
        client.force_authenticate(user=staff_user)

        # Try to create time entry with zero hours
        response = client.post(
            "/api/v1/deliverable-time-entries/",
            {
                "deliverable": deliverable.id,
                "entry_date": "2026-01-15",
                "hours": "0",
            },
            format="json",
        )
        assert response.status_code == 400
        assert "hours" in response.data
        # Check that validation error is present (either model or serializer validation)
        assert len(response.data["hours"]) > 0

    def test_hours_positive_value_accepted(self, staff_user, staff_profile, deliverable):
        """Test that positive hours are accepted."""
        client = APIClient()
        client.force_authenticate(user=staff_user)

        # Create time entry with positive hours
        response = client.post(
            "/api/v1/deliverable-time-entries/",
            {
                "deliverable": deliverable.id,
                "entry_date": "2026-01-15",
                "hours": "5.5",
            },
            format="json",
        )
        assert response.status_code == 201
        assert response.data["hours"] == "5.50"


@pytest.mark.django_db
class TestTagAndOwnerSerializationValidation:
    def test_contract_validate_tags_none_and_invalid_type(self):
        serializer = ContractSerializer()
        assert serializer.validate_tags(None) == []

        with pytest.raises(serializers.ValidationError):
            serializer.validate_tags(["ops", 123])

    def test_initiative_serializer_owner_name_and_latest_update_none(self):
        initiative = Initiative.objects.create(name="No Owner Initiative", owner=None, status="active")
        serialized = InitiativeSerializer(initiative).data
        assert serialized["owner_name"] is None
        assert serialized["latest_update"] is None

    def test_initiative_serializer_owner_name_present(self, staff_profile):
        initiative = Initiative.objects.create(name="Owner Initiative", owner=staff_profile, status="active")
        serialized = InitiativeSerializer(initiative).data
        assert serialized["owner_name"] == f"{staff_profile.first_name} {staff_profile.last_name}".strip()

    def test_initiative_validate_tags_none_and_invalid_type(self):
        serializer = InitiativeSerializer()
        assert serializer.validate_tags(None) == []

        with pytest.raises(serializers.ValidationError):
            serializer.validate_tags(["ops", 123])

    def test_initiative_validate_tags_trims_blanks_and_deduplicates_case_insensitive(self):
        serializer = InitiativeSerializer()
        normalized = serializer.validate_tags([" Ops ", "ops", "", "Internal"])
        assert normalized == ["Ops", "Internal"]

    def test_future_work_serializer_owner_name_and_validate_tags(self, staff_profile):
        item = FutureWork.objects.create(name="With Owner", owner=staff_profile, tags=["Pipeline"])
        serialized = FutureWorkSerializer(item).data
        assert serialized["owner_name"] == f"{staff_profile.first_name} {staff_profile.last_name}".strip()

        serializer = FutureWorkSerializer()
        assert serializer.validate_tags(None) == []
        normalized = serializer.validate_tags([" Pipeline ", "pipeline", "", "Internal"])
        assert normalized == ["Pipeline", "Internal"]

        with pytest.raises(serializers.ValidationError):
            serializer.validate_tags(["ok", 999])

    def test_future_work_to_contract_serializer_rejects_end_before_start(self):
        serializer = FutureWorkToContractSerializer(
            data={
                "name": "Bad Date Contract",
                "start_date": "2026-10-31",
                "end_date": "2026-04-01",
                "budget_hours": "240.00",
            }
        )
        assert serializer.is_valid() is False
        assert "end_date" in serializer.errors
