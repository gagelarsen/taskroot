"""
Tests for permission edge cases.
"""

from datetime import date
from decimal import Decimal

import pytest

from core.models import DeliverableTimeEntry, Task


class TestTimeEntryPermissions:
    """Test time entry permission edge cases."""

    def test_user_without_staff_profile_cannot_edit_time_entry(
        self, api_client, deliverable, staff_profile, user_without_staff
    ):
        """Test that a user without a staff profile cannot edit time entries."""
        api_client.force_authenticate(user=user_without_staff)

        # Create a time entry
        entry = DeliverableTimeEntry.objects.create(
            deliverable=deliverable,
            staff=staff_profile,
            entry_date=date(2024, 1, 15),
            hours=Decimal("8.0"),
        )

        # Try to update it
        response = api_client.patch(
            f"/api/v1/deliverable-time-entries/{entry.id}/",
            {"hours": 10.0},
            format="json",
        )
        # Should be forbidden
        assert response.status_code in (403, 401)

    def test_manager_can_edit_any_time_entry(
        self, api_client, deliverable, staff_profile, manager_user, manager_profile
    ):
        """Test that managers can edit any time entry."""
        # Create a time entry for staff
        entry = DeliverableTimeEntry.objects.create(
            deliverable=deliverable,
            staff=staff_profile,
            entry_date=date(2024, 1, 15),
            hours=Decimal("8.0"),
        )

        # Manager tries to edit it
        api_client.force_authenticate(user=manager_user)
        response = api_client.patch(
            f"/api/v1/deliverable-time-entries/{entry.id}/",
            {"hours": 10.0},
            format="json",
        )
        assert response.status_code == 200

    def test_admin_can_edit_any_time_entry(self, api_client, deliverable, staff_profile, admin_user, admin_profile):
        """Test that admins can edit any time entry."""
        # Create a time entry for staff
        entry = DeliverableTimeEntry.objects.create(
            deliverable=deliverable,
            staff=staff_profile,
            entry_date=date(2024, 1, 15),
            hours=Decimal("8.0"),
        )

        # Admin tries to edit it
        api_client.force_authenticate(user=admin_user)
        response = api_client.patch(
            f"/api/v1/deliverable-time-entries/{entry.id}/",
            {"hours": 10.0},
            format="json",
        )
        assert response.status_code == 200

    def test_staff_can_read_others_time_entries(self, api_client, deliverable, staff_user, other_staff_user_profile):
        """Test that staff can read other staff's time entries."""
        # Create a time entry for other staff
        entry = DeliverableTimeEntry.objects.create(
            deliverable=deliverable,
            staff=other_staff_user_profile,
            entry_date=date(2024, 1, 15),
            hours=Decimal("8.0"),
        )

        # Staff tries to read it
        api_client.force_authenticate(user=staff_user)
        response = api_client.get(f"/api/v1/deliverable-time-entries/{entry.id}/")
        assert response.status_code == 200


@pytest.mark.django_db
class TestTaskPermissions:
    """Test task permission edge cases."""

    def test_staff_can_list_tasks(self, api_client, staff_user, staff_profile, deliverable):
        """Test that staff can list tasks."""
        Task.objects.create(
            deliverable=deliverable,
            title="Test Task",
            assignee=staff_profile,
        )

        api_client.force_authenticate(user=staff_user)
        response = api_client.get("/api/v1/tasks/")
        assert response.status_code == 200

    def test_staff_can_retrieve_task(self, api_client, staff_user, staff_profile, deliverable):
        """Test that staff can retrieve a task."""
        task = Task.objects.create(
            deliverable=deliverable,
            title="Test Task",
            assignee=staff_profile,
        )

        api_client.force_authenticate(user=staff_user)
        response = api_client.get(f"/api/v1/tasks/{task.id}/")
        assert response.status_code == 200

    def test_staff_cannot_update_unassigned_task(self, api_client, staff_user, deliverable):
        """Test that staff cannot update tasks not assigned to them."""
        task = Task.objects.create(
            deliverable=deliverable,
            title="Test Task",
            assignee=None,  # Unassigned
        )

        api_client.force_authenticate(user=staff_user)
        response = api_client.patch(
            f"/api/v1/tasks/{task.id}/",
            {"title": "Updated Title"},
            format="json",
        )
        assert response.status_code == 403

    def test_staff_can_create_task_assigned_to_null(self, api_client, staff_user, staff_profile, deliverable):
        """Test that staff can create unassigned tasks."""
        api_client.force_authenticate(user=staff_user)
        response = api_client.post(
            "/api/v1/tasks/",
            {
                "deliverable": deliverable.id,
                "title": "New Task",
                "assignee": None,
            },
            format="json",
        )
        assert response.status_code == 201

    def test_staff_cannot_destroy_others_task(self, api_client, staff_user, other_staff_user_profile, deliverable):
        """Test that staff cannot delete tasks assigned to others."""
        task = Task.objects.create(
            deliverable=deliverable,
            title="Test Task",
            assignee=other_staff_user_profile,
        )

        api_client.force_authenticate(user=staff_user)
        response = api_client.delete(f"/api/v1/tasks/{task.id}/")
        assert response.status_code == 403


