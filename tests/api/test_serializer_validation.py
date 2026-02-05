"""
Tests for serializer validation edge cases.
"""

import pytest
from rest_framework.test import APIClient


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
                "entry_date": "2024-01-15",
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
                "entry_date": "2024-01-15",
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
                "entry_date": "2024-01-15",
                "hours": "5.5",
            },
            format="json",
        )
        assert response.status_code == 201
        assert response.data["hours"] == "5.50"
