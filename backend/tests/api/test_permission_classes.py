"""
Tests for permission classes directly.
"""

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth.models import User
from rest_framework.exceptions import PermissionDenied
from rest_framework.test import APIClient

from core.api.v1.permissions import (
    CanEditTaskAsStaff,
    HasStaffProfile,
    ReadAllWriteAdminOnly,
)
from core.models import Contract, Deliverable, Staff


@pytest.mark.django_db
class TestCanCreateTaskAsStaff:
    """Test CanCreateTaskAsStaff permission via API."""

    def test_staff_can_create_with_assignee_field_missing(self, staff_user, staff_profile):
        """Test that staff can create when assignee field is missing."""
        client = APIClient()
        client.force_authenticate(user=staff_user)

        contract = Contract.objects.create(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            budget_hours_total=Decimal("1000.0"),
        )
        deliverable = Deliverable.objects.create(contract=contract, name="Test")

        response = client.post(
            "/api/v1/tasks/",
            {"deliverable": deliverable.id, "title": "Test"},
            format="json",
        )
        assert response.status_code == 201

    def test_staff_can_create_with_assignee_self(self, staff_user, staff_profile):
        """Test that staff can create when assignee is self."""
        client = APIClient()
        client.force_authenticate(user=staff_user)

        contract = Contract.objects.create(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            budget_hours_total=Decimal("1000.0"),
        )
        deliverable = Deliverable.objects.create(contract=contract, name="Test")

        response = client.post(
            "/api/v1/tasks/",
            {"deliverable": deliverable.id, "title": "Test", "assignee": staff_profile.id},
            format="json",
        )
        assert response.status_code == 201

    def test_staff_cannot_create_with_assignee_other(self, staff_user, staff_profile):
        """Test that staff cannot create when assignee is another staff."""
        client = APIClient()
        client.force_authenticate(user=staff_user)

        contract = Contract.objects.create(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            budget_hours_total=Decimal("1000.0"),
        )
        deliverable = Deliverable.objects.create(contract=contract, name="Test")

        response = client.post(
            "/api/v1/tasks/",
            {"deliverable": deliverable.id, "title": "Test", "assignee": 999},
            format="json",
        )
        assert response.status_code == 403

    def test_staff_cannot_create_with_invalid_assignee_type(self, staff_user, staff_profile):
        """Test that staff cannot create when assignee is invalid type (lines 68-69)."""
        client = APIClient()
        client.force_authenticate(user=staff_user)

        contract = Contract.objects.create(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            budget_hours_total=Decimal("1000.0"),
        )
        deliverable = Deliverable.objects.create(contract=contract, name="Test")

        # Try with invalid assignee type (dict instead of int)
        response = client.post(
            "/api/v1/tasks/",
            {"deliverable": deliverable.id, "title": "Test", "assignee": {"invalid": "type"}},
            format="json",
        )
        assert response.status_code == 403


@pytest.mark.django_db
class TestHasStaffProfile:
    """Test HasStaffProfile permission."""

    def test_unauthenticated_user_allowed(self, request_factory):
        """Test that unauthenticated users are allowed (IsAuthenticated handles this)."""
        request = request_factory.get("/api/v1/tasks/")
        request.user = None

        permission = HasStaffProfile()
        assert permission.has_permission(request, None) is True

    def test_user_without_staff_profile_raises_permission_denied(self, request_factory):
        """Test that user without staff profile raises PermissionDenied."""
        user = User.objects.create_user(username="no_staff", password="test123")
        request = request_factory.get("/api/v1/tasks/")
        request.user = user

        permission = HasStaffProfile()
        with pytest.raises(PermissionDenied):
            permission.has_permission(request, None)

    def test_user_with_staff_profile_allowed(self, request_factory, staff_user, staff_profile):
        """Test that user with staff profile is allowed."""
        request = request_factory.get("/api/v1/tasks/")
        request.user = staff_user

        permission = HasStaffProfile()
        assert permission.has_permission(request, None) is True


@pytest.mark.django_db
class TestReadAllWriteAdminOnly:
    """Test ReadAllWriteAdminOnly permission."""

    def test_read_allowed_for_all(self, request_factory, staff_user, staff_profile):
        """Test that read operations are allowed for all."""
        request = request_factory.get("/api/v1/staff/")
        request.user = staff_user

        permission = ReadAllWriteAdminOnly()
        assert permission.has_permission(request, None) is True

    def test_write_denied_for_non_admin(self, request_factory, staff_user, staff_profile):
        """Test that write operations are denied for non-admin."""
        request = request_factory.post("/api/v1/staff/", {})
        request.user = staff_user

        permission = ReadAllWriteAdminOnly()
        assert permission.has_permission(request, None) is False

    def test_write_allowed_for_admin(self, request_factory, admin_user, admin_profile):
        """Test that write operations are allowed for admin."""
        request = request_factory.post("/api/v1/staff/", {})
        request.user = admin_user

        permission = ReadAllWriteAdminOnly()
        assert permission.has_permission(request, None) is True


