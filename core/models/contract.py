from datetime import date
from decimal import Decimal
from math import ceil

from django.core.validators import MinValueValidator
from django.db import models


class Contract(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        CLOSED = "closed", "Closed"

    start_date = models.DateField()
    end_date = models.DateField()
    budget_hours_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Contract #{self.pk} ({self.start_date} → {self.end_date})"

    # Rollup metrics - computed fields (read-only)

    def get_expected_hours_total(self) -> Decimal:
        """Sum of all deliverables' expected hours."""
        total = Decimal("0")
        for deliverable in self.deliverables.all():
            total += deliverable.get_expected_hours_total()
        return total

    def get_actual_hours_total(self) -> Decimal:
        """Sum of all deliverables' actual hours."""
        total = Decimal("0")
        for deliverable in self.deliverables.all():
            total += deliverable.get_actual_hours_total()
        return total

    def get_planned_weeks(self) -> int:
        """
        Number of planned weeks for this contract.
        Uses contract start_date and end_date.
        Minimum is 1 week.
        """
        days = (self.end_date - self.start_date).days + 1
        return max(1, ceil(days / 7))

    def get_elapsed_weeks(self) -> int:
        """
        Number of elapsed weeks from start to today (capped at planned end).
        Minimum is 1 week.
        """
        today = date.today()
        actual_end = min(today, self.end_date)

        # If we haven't started yet, return 1
        if today < self.start_date:
            return 1

        days = (actual_end - self.start_date).days + 1
        return max(1, ceil(days / 7))

    def get_expected_hours_per_week(self) -> Decimal:
        """Expected hours divided by planned weeks."""
        planned_weeks = self.get_planned_weeks()
        expected_total = self.get_expected_hours_total()
        return expected_total / Decimal(str(planned_weeks))

    def get_actual_hours_per_week(self) -> Decimal:
        """Actual hours divided by elapsed weeks."""
        elapsed_weeks = self.get_elapsed_weeks()
        actual_total = self.get_actual_hours_total()
        return actual_total / Decimal(str(elapsed_weeks))

    def get_remaining_budget_hours(self) -> Decimal:
        """Budget hours remaining (budget - actual)."""
        return self.budget_hours_total - self.get_actual_hours_total()

    # Health flags

    def is_over_budget(self) -> bool:
        """True if actual hours exceed budget."""
        return self.get_actual_hours_total() > self.budget_hours_total

    def is_over_expected(self) -> bool:
        """True if actual hours exceed expected hours."""
        return self.get_actual_hours_total() > self.get_expected_hours_total()
