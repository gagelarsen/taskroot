from datetime import date
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from core.models import Contract, Deliverable, DeliverableStatusUpdate, DeliverableTimeEntry, Staff


@pytest.mark.django_db
def test_time_entry_hours_must_be_positive():
    _ = Staff.objects.create(email="a@example.com", first_name="A", last_name="User")
    contract = Contract.objects.create(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        budget_hours=Decimal("10.0"),
        status=Contract.Status.ACTIVE,
    )
    deliverable = Deliverable.objects.create(contract=contract, name="D1")

    te = DeliverableTimeEntry(deliverable=deliverable, entry_date=date(2026, 2, 1), hours=Decimal("0"))
    with pytest.raises(ValidationError):
        te.full_clean()


@pytest.mark.django_db
def test_unique_status_update_by_deliverable_period_end():
    staff = Staff.objects.create(email="b@example.com", first_name="B", last_name="User")
    contract = Contract.objects.create(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        budget_hours=Decimal("10.0"),
        status=Contract.Status.ACTIVE,
    )
    deliverable = Deliverable.objects.create(contract=contract, name="D1")

    DeliverableStatusUpdate.objects.create(
        deliverable=deliverable,
        period_end=date(2026, 2, 1),
        status=DeliverableStatusUpdate.Status.ON_TRACK,
        created_by=staff,
    )

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            DeliverableStatusUpdate.objects.create(
                deliverable=deliverable,
                period_end=date(2026, 2, 1),
                status=DeliverableStatusUpdate.Status.AT_RISK,
                created_by=staff,
            )


@pytest.mark.django_db
def test_contract_end_date_must_be_after_start_date():
    """Contract end_date must be >= start_date."""
    # Valid contract
    contract = Contract.objects.create(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        budget_hours=Decimal("1000.0"),
    )
    assert contract.id is not None

    # Invalid contract (end before start)
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Contract.objects.create(
                start_date=date(2026, 12, 31),
                end_date=date(2026, 1, 1),  # Before start
                budget_hours=Decimal("1000.0"),
            )


@pytest.mark.django_db
def test_time_entry_unique_external_key():
    """Time entries with same (external_source, external_id) should be unique."""
    _ = Staff.objects.create(email="c@example.com", first_name="C", last_name="User")
    contract = Contract.objects.create(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        budget_hours=Decimal("1000.0"),
    )
    deliverable = Deliverable.objects.create(contract=contract, name="Test")

    # First entry with external key
    DeliverableTimeEntry.objects.create(
        deliverable=deliverable,
        entry_date=date(2026, 1, 15),
        hours=Decimal("8.0"),
        external_source="jira",
        external_id="PROJ-123",
    )

    # Duplicate external key should fail
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            DeliverableTimeEntry.objects.create(
                deliverable=deliverable,
                entry_date=date(2026, 1, 16),  # Different date
                hours=Decimal("6.0"),  # Different hours
                external_source="jira",
                external_id="PROJ-123",  # Same external key
            )