@pytest.mark.django_db
class TestCanEditTaskAsStaff:
    """Test CanEditTaskAsStaff permission."""

    def test_read_operations_allowed(self, request_factory, staff_user, staff_profile):
        """Test that read operations (GET, HEAD, OPTIONS) are allowed."""

        # Test GET
        request = request_factory.get("/api/v1/tasks/1/")
        request.user = staff_user
        permission = CanEditTaskAsStaff()
        assert permission.has_object_permission(request, None, None) is True

        # Test HEAD
        request = request_factory.head("/api/v1/tasks/1/")
        request.user = staff_user
        assert permission.has_object_permission(request, None, None) is True

        # Test OPTIONS
        request = request_factory.options("/api/v1/tasks/1/")
        request.user = staff_user
        assert permission.has_object_permission(request, None, None) is True

    def test_user_without_staff_profile_denied(self, request_factory):
        """Test that user without staff profile is denied for write operations."""

        user = User.objects.create_user(username="no_staff", password="test123")
        request = request_factory.patch("/api/v1/tasks/1/", {})
        request.user = user

        permission = CanEditTaskAsStaff()
        assert permission.has_object_permission(request, None, None) is False


@pytest.mark.django_db
class TestIsOwnTimeEntryOrPrivileged:
    """Test IsOwnTimeEntryOrPrivileged permission."""

    def test_read_operations_allowed(self, request_factory, staff_user, staff_profile):
        """Test that read operations (GET, HEAD, OPTIONS) are allowed."""
        from core.api.v1.permissions import IsOwnTimeEntryOrPrivileged

        # Test GET
        request = request_factory.get("/api/v1/time-entries/1/")
        request.user = staff_user
        permission = IsOwnTimeEntryOrPrivileged()
        assert permission.has_object_permission(request, None, None) is True

        # Test HEAD
        request = request_factory.head("/api/v1/time-entries/1/")
        request.user = staff_user
        assert permission.has_object_permission(request, None, None) is True

        # Test OPTIONS
        request = request_factory.options("/api/v1/time-entries/1/")
        request.user = staff_user
        assert permission.has_object_permission(request, None, None) is True

    def test_user_without_staff_profile_denied(self, request_factory):
        """Test that user without staff profile is denied for write operations."""
        from core.api.v1.permissions import IsOwnTimeEntryOrPrivileged

        user = User.objects.create_user(username="no_staff", password="test123")
        request = request_factory.patch("/api/v1/time-entries/1/", {})
        request.user = user

        # Create a mock time entry object
        class MockTimeEntry:
            staff_id = 999

        permission = IsOwnTimeEntryOrPrivileged()
        assert permission.has_object_permission(request, None, MockTimeEntry()) is False

    def test_manager_can_edit_any_time_entry(self, request_factory):
        """Test that managers can edit any time entry."""
        from core.api.v1.permissions import IsOwnTimeEntryOrPrivileged

        user = User.objects.create_user(username="manager", password="test123")
        _ = Staff.objects.create(user=user, email="manager@example.com", role="manager")
        request = request_factory.patch("/api/v1/time-entries/1/", {})
        request.user = user

        # Create a mock time entry object owned by someone else
        class MockTimeEntry:
            staff_id = 999

        permission = IsOwnTimeEntryOrPrivileged()
        assert permission.has_object_permission(request, None, MockTimeEntry()) is True


@pytest.mark.django_db
class TestIsManagerOrAdmin:
    """Test IsManagerOrAdmin permission."""

    def test_manager_allowed(self, request_factory):
        """Test that managers are allowed."""
        from core.api.v1.permissions import IsManagerOrAdmin

        user = User.objects.create_user(username="manager", password="test123")
        _ = Staff.objects.create(user=user, email="manager@example.com", role="manager")
        request = request_factory.get("/api/v1/staff/")
        request.user = user

        permission = IsManagerOrAdmin()
        assert permission.has_permission(request, None) is True

    def test_admin_allowed(self, request_factory, admin_user, admin_profile):
        """Test that admins are allowed."""
        from core.api.v1.permissions import IsManagerOrAdmin

        request = request_factory.get("/api/v1/staff/")
        request.user = admin_user

        permission = IsManagerOrAdmin()
        assert permission.has_permission(request, None) is True

    def test_staff_denied(self, request_factory, staff_user, staff_profile):
        """Test that regular staff are denied."""
        from core.api.v1.permissions import IsManagerOrAdmin

        request = request_factory.get("/api/v1/staff/")
        request.user = staff_user

        permission = IsManagerOrAdmin()
        assert permission.has_permission(request, None) is False


@pytest.mark.django_db
class TestIsStaffOrAbove:
    """Test IsStaffOrAbove permission."""

    def test_all_authenticated_users_allowed(self, request_factory, staff_user, staff_profile):
        """Test that all authenticated users with staff profile are allowed."""
        from core.api.v1.permissions import IsStaffOrAbove

        request = request_factory.get("/api/v1/tasks/")
        request.user = staff_user

        permission = IsStaffOrAbove()
        assert permission.has_permission(request, None) is True
