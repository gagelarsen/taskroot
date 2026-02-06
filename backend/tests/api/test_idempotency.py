"""
Tests for idempotent time entry creation.
"""

import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient

from core.models import Contract, Deliverable, DeliverableTimeEntry, Staff


@pytest.fixture
def admin_user(db):
    """Create an admin user with staff profile."""
    user = User.objects.create_user(username="admin", password="admin123")
    _ = Staff.objects.create(user=user, email="admin@example.com", role="admin")
    return user


@pytest.fixture
def api_client():
    """Create an API client."""
    return APIClient()


@pytest.fixture
def auth_client(api_client, admin_user):
    """Create an authenticated API client."""
    api_client.force_authenticate(user=admin_user)
    return api_client


@pytest.fixture
def contract(db):
    """Create a test contract."""
    return Contract.objects.create(
        start_date="2024-01-01",
        end_date="2024-12-31",
        budget_hours=1000,
        status="active",
    )


@pytest.fixture
def deliverable(contract):
    """Create a test deliverable."""
    return Deliverable.objects.create(
        contract=contract,
        name="Test Deliverable",
        status="in_progress",
    )


@pytest.fixture
def staff(db):
    """Create a test staff member."""
    user = User.objects.create_user(username="staff1", password="staff123")
    return Staff.objects.create(user=user, email="staff1@example.com", role="staff")


@pytest.mark.django_db
class TestTimeEntryIdempotency:
    """Test idempotent time entry creation."""

    def test_create_time_entry_without_idempotency_key(self, auth_client, deliverable, staff):
        """Creating time entries without idempotency key creates new entries each time."""
        payload = {
            "deliverable": deliverable.id,
            "staff": staff.id,
            "entry_date": "2024-01-15",
            "hours": 8.0,
            "note": "Development work",
        }

        # First request
        response1 = auth_client.post("/api/v1/deliverable-time-entries/", payload, format="json")
        assert response1.status_code == 201
        entry1_id = response1.data["id"]

        # Second request with same data
        response2 = auth_client.post("/api/v1/deliverable-time-entries/", payload, format="json")
        assert response2.status_code == 201
        entry2_id = response2.data["id"]

        # Should create two different entries
        assert entry1_id != entry2_id
        assert DeliverableTimeEntry.objects.count() == 2

    def test_create_time_entry_with_idempotency_key_returns_existing(self, auth_client, deliverable, staff):
        """Creating time entry with same idempotency key returns existing entry."""
        payload = {
            "deliverable": deliverable.id,
            "staff": staff.id,
            "entry_date": "2024-01-15",
            "hours": 8.0,
            "note": "Development work",
            "external_source": "jira",
            "external_id": "PROJ-123",
        }

        # First request - creates new entry
        response1 = auth_client.post("/api/v1/deliverable-time-entries/", payload, format="json")
        assert response1.status_code == 201
        entry1_id = response1.data["id"]
        assert response1.data["external_source"] == "jira"
        assert response1.data["external_id"] == "PROJ-123"

        # Second request with same idempotency key - returns existing
        response2 = auth_client.post("/api/v1/deliverable-time-entries/", payload, format="json")
        assert response2.status_code == 200  # 200 OK, not 201 Created
        entry2_id = response2.data["id"]

        # Should return the same entry
        assert entry1_id == entry2_id
        assert DeliverableTimeEntry.objects.count() == 1

    def test_different_idempotency_keys_create_different_entries(self, auth_client, deliverable, staff):
        """Different idempotency keys create different entries."""
        payload1 = {
            "deliverable": deliverable.id,
            "staff": staff.id,
            "entry_date": "2024-01-15",
            "hours": 8.0,
            "external_source": "jira",
            "external_id": "PROJ-123",
        }

        payload2 = {
            "deliverable": deliverable.id,
            "staff": staff.id,
            "entry_date": "2024-01-15",
            "hours": 6.0,
            "external_source": "jira",
            "external_id": "PROJ-456",  # Different external_id
        }

        response1 = auth_client.post("/api/v1/deliverable-time-entries/", payload1, format="json")
        assert response1.status_code == 201

        response2 = auth_client.post("/api/v1/deliverable-time-entries/", payload2, format="json")
        assert response2.status_code == 201

        # Should create two different entries
        assert response1.data["id"] != response2.data["id"]
        assert DeliverableTimeEntry.objects.count() == 2

    def test_external_source_without_external_id_fails(self, auth_client, deliverable, staff):
        """Providing external_source without external_id returns 400."""
        payload = {
            "deliverable": deliverable.id,
            "staff": staff.id,
            "entry_date": "2024-01-15",
            "hours": 8.0,
            "external_source": "jira",
            # Missing external_id
        }

        response = auth_client.post("/api/v1/deliverable-time-entries/", payload, format="json")
        assert response.status_code == 400
        assert "external_id" in response.data

    def test_external_id_without_external_source_fails(self, auth_client, deliverable, staff):
        """Providing external_id without external_source returns 400."""
        payload = {
            "deliverable": deliverable.id,
            "staff": staff.id,
            "entry_date": "2024-01-15",
            "hours": 8.0,
            "external_id": "PROJ-123",
            # Missing external_source
        }

        response = auth_client.post("/api/v1/deliverable-time-entries/", payload, format="json")
        assert response.status_code == 400
        assert "external_source" in response.data

    def test_idempotency_works_across_different_sources(self, auth_client, deliverable, staff):
        """Same external_id but different external_source creates different entries."""
        payload1 = {
            "deliverable": deliverable.id,
            "staff": staff.id,
            "entry_date": "2024-01-15",
            "hours": 8.0,
            "external_source": "jira",
            "external_id": "123",
        }

        payload2 = {
            "deliverable": deliverable.id,
            "staff": staff.id,
            "entry_date": "2024-01-15",
            "hours": 6.0,
            "external_source": "harvest",
            "external_id": "123",  # Same ID but different source
        }

        response1 = auth_client.post("/api/v1/deliverable-time-entries/", payload1, format="json")
        assert response1.status_code == 201

        response2 = auth_client.post("/api/v1/deliverable-time-entries/", payload2, format="json")
        assert response2.status_code == 201

        # Should create two different entries
        assert response1.data["id"] != response2.data["id"]
        assert DeliverableTimeEntry.objects.count() == 2
