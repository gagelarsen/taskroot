"""
Tests for filter edge cases and helper functions.
"""

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient

from core.api.v1.filters import _parse_bool
from core.models import Contract, Deliverable, DeliverableAssignment, Staff


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
        start_date=date(2024, 1, 1),
        end_date=date(2024, 12, 31),
        budget_hours=Decimal("1000.0"),
        status="active",
    )


@pytest.fixture
def deliverable(contract):
    """Create a test deliverable."""
    return Deliverable.objects.create(
        contract=contract,
        name="Test Deliverable",
        status="in_progress",
        start_date=date(2024, 1, 1),
        due_date=date(2024, 6, 30),
    )


@pytest.fixture
def staff(db):
    """Create a test staff member."""
    user = User.objects.create_user(username="staff1", password="staff123")
    return Staff.objects.create(user=user, email="staff1@example.com", role="staff")


class TestParseBool:
    """Test the _parse_bool helper function."""

    def test_parse_bool_true_values(self):
        """Test parsing true values."""
        assert _parse_bool("true") is True
        assert _parse_bool("True") is True
        assert _parse_bool("TRUE") is True
        assert _parse_bool("1") is True
        assert _parse_bool("yes") is True
        assert _parse_bool("YES") is True

    def test_parse_bool_false_values(self):
        """Test parsing false values."""
        assert _parse_bool("false") is False
        assert _parse_bool("False") is False
        assert _parse_bool("FALSE") is False
        assert _parse_bool("0") is False
        assert _parse_bool("no") is False
        assert _parse_bool("NO") is False

    def test_parse_bool_none(self):
        """Test parsing None."""
        assert _parse_bool(None) is None

    def test_parse_bool_invalid_values(self):
        """Test parsing invalid values returns None."""
        assert _parse_bool("invalid") is None
        assert _parse_bool("maybe") is None
        assert _parse_bool("2") is None
        assert _parse_bool("") is None


@pytest.mark.django_db
class TestContractFilters:
    """Test contract filter edge cases."""

    def test_contract_filter_over_budget_true(self, auth_client, contract, deliverable, staff):
        """Test filtering contracts that are over budget."""
        # Create time entries that exceed budget
        from core.models import DeliverableTimeEntry

        DeliverableTimeEntry.objects.create(
            deliverable=deliverable,
            entry_date=date(2024, 1, 15),
            hours=Decimal("1500.0"),  # Exceeds 1000 budget
        )

        response = auth_client.get("/api/v1/contracts/?over_budget=true")
        assert response.status_code == 200
        assert len(response.data["results"]) == 1

    def test_contract_filter_over_budget_false(self, auth_client, contract):
        """Test filtering contracts that are not over budget."""
        response = auth_client.get("/api/v1/contracts/?over_budget=false")
        assert response.status_code == 200
        assert len(response.data["results"]) == 1

    def test_contract_filter_over_expected_true(self, auth_client, contract, deliverable, staff):
        """Test filtering contracts that are over expected hours."""
        from core.models import DeliverableAssignment, DeliverableTimeEntry

        # Create assignment with expected hours
        DeliverableAssignment.objects.create(
            deliverable=deliverable,
            staff=staff,
            budget_hours=Decimal("100.0"),
            is_lead=True,
        )

        # Create time entries that exceed expected
        DeliverableTimeEntry.objects.create(
            deliverable=deliverable,
            entry_date=date(2024, 1, 15),
            hours=Decimal("150.0"),  # Exceeds 100 expected
        )

        response = auth_client.get("/api/v1/contracts/?over_expected=true")
        assert response.status_code == 200
        assert len(response.data["results"]) == 1

    def test_contract_filter_over_budget_invalid_value(self, auth_client, contract):
        """Test filtering with invalid boolean value returns all results."""
        response = auth_client.get("/api/v1/contracts/?over_budget=invalid")
        assert response.status_code == 200
        # Should return all contracts (filter ignored)
        assert len(response.data["results"]) == 1

    def test_contract_filter_over_expected_invalid_value(self, auth_client, contract):
        """Test filtering with invalid boolean value returns all results."""
        response = auth_client.get("/api/v1/contracts/?over_expected=maybe")
        assert response.status_code == 200
        # Should return all contracts (filter ignored)
        assert len(response.data["results"]) == 1

    def test_contract_filter_over_expected_false(self, auth_client, contract):
        """Test filtering contracts that are NOT over expected hours."""
        response = auth_client.get("/api/v1/contracts/?over_expected=false")
        assert response.status_code == 200
        # Should return contracts not over expected
        assert len(response.data["results"]) == 1


