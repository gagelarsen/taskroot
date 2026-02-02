from datetime import date
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from core.models import Contract, Deliverable, DeliverableStatusUpdate, DeliverableTimeEntry, Staff


@pytest.mark.django_db
def test_time_entry_hours_must_be_positive():
    staff = Staff.objects.create(email="a@example.com", first_name="A", last_name="User")
    contract = Contract.objects.create(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        budget_hours_total=Decimal("10.0"),
        status=Contract.Status.ACTIVE,
    )
    deliverable = Deliverable.objects.create(contract=contract, name="D1")

    te = DeliverableTimeEntry(deliverable=deliverable, staff=staff, entry_date=date(2026, 2, 1), hours=Decimal("0"))
    with pytest.raises(ValidationError):
        te.full_clean()


@pytest.mark.django_db
def test_unique_status_update_by_deliverable_period_end():
    staff = Staff.objects.create(email="b@example.com", first_name="B", last_name="User")
    contract = Contract.objects.create(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        budget_hours_total=Decimal("10.0"),
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
