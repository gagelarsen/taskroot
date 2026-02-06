"""
Tests to cover remaining edge cases for 100% coverage.
"""

from datetime import date
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from core.models import DeliverableTimeEntry, Task


@pytest.mark.django_db
class TestPermissionEdgeCases:
    """Test permission edge cases to achieve 100% coverage."""

    def test_can_create_task_as_staff_non_post_request(self, staff_user, deliverable):
        """Test CanCreateTaskAsStaff allows non-POST requests (line 52)."""
        client = APIClient()
        client.force_authenticate(user=staff_user)

        # GET request should be allowed
        response = client.get("/api/v1/tasks/")
        assert response.status_code == 200

    def test_can_create_task_as_staff_user_without_staff_profile(self, user_without_staff, deliverable):
        """Test CanCreateTaskAsStaff denies user without staff profile (line 56)."""
        client = APIClient()
        client.force_authenticate(user=user_without_staff)

        # POST request should be denied
        response = client.post(
            "/api/v1/tasks/",
            {
                "deliverable": deliverable.id,
                "title": "Test Task",
                "status": "todo",
            },
            format="json",
        )
        assert response.status_code == 403

    def test_can_create_task_with_invalid_assignee_type(self, staff_user, deliverable):
        """Test CanCreateTaskAsStaff with invalid assignee type (lines 71-72)."""
        client = APIClient()
        client.force_authenticate(user=staff_user)

        # POST with invalid assignee type (list instead of int)
        response = client.post(
            "/api/v1/tasks/",
            {
                "deliverable": deliverable.id,
                "title": "Test Task",
                "status": "todo",
                "assignee": [1, 2, 3],  # Invalid type - list instead of int
            },
            format="json",
        )
        assert response.status_code in (400, 403)  # Either validation error or permission denied


@pytest.mark.django_db
class TestViewEdgeCases:
    """Test view edge cases to achieve 100% coverage."""

    def test_staff_create_task_for_other_staff(self, staff_user, staff_profile, other_staff_user_profile, deliverable):
        """Test staff creating task for another staff (line 339)."""
        client = APIClient()
        client.force_authenticate(user=staff_user)

        response = client.post(
            "/api/v1/tasks/",
            {
                "deliverable": deliverable.id,
                "title": "Task for other",
                "status": "todo",
                "assignee": other_staff_user_profile.id,
            },
            format="json",
        )
        assert response.status_code == 403
        assert "themselves" in str(response.data).lower() or "unassigned" in str(response.data).lower()

    def test_staff_update_unassigned_task(self, staff_user, deliverable):
        """Test staff updating unassigned task (line 349)."""
        # Create unassigned task
        task = Task.objects.create(
            deliverable=deliverable,
            title="Unassigned Task",
            status="todo",
            assignee=None,
        )

        client = APIClient()
        client.force_authenticate(user=staff_user)

        response = client.patch(
            f"/api/v1/tasks/{task.id}/",
            {"title": "Updated Title"},
            format="json",
        )
        assert response.status_code == 403

    def test_staff_update_other_staff_time_entry(self, staff_user, other_staff_user_profile, deliverable):
        """Test staff updating another staff's time entry (line 554)."""
        # Create time entry for other staff
        entry = DeliverableTimeEntry.objects.create(
            deliverable=deliverable,
            entry_date=date(2024, 1, 15),
            hours=Decimal("5.0"),
        )

        client = APIClient()
        client.force_authenticate(user=staff_user)

        response = client.patch(
            f"/api/v1/deliverable-time-entries/{entry.id}/",
            {"hours": "10.0"},
            format="json",
        )
        assert response.status_code == 403

    def test_staff_delete_other_staff_time_entry(self, staff_user, other_staff_user_profile, deliverable):
        """Test staff deleting another staff's time entry (line 568)."""
        # Create time entry for other staff
        entry = DeliverableTimeEntry.objects.create(
            deliverable=deliverable,
            entry_date=date(2024, 1, 15),
            hours=Decimal("5.0"),
        )

        client = APIClient()
        client.force_authenticate(user=staff_user)

        response = client.delete(f"/api/v1/deliverable-time-entries/{entry.id}/")
        assert response.status_code == 403


@pytest.mark.django_db
class TestFilterEdgeCases:
    """Test filter edge cases to achieve 100% coverage."""

    def test_deliverable_filter_staff_id_none(self, staff_user, contract, deliverable):
        """Test deliverable filter with staff_id=None (line 112)."""
        client = APIClient()
        client.force_authenticate(user=staff_user)

        # Test with None value (empty parameter)
        response = client.get("/api/v1/deliverables/", {"staff_id": ""})
        assert response.status_code == 200
        # Should return all deliverables (filter ignored)


@pytest.mark.django_db
class TestSerializerEdgeCases:
    """Test serializer edge cases to achieve 100% coverage."""

    def test_time_entry_hours_validation_zero(self, staff_user, staff_profile, deliverable):
        """Test time entry hours validation for zero value (line 324)."""
        client = APIClient()
        client.force_authenticate(user=staff_user)

        # Try to create time entry with zero hours
        response = client.post(
            "/api/v1/deliverable-time-entries/",
            {
                "deliverable": deliverable.id,
                "entry_date": "2024-01-15",
                "hours": "0.0",
            },
            format="json",
        )
        assert response.status_code == 400
        assert "hours" in response.data