@pytest.mark.django_db
class TestViewEdgeCases:
    """Test view edge cases."""

    def test_time_entry_create_with_zero_hours_fails(self, api_client, admin_user, admin_profile, deliverable):
        """Test that creating a time entry with zero hours fails."""
        api_client.force_authenticate(user=admin_user)
        response = api_client.post(
            "/api/v1/deliverable-time-entries/",
            {
                "deliverable": deliverable.id,
                "staff": admin_profile.id,
                "entry_date": "2024-01-15",
                "hours": 0,  # Invalid
            },
            format="json",
        )
        assert response.status_code == 400
        assert "hours" in response.data or "Hours must be greater than 0" in str(response.data)

    def test_staff_can_delete_own_time_entry(self, api_client, staff_user, staff_profile, deliverable):
        """Test that staff can delete their own time entries."""
        # Create a time entry for staff
        entry = DeliverableTimeEntry.objects.create(
            deliverable=deliverable,
            staff=staff_profile,
            entry_date=date(2024, 1, 15),
            hours=Decimal("8.0"),
        )

        # Staff tries to delete it
        api_client.force_authenticate(user=staff_user)
        response = api_client.delete(f"/api/v1/deliverable-time-entries/{entry.id}/")
        assert response.status_code == 204

    def test_staff_cannot_delete_others_time_entry(self, api_client, staff_user, other_staff_user_profile, deliverable):
        """Test that staff cannot delete other staff's time entries."""
        # Create a time entry for other staff
        entry = DeliverableTimeEntry.objects.create(
            deliverable=deliverable,
            staff=other_staff_user_profile,
            entry_date=date(2024, 1, 15),
            hours=Decimal("8.0"),
        )

        # Staff tries to delete it
        api_client.force_authenticate(user=staff_user)
        response = api_client.delete(f"/api/v1/deliverable-time-entries/{entry.id}/")
        assert response.status_code == 403

    def test_staff_cannot_update_others_time_entry(self, api_client, staff_user, other_staff_user_profile, deliverable):
        """Test that staff cannot update other staff's time entries."""
        # Create a time entry for other staff
        entry = DeliverableTimeEntry.objects.create(
            deliverable=deliverable,
            staff=other_staff_user_profile,
            entry_date=date(2024, 1, 15),
            hours=Decimal("8.0"),
        )

        # Staff tries to update it
        api_client.force_authenticate(user=staff_user)
        response = api_client.patch(
            f"/api/v1/deliverable-time-entries/{entry.id}/",
            {"hours": 10.0},
            format="json",
        )
        assert response.status_code == 403

    def test_staff_can_create_own_time_entry(self, api_client, staff_user, staff_profile, deliverable):
        """Test that staff can create their own time entries."""
        api_client.force_authenticate(user=staff_user)
        response = api_client.post(
            "/api/v1/deliverable-time-entries/",
            {
                "deliverable": deliverable.id,
                "staff": staff_profile.id,
                "entry_date": "2024-01-15",
                "hours": 8.0,
            },
            format="json",
        )
        assert response.status_code == 201
