from decimal import Decimal

from core.models import Deliverable


def test_get_actual_burn_rate_returns_zero_when_entries_have_total_but_no_first_last():
    class FakeOrderedQuerySet:
        def first(self):
            return None

    class FakeEntriesQuerySet:
        def aggregate(self, **kwargs):
            return {"total": Decimal("5")}

        def order_by(self, *args, **kwargs):
            return FakeOrderedQuerySet()

    class FakeTimeEntriesManager:
        def filter(self, **kwargs):
            return FakeEntriesQuerySet()

    class FakeDeliverable:
        time_entries = FakeTimeEntriesManager()

    result = Deliverable.get_actual_burn_rate(FakeDeliverable(), weeks=4)
    assert result == Decimal("0")
