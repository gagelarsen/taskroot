"""
Tests for view-level permission edge cases.
"""

from datetime import date
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from core.models import DeliverableTimeEntry, Task


class TestTaskViewPermissions:
    """Test task view permission edge cases."""

    def test_staff_cannot_create_task_for_other_staff(
        self, staff_user, staff_profile, other_staff_user_profile, deliverable
    ):
        """Test that staff cannot create tasks assigned to other staff."""
        client = APIClient()
        client.force_authenticate(user=staff_user)

        response = client.post(
            "/api/v1/tasks/",
            {
                "deliverable": deliverable.id,
                "title": "Task for other staff",
                "status": "todo",
                "assignee": other_staff_user_profile.id,
            },
            format="json",
        )
        assert response.status_code == 403
        assert "themselves" in str(response.data).lower() or "unassigned" in str(response.data).lower()

    def test_staff_cannot_update_task_not_assigned_to_them(
        self, staff_user, staff_profile, other_staff_user_profile, deliverable
    ):
        """Test that staff cannot update tasks not assigned to them."""
        # Create task assigned to other staff
        task = Task.objects.create(
            deliverable=deliverable,
            title="Other's task",
            status="todo",
            assignee=other_staff_user_profile,
        )

        client = APIClient()
        client.force_authenticate(user=staff_user)

        response = client.patch(
            f"/api/v1/tasks/{task.id}/",
            {"title": "Updated title"},
            format="json",
        )
        assert response.status_code == 403

    def test_manager_can_create_task_for_any_staff(self, manager_user, manager_profile, staff_profile, deliverable):
        """Test that managers can create tasks for any staff."""
        client = APIClient()
        client.force_authenticate(user=manager_user)

        response = client.post(
            "/api/v1/tasks/",
            {
                "deliverable": deliverable.id,
                "title": "Task for staff",
                "status": "todo",
                "assignee": staff_profile.id,
            },
            format="json",
        )
        assert response.status_code == 201


@pytest.mark.django_db
class TestTimeEntryViewPermissions:
    """Test time entry view permission edge cases."""

    def test_staff_cannot_update_other_staff_time_entry(
        self, staff_user, staff_profile, other_staff_user_profile, deliverable
    ):
        """Test that staff cannot update other staff's time entries."""
        # Create time entry for other staff
        entry = DeliverableTimeEntry.objects.create(
            deliverable=deliverable,
            staff=other_staff_user_profile,
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
        assert "own" in str(response.data).lower()

    def test_staff_cannot_delete_other_staff_time_entry(
        self, staff_user, staff_profile, other_staff_user_profile, deliverable
    ):
        """Test that staff cannot delete other staff's time entries."""
        # Create time entry for other staff
        entry = DeliverableTimeEntry.objects.create(
            deliverable=deliverable,
            staff=other_staff_user_profile,
            entry_date=date(2024, 1, 15),
            hours=Decimal("5.0"),
        )

        client = APIClient()
        client.force_authenticate(user=staff_user)

        response = client.delete(f"/api/v1/deliverable-time-entries/{entry.id}/")
        assert response.status_code == 403
        assert "own" in str(response.data).lower()

    def test_manager_can_update_any_time_entry(self, manager_user, manager_profile, staff_profile, deliverable):
        """Test that managers can update any time entry."""
        # Create time entry for staff
        entry = DeliverableTimeEntry.objects.create(
            deliverable=deliverable,
            staff=staff_profile,
            entry_date=date(2024, 1, 15),
            hours=Decimal("5.0"),
        )

        client = APIClient()
        client.force_authenticate(user=manager_user)

        response = client.patch(
            f"/api/v1/deliverable-time-entries/{entry.id}/",
            {"hours": "10.0"},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["hours"] == "10.00"