@pytest.mark.django_db
class TestDeliverableFilters:
    """Test deliverable filter edge cases."""

    def test_deliverable_filter_missing_lead_true(self, auth_client, contract, deliverable, staff):
        """Test filtering deliverables missing a lead."""
        # Deliverable has no assignments yet, so missing lead
        response = auth_client.get("/api/v1/deliverables/?missing_lead=true")
        assert response.status_code == 200
        assert len(response.data["results"]) == 1

    def test_deliverable_filter_missing_lead_false(self, auth_client, contract, deliverable, staff):
        """Test filtering deliverables with a lead."""
        # Add a lead assignment
        DeliverableAssignment.objects.create(
            deliverable=deliverable,
            staff=staff,
            budget_hours=Decimal("100.0"),
            is_lead=True,
        )

        response = auth_client.get("/api/v1/deliverables/?missing_lead=false")
        assert response.status_code == 200
        assert len(response.data["results"]) == 1

    def test_deliverable_filter_missing_estimate_true(self, auth_client, contract, deliverable, staff):
        """Test filtering deliverables missing estimates."""
        # Add assignment with 0 expected hours
        DeliverableAssignment.objects.create(
            deliverable=deliverable,
            staff=staff,
            budget_hours=Decimal("0.0"),
            is_lead=True,
        )

        response = auth_client.get("/api/v1/deliverables/?missing_estimate=true")
        assert response.status_code == 200
        assert len(response.data["results"]) == 1

    def test_deliverable_filter_over_expected_true(self, auth_client, contract, deliverable, staff):
        """Test filtering deliverables over expected hours."""
        from core.models import DeliverableTimeEntry

        # Add assignment with expected hours
        DeliverableAssignment.objects.create(
            deliverable=deliverable,
            staff=staff,
            budget_hours=Decimal("50.0"),
            is_lead=True,
        )

        # Add time entries exceeding expected
        DeliverableTimeEntry.objects.create(
            deliverable=deliverable,
            entry_date=date(2024, 1, 15),
            hours=Decimal("75.0"),
        )

        response = auth_client.get("/api/v1/deliverables/?over_expected=true")
        assert response.status_code == 200
        assert len(response.data["results"]) == 1

    def test_deliverable_filter_missing_lead_invalid_value(self, auth_client, contract, deliverable):
        """Test filtering with invalid boolean value returns all results."""
        response = auth_client.get("/api/v1/deliverables/?missing_lead=invalid")
        assert response.status_code == 200
        # Should return all deliverables (filter ignored)
        assert len(response.data["results"]) == 1

    def test_deliverable_filter_missing_estimate_invalid_value(self, auth_client, contract, deliverable):
        """Test filtering with invalid boolean value returns all results."""
        response = auth_client.get("/api/v1/deliverables/?missing_estimate=maybe")
        assert response.status_code == 200
        # Should return all deliverables (filter ignored)
        assert len(response.data["results"]) == 1

    def test_deliverable_filter_staff_id_empty(self, auth_client, contract, deliverable):
        """Test filtering with empty staff_id returns all results."""
        response = auth_client.get("/api/v1/deliverables/?staff_id=")
        assert response.status_code == 200
        # Should return all deliverables (filter ignored)
        assert len(response.data["results"]) == 1

    def test_deliverable_filter_lead_only_invalid_value(self, auth_client, contract, deliverable):
        """Test filtering with invalid boolean value returns all results."""
        response = auth_client.get("/api/v1/deliverables/?lead_only=invalid")
        assert response.status_code == 200
        # Should return all deliverables (filter ignored)
        assert len(response.data["results"]) == 1

    def test_deliverable_filter_has_assignments_invalid_value(self, auth_client, contract, deliverable):
        """Test filtering with invalid boolean value returns all results."""
        response = auth_client.get("/api/v1/deliverables/?has_assignments=maybe")
        assert response.status_code == 200
        # Should return all deliverables (filter ignored)
        assert len(response.data["results"]) == 1

    def test_deliverable_filter_has_assignments_true(self, auth_client, contract, deliverable, staff):
        """Test filtering deliverables that have assignments."""
        # Add an assignment
        DeliverableAssignment.objects.create(
            deliverable=deliverable,
            staff=staff,
            budget_hours=Decimal("100.0"),
            is_lead=True,
        )

        response = auth_client.get("/api/v1/deliverables/?has_assignments=true")
        assert response.status_code == 200
        assert len(response.data["results"]) == 1

    def test_deliverable_filter_over_expected_invalid_value(self, auth_client, contract, deliverable):
        """Test filtering with invalid over_expected value returns all results."""
        response = auth_client.get("/api/v1/deliverables/?over_expected=invalid")
        assert response.status_code == 200
        # Should return all deliverables (filter ignored)
        assert len(response.data["results"]) == 1

    def test_deliverable_filter_missing_estimate_false(self, auth_client, contract, deliverable, staff):
        """Test filtering deliverables that are NOT missing estimates."""
        # Add assignment with expected hours > 0
        DeliverableAssignment.objects.create(
            deliverable=deliverable,
            staff=staff,
            budget_hours=Decimal("100.0"),
            is_lead=True,
        )

        response = auth_client.get("/api/v1/deliverables/?missing_estimate=false")
        assert response.status_code == 200
        assert len(response.data["results"]) == 1


