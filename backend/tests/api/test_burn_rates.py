"""Tests for burn rate calculations on contracts and deliverables."""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.contrib.auth.models import User

from core.models import (
    Contract,
    Deliverable,
    DeliverableAssignment,
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
        role="admin",
    )


@pytest.fixture
def contract(db):
    """Create a contract with known dates."""
    return Contract.objects.create(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        budget_hours=Decimal("1000"),
        status="active",
    )


@pytest.fixture
def deliverable(contract):
    """Create a deliverable."""
    return Deliverable.objects.create(
        contract=contract,
        name="Test Deliverable",
        budget_hours=Decimal("500"),
        status="in_progress",
    )


@pytest.fixture
def staff_member(db):
    """Create a staff member for assignments."""
    user = User.objects.create_user(username="staff1", password="staff123")
    return Staff.objects.create(
        user=user,
        email="staff1@example.com",
        first_name="Staff",
        last_name="Member",
        role="staff",
    )


@pytest.mark.django_db
class TestDeliverableBurnRates:
    """Test burn rate calculations for deliverables."""

    def test_estimated_burn_rate_from_assignments(self, deliverable, staff_member):
        """Estimated burn rate should equal sum of assignment budget_hours."""
        DeliverableAssignment.objects.create(
            deliverable=deliverable,
            staff=staff_member,
            budget_hours=Decimal("20"),  # 20 hours per week
            is_lead=True,
        )

        assert deliverable.get_estimated_burn_rate() == Decimal("20")

    def test_estimated_burn_rate_with_no_assignments(self, deliverable):
        """Estimated burn rate should be 0 when no assignments exist."""
        assert deliverable.get_estimated_burn_rate() == Decimal("0")

    def test_actual_burn_rate_from_time_entries(self, deliverable):
        """Actual burn rate should calculate average hours per week from recent entries."""
        today = date.today()

        # Add time entries over 2 weeks (14 days)
        # Week 1: 40 hours
        DeliverableTimeEntry.objects.create(
            deliverable=deliverable,
            entry_date=today - timedelta(days=13),
            hours=Decimal("20"),
        )
        DeliverableTimeEntry.objects.create(
            deliverable=deliverable,
            entry_date=today - timedelta(days=10),
            hours=Decimal("20"),
        )

        # Week 2: 30 hours
        DeliverableTimeEntry.objects.create(
            deliverable=deliverable,
            entry_date=today - timedelta(days=6),
            hours=Decimal("15"),
        )
        DeliverableTimeEntry.objects.create(
            deliverable=deliverable,
            entry_date=today - timedelta(days=3),
            hours=Decimal("15"),
        )

        # Total: 70 hours over 2 weeks = 35 hours/week
        burn_rate = deliverable.get_actual_burn_rate(weeks=4)
        assert burn_rate == Decimal("35")

    def test_actual_burn_rate_with_no_entries(self, deliverable):
        """Actual burn rate should be 0 when no time entries exist."""
        assert deliverable.get_actual_burn_rate(weeks=4) == Decimal("0")

    def test_actual_burn_rate_with_old_entries_only(self, deliverable):
        """Actual burn rate should be 0 when entries are outside lookback period."""
        old_date = date.today() - timedelta(days=60)  # 60 days ago (outside 4-week window)

        DeliverableTimeEntry.objects.create(
            deliverable=deliverable,
            entry_date=old_date,
            hours=Decimal("100"),
        )

        # Should return 0 because entry is outside the 4-week lookback
        assert deliverable.get_actual_burn_rate(weeks=4) == Decimal("0")


@pytest.mark.django_db
class TestContractBurnRates:
    """Test burn rate calculations for contracts."""

    def test_estimated_burn_rate_rolls_up_deliverables(self, contract, staff_member):
        """Contract estimated burn rate should sum all deliverable burn rates."""
        d1 = Deliverable.objects.create(
            contract=contract,
            name="Deliverable 1",
            budget_hours=Decimal("300"),
        )
        d2 = Deliverable.objects.create(
            contract=contract,
            name="Deliverable 2",
            budget_hours=Decimal("200"),
        )

        # D1: 20 hours/week
        DeliverableAssignment.objects.create(
            deliverable=d1,
            staff=staff_member,
            budget_hours=Decimal("20"),
        )

        # D2: 15 hours/week
        DeliverableAssignment.objects.create(
            deliverable=d2,
            staff=staff_member,
            budget_hours=Decimal("15"),
        )

        # Total: 35 hours/week
        assert contract.get_estimated_burn_rate() == Decimal("35")

    def test_actual_burn_rate_rolls_up_deliverables(self, contract):
        """Contract actual burn rate should sum all deliverable burn rates."""
        d1 = Deliverable.objects.create(
            contract=contract,
            name="Deliverable 1",
            budget_hours=Decimal("300"),
        )
        d2 = Deliverable.objects.create(
            contract=contract,
            name="Deliverable 2",
            budget_hours=Decimal("200"),
        )

        today = date.today()

        # D1: 40 hours over 2 weeks = 20 hours/week
        DeliverableTimeEntry.objects.create(
            deliverable=d1,
            entry_date=today - timedelta(days=10),
            hours=Decimal("20"),
        )
        DeliverableTimeEntry.objects.create(
            deliverable=d1,
            entry_date=today - timedelta(days=3),
            hours=Decimal("20"),
        )

        # D2: 30 hours over 2 weeks = 15 hours/week
        DeliverableTimeEntry.objects.create(
            deliverable=d2,
            entry_date=today - timedelta(days=10),
            hours=Decimal("15"),
        )
        DeliverableTimeEntry.objects.create(
            deliverable=d2,
            entry_date=today - timedelta(days=3),
            hours=Decimal("15"),
        )

        # Total: 35 hours/week
        burn_rate = contract.get_actual_burn_rate(weeks=4)
        assert burn_rate == Decimal("35")
