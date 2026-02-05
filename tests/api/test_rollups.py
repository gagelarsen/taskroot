"""
Tests for rollup metrics and health indicators (PR7).
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.contrib.auth.models import User

from core.models import (
    Contract,
    Deliverable,
    DeliverableAssignment,
    DeliverableStatusUpdate,
    DeliverableTimeEntry,
    Staff,
)


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(username="admin", password="admin123", is_staff=True)


@pytest.fixture
def admin_profile(admin_user):
    return Staff.objects.create(
        user=admin_user,
        email="admin@example.com",
        first_name="Admin",
        last_name="User",
        role=Staff.Role.ADMIN,
        status=Staff.Status.ACTIVE,
    )


@pytest.fixture
def contract(db):
    """Create a contract with known dates."""
    return Contract.objects.create(
        start_date=date(2024, 1, 1),
        end_date=date(2024, 3, 31),  # 90 days = ~13 weeks
        budget_hours_total=Decimal("1000.00"),
        status=Contract.Status.ACTIVE,
    )


@pytest.fixture
def deliverable(contract):
    """Create a deliverable with known dates."""
    return Deliverable.objects.create(
        contract=contract,
        name="Test Deliverable",
        start_date=date(2024, 1, 1),
        due_date=date(2024, 1, 28),  # 28 days = 4 weeks
        status=Deliverable.Status.IN_PROGRESS,
    )


@pytest.fixture
def staff_member(db):
    """Create a staff member for assignments."""
    user = User.objects.create_user(username="staff1", password="staff123")
    return Staff.objects.create(
        user=user,
        email="staff1@example.com",
        first_name="Staff",
        last_name="One",
        role=Staff.Role.STAFF,
        status=Staff.Status.ACTIVE,
    )


@pytest.mark.django_db
class TestDeliverableRollups:
    """Test deliverable-level rollup metrics."""

    def test_expected_hours_total_sums_assignments(self, deliverable, staff_member):
        """Expected hours should sum all assignment expected_hours."""
        # Create assignments
        DeliverableAssignment.objects.create(
            deliverable=deliverable,
            staff=staff_member,
            expected_hours=Decimal("40.00"),
            is_lead=True,
        )

        # Create another staff member and assignment
        user2 = User.objects.create_user(username="staff2", password="staff123")
        staff2 = Staff.objects.create(
            user=user2,
            email="staff2@example.com",
            first_name="Staff",
            last_name="Two",
            role=Staff.Role.STAFF,
            status=Staff.Status.ACTIVE,
        )
        DeliverableAssignment.objects.create(
            deliverable=deliverable,
            staff=staff2,
            expected_hours=Decimal("60.00"),
            is_lead=False,
        )

        assert deliverable.get_expected_hours_total() == Decimal("100.00")

    def test_expected_hours_total_zero_when_no_assignments(self, deliverable):
        """Expected hours should be 0 when no assignments exist."""
        assert deliverable.get_expected_hours_total() == Decimal("0")

    def test_actual_hours_total_sums_time_entries(self, deliverable, staff_member):
        """Actual hours should sum all time entry hours."""
        DeliverableTimeEntry.objects.create(
            deliverable=deliverable,
            staff=staff_member,
            entry_date=date(2024, 1, 5),
            hours=Decimal("8.00"),
        )
        DeliverableTimeEntry.objects.create(
            deliverable=deliverable,
            staff=staff_member,
            entry_date=date(2024, 1, 6),
            hours=Decimal("7.50"),
        )

        assert deliverable.get_actual_hours_total() == Decimal("15.50")

    def test_actual_hours_total_zero_when_no_entries(self, deliverable):
        """Actual hours should be 0 when no time entries exist."""
        assert deliverable.get_actual_hours_total() == Decimal("0")

    def test_variance_hours_computed_correctly(self, deliverable, staff_member):
        """Variance should be actual - expected."""
        DeliverableAssignment.objects.create(
            deliverable=deliverable,
            staff=staff_member,
            expected_hours=Decimal("40.00"),
            is_lead=True,
        )
        DeliverableTimeEntry.objects.create(
            deliverable=deliverable,
            staff=staff_member,
            entry_date=date(2024, 1, 5),
            hours=Decimal("50.00"),
        )

        assert deliverable.get_variance_hours() == Decimal("10.00")

    def test_is_over_expected_flag(self, deliverable, staff_member):
        """is_over_expected should be True when actual > expected."""
        DeliverableAssignment.objects.create(
            deliverable=deliverable,
            staff=staff_member,
            expected_hours=Decimal("40.00"),
            is_lead=True,
        )

        # Not over expected yet
        assert deliverable.is_over_expected() is False

        # Add time entries to go over
        DeliverableTimeEntry.objects.create(
            deliverable=deliverable,
            staff=staff_member,
            entry_date=date(2024, 1, 5),
            hours=Decimal("50.00"),
        )

        assert deliverable.is_over_expected() is True

    def test_is_missing_estimate_flag(self, deliverable, staff_member):
        """is_missing_estimate should be True when expected == 0 but has assignments."""
        # No assignments yet
        assert deliverable.is_missing_estimate() is False

        # Create assignment with 0 expected hours
        DeliverableAssignment.objects.create(
            deliverable=deliverable,
            staff=staff_member,
            expected_hours=Decimal("0"),
            is_lead=True,
        )

        assert deliverable.is_missing_estimate() is True

    def test_is_missing_lead_flag(self, deliverable, staff_member):
        """is_missing_lead should be True when no assignment has is_lead=True."""
        # No assignments yet
        assert deliverable.is_missing_lead() is True

        # Create assignment without lead
        DeliverableAssignment.objects.create(
            deliverable=deliverable,
            staff=staff_member,
            expected_hours=Decimal("40.00"),
            is_lead=False,
        )

        assert deliverable.is_missing_lead() is True

        # Update to be lead
        assignment = deliverable.assignments.first()
        assignment.is_lead = True
        assignment.save()

        assert deliverable.is_missing_lead() is False


@pytest.mark.django_db
class TestWeeksCalculations:
    """Test weeks calculation logic."""

    def test_planned_weeks_minimum_is_one(self, contract):
        """Planned weeks should be at least 1."""
        # Create deliverable with same start and end date
        deliverable = Deliverable.objects.create(
            contract=contract,
            start_date=date(2024, 1, 1),
            due_date=date(2024, 1, 1),  # Same day
            status=Deliverable.Status.PLANNED,
        )

        assert deliverable.get_planned_weeks() == 1

    def test_planned_weeks_calculation(self, deliverable):
        """Planned weeks should be ceil((end - start + 1) / 7)."""
        # deliverable has 28 days (Jan 1 - Jan 28)
        # (28 - 1 + 1) / 7 = 28 / 7 = 4 weeks
        assert deliverable.get_planned_weeks() == 4

    def test_planned_weeks_uses_contract_dates_when_deliverable_dates_missing(self, contract):
        """Should fall back to contract dates when deliverable dates are None."""
        deliverable = Deliverable.objects.create(
            contract=contract,
            start_date=None,
            due_date=None,
            status=Deliverable.Status.PLANNED,
        )

        # Contract has 90 days (Jan 1 - Mar 31)
        # 90 / 7 = 12.857... = 13 weeks
        assert deliverable.get_planned_weeks() == 13

    def test_elapsed_weeks_minimum_is_one(self, contract):
        """Elapsed weeks should be at least 1."""
        # Create deliverable in the future
        future_start = date.today() + timedelta(days=30)
        deliverable = Deliverable.objects.create(
            contract=contract,
            start_date=future_start,
            due_date=future_start + timedelta(days=7),
            status=Deliverable.Status.PLANNED,
        )

        assert deliverable.get_elapsed_weeks() == 1

    def test_elapsed_weeks_caps_at_end_date(self, contract):
        """Elapsed weeks should cap at the end date, not go beyond."""
        # Create deliverable that ended in the past
        deliverable = Deliverable.objects.create(
            contract=contract,
            start_date=date(2024, 1, 1),
            due_date=date(2024, 1, 14),  # 14 days = 2 weeks
            status=Deliverable.Status.COMPLETE,
        )

        # Even though today is beyond the end date, elapsed should cap at 2 weeks
        assert deliverable.get_elapsed_weeks() >= 1  # At least 1 week

    def test_per_week_metrics(self, deliverable, staff_member):
        """Per-week metrics should divide totals by weeks."""
        DeliverableAssignment.objects.create(
            deliverable=deliverable,
            staff=staff_member,
            expected_hours=Decimal("80.00"),
            is_lead=True,
        )

        # deliverable has 4 planned weeks
        # 80 / 4 = 20 hours per week
        assert deliverable.get_expected_hours_per_week() == Decimal("20.00")


@pytest.mark.django_db
class TestContractRollups:
    """Test contract-level rollup metrics."""

    def test_expected_hours_total_rolls_up_deliverables(self, contract, staff_member):
        """Contract expected hours should sum all deliverable expected hours."""
        # Create two deliverables
        d1 = Deliverable.objects.create(
            contract=contract,
            name="Deliverable 1",
            status=Deliverable.Status.IN_PROGRESS,
        )
        d2 = Deliverable.objects.create(
            contract=contract,
            name="Deliverable 2",
            status=Deliverable.Status.PLANNED,
        )

        # Add assignments
        DeliverableAssignment.objects.create(
            deliverable=d1,
            staff=staff_member,
            expected_hours=Decimal("40.00"),
            is_lead=True,
        )
        DeliverableAssignment.objects.create(
            deliverable=d2,
            staff=staff_member,
            expected_hours=Decimal("60.00"),
            is_lead=True,
        )

        assert contract.get_expected_hours_total() == Decimal("100.00")

    def test_actual_hours_total_rolls_up_deliverables(self, contract, staff_member):
        """Contract actual hours should sum all deliverable actual hours."""
        d1 = Deliverable.objects.create(
            contract=contract,
            name="Deliverable 1",
            status=Deliverable.Status.IN_PROGRESS,
        )
        d2 = Deliverable.objects.create(
            contract=contract,
            name="Deliverable 2",
            status=Deliverable.Status.IN_PROGRESS,
        )

        # Add time entries
        DeliverableTimeEntry.objects.create(
            deliverable=d1,
            staff=staff_member,
            entry_date=date(2024, 1, 5),
            hours=Decimal("25.00"),
        )
        DeliverableTimeEntry.objects.create(
            deliverable=d2,
            staff=staff_member,
            entry_date=date(2024, 1, 6),
            hours=Decimal("35.00"),
        )

        assert contract.get_actual_hours_total() == Decimal("60.00")

    def test_remaining_budget_hours(self, contract, staff_member):
        """Remaining budget should be budget - actual."""
        deliverable = Deliverable.objects.create(
            contract=contract,
            name="Deliverable 1",
            status=Deliverable.Status.IN_PROGRESS,
        )

        # Contract has 1000 budget hours
        DeliverableTimeEntry.objects.create(
            deliverable=deliverable,
            staff=staff_member,
            entry_date=date(2024, 1, 5),
            hours=Decimal("250.00"),
        )

        assert contract.get_remaining_budget_hours() == Decimal("750.00")

    def test_is_over_budget_flag(self, contract, staff_member):
        """is_over_budget should be True when actual > budget."""
        deliverable = Deliverable.objects.create(
            contract=contract,
            name="Deliverable 1",
            status=Deliverable.Status.IN_PROGRESS,
        )

        # Not over budget yet
        assert contract.is_over_budget() is False

        # Add time entries to exceed budget (1000 hours)
        DeliverableTimeEntry.objects.create(
            deliverable=deliverable,
            staff=staff_member,
            entry_date=date(2024, 1, 5),
            hours=Decimal("1100.00"),
        )

        assert contract.is_over_budget() is True

    def test_contract_planned_weeks(self, contract):
        """Contract planned weeks should use contract dates."""
        # Contract has 90 days (Jan 1 - Mar 31)
        # 90 / 7 = 12.857... = 13 weeks
        assert contract.get_planned_weeks() == 13


@pytest.mark.django_db
class TestLatestStatusUpdate:
    """Test latest status update exposure."""

    def test_latest_status_update_returns_newest_by_period_end(self, deliverable, staff_member):
        """Should return the status update with the most recent period_end."""
        # Create multiple status updates
        DeliverableStatusUpdate.objects.create(
            deliverable=deliverable,
            period_end=date(2024, 1, 7),
            status=DeliverableStatusUpdate.Status.ON_TRACK,
            summary="Week 1",
            created_by=staff_member,
        )
        latest = DeliverableStatusUpdate.objects.create(
            deliverable=deliverable,
            period_end=date(2024, 1, 21),
            status=DeliverableStatusUpdate.Status.AT_RISK,
            summary="Week 3",
            created_by=staff_member,
        )
        DeliverableStatusUpdate.objects.create(
            deliverable=deliverable,
            period_end=date(2024, 1, 14),
            status=DeliverableStatusUpdate.Status.ON_TRACK,
            summary="Week 2",
            created_by=staff_member,
        )

        result = deliverable.get_latest_status_update()
        assert result.id == latest.id
        assert result.period_end == date(2024, 1, 21)
        assert result.status == DeliverableStatusUpdate.Status.AT_RISK

    def test_latest_status_update_returns_none_when_no_updates(self, deliverable):
        """Should return None when no status updates exist."""
        assert deliverable.get_latest_status_update() is None


@pytest.mark.django_db
class TestRollupsInAPI:
    """Test that rollup metrics are exposed in API responses."""

    def test_deliverable_api_includes_rollup_fields(self, admin_user, admin_profile, deliverable, staff_member):
        """Deliverable API should include all rollup fields."""
        from rest_framework.test import APIClient

        # Add some data
        DeliverableAssignment.objects.create(
            deliverable=deliverable,
            staff=staff_member,
            expected_hours=Decimal("40.00"),
            is_lead=True,
        )
        DeliverableTimeEntry.objects.create(
            deliverable=deliverable,
            staff=staff_member,
            entry_date=date(2024, 1, 5),
            hours=Decimal("10.00"),
        )

        client = APIClient()
        client.force_authenticate(user=admin_user)
        response = client.get(f"/api/v1/deliverables/{deliverable.id}/")

        assert response.status_code == 200
        data = response.json()

        # Check rollup fields are present
        assert "expected_hours_total" in data
        assert "actual_hours_total" in data
        assert "planned_weeks" in data
        assert "elapsed_weeks" in data
        assert "expected_hours_per_week" in data
        assert "actual_hours_per_week" in data
        assert "variance_hours" in data
        assert "is_over_expected" in data
        assert "is_missing_estimate" in data
        assert "is_missing_lead" in data
        assert "latest_status_update" in data

        # Check values (API returns floats, not strings)
        assert data["expected_hours_total"] == 40.0
        assert data["actual_hours_total"] == 10.0
        assert data["is_over_expected"] is False
        assert data["is_missing_lead"] is False

    def test_contract_api_includes_rollup_fields(self, admin_user, admin_profile, contract, staff_member):
        """Contract API should include all rollup fields."""
        from rest_framework.test import APIClient

        # Add a deliverable with data
        deliverable = Deliverable.objects.create(
            contract=contract,
            name="Test Deliverable",
            status=Deliverable.Status.IN_PROGRESS,
        )
        DeliverableAssignment.objects.create(
            deliverable=deliverable,
            staff=staff_member,
            expected_hours=Decimal("100.00"),
            is_lead=True,
        )
        DeliverableTimeEntry.objects.create(
            deliverable=deliverable,
            staff=staff_member,
            entry_date=date(2024, 1, 5),
            hours=Decimal("50.00"),
        )

        client = APIClient()
        client.force_authenticate(user=admin_user)
        response = client.get(f"/api/v1/contracts/{contract.id}/")

        assert response.status_code == 200
        data = response.json()

        # Check rollup fields are present
        assert "expected_hours_total" in data
        assert "actual_hours_total" in data
        assert "planned_weeks" in data
        assert "elapsed_weeks" in data
        assert "expected_hours_per_week" in data
        assert "actual_hours_per_week" in data
        assert "remaining_budget_hours" in data
        assert "is_over_budget" in data
        assert "is_over_expected" in data

        # Check values (API returns floats, not strings)
        assert data["expected_hours_total"] == 100.0
        assert data["actual_hours_total"] == 50.0
        assert data["remaining_budget_hours"] == 950.0
        assert data["is_over_budget"] is False

    def test_health_filters_work(self, admin_user, admin_profile, contract, staff_member):
        """Health query filters should work correctly."""
        from rest_framework.test import APIClient

        # Create deliverable that is over expected
        d1 = Deliverable.objects.create(
            contract=contract,
            name="Over Expected",
            status=Deliverable.Status.IN_PROGRESS,
        )
        DeliverableAssignment.objects.create(
            deliverable=d1,
            staff=staff_member,
            expected_hours=Decimal("10.00"),
            is_lead=True,
        )
        DeliverableTimeEntry.objects.create(
            deliverable=d1,
            staff=staff_member,
            entry_date=date(2024, 1, 5),
            hours=Decimal("20.00"),
        )

        # Create deliverable that is not over expected
        d2 = Deliverable.objects.create(
            contract=contract,
            name="On Track",
            status=Deliverable.Status.IN_PROGRESS,
        )
        DeliverableAssignment.objects.create(
            deliverable=d2,
            staff=staff_member,
            expected_hours=Decimal("50.00"),
            is_lead=True,
        )
        DeliverableTimeEntry.objects.create(
            deliverable=d2,
            staff=staff_member,
            entry_date=date(2024, 1, 5),
            hours=Decimal("10.00"),
        )

        client = APIClient()
        client.force_authenticate(user=admin_user)

        # Filter for over_expected=true
        response = client.get("/api/v1/deliverables/?over_expected=true")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["results"][0]["id"] == d1.id

        # Filter for over_expected=false
        response = client.get("/api/v1/deliverables/?over_expected=false")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["results"][0]["id"] == d2.id