@pytest.mark.django_db
class TestTaskFilters:
    """Test task filter edge cases."""

    def test_task_filter_unassigned_true(self, auth_client, contract, deliverable):
        """Test filtering unassigned tasks."""
        from core.models import Task

        # Create unassigned task
        Task.objects.create(
            deliverable=deliverable,
            title="Unassigned Task",
            status="todo",
        )

        response = auth_client.get("/api/v1/tasks/?unassigned=true")
        assert response.status_code == 200
        assert len(response.data["results"]) == 1

    def test_task_filter_unassigned_false(self, auth_client, contract, deliverable, staff):
        """Test filtering assigned tasks."""
        from core.models import Task

        # Create assigned task
        Task.objects.create(
            deliverable=deliverable,
            title="Assigned Task",
            status="todo",
            assignee=staff,
        )

        response = auth_client.get("/api/v1/tasks/?unassigned=false")
        assert response.status_code == 200
        assert len(response.data["results"]) == 1

    def test_task_filter_unassigned_invalid_value(self, auth_client, contract, deliverable):
        """Test filtering with invalid unassigned value returns all results."""
        from core.models import Task

        Task.objects.create(
            deliverable=deliverable,
            title="Test Task",
            status="todo",
        )

        response = auth_client.get("/api/v1/tasks/?unassigned=invalid")
        assert response.status_code == 200
        # Should return all tasks (filter ignored)
        assert len(response.data["results"]) == 1


@pytest.mark.django_db
class TestAssignmentFilters:
    """Test assignment filter edge cases."""

    def test_assignment_filter_lead_only_invalid_value(self, auth_client, contract, deliverable, staff):
        """Test filtering with invalid lead_only value returns all results."""
        DeliverableAssignment.objects.create(
            deliverable=deliverable,
            staff=staff,
            budget_hours=Decimal("100.0"),
            is_lead=True,
        )

        response = auth_client.get("/api/v1/deliverable-assignments/?lead_only=invalid")
        assert response.status_code == 200
        # Should return all assignments (filter ignored)
        assert len(response.data["results"]) == 1


@pytest.mark.django_db
class TestOrderingBackend:
    """Test custom ordering backend edge cases."""

    def test_ordering_with_invalid_field(self, auth_client, contract):
        """Test ordering with invalid field is ignored."""
        response = auth_client.get("/api/v1/contracts/?order_by=invalid_field&order_dir=asc")
        assert response.status_code == 200
        # Should still return results, just not ordered by invalid field

    def test_ordering_with_invalid_direction(self, auth_client, contract):
        """Test ordering with invalid direction defaults to asc."""
        response = auth_client.get("/api/v1/contracts/?order_by=start_date&order_dir=invalid")
        assert response.status_code == 200
        # Should default to ascending

    def test_ordering_desc(self, auth_client):
        """Test descending order."""
        Contract.objects.create(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            budget_hours=Decimal("1000.0"),
        )
        Contract.objects.create(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            budget_hours=Decimal("2000.0"),
        )

        response = auth_client.get("/api/v1/contracts/?order_by=start_date&order_dir=desc")
        assert response.status_code == 200
        results = response.data["results"]
        assert len(results) == 2
        # First result should be 2025 (descending)
        assert results[0]["start_date"] == "2025-01-01"
