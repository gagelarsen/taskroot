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

    name = models.CharField(max_length=255, default="")
    client_name = models.CharField(max_length=255, default="")
    start_date = models.DateField()
    end_date = models.DateField()
    budget_hours = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(end_date__gte=models.F("start_date")),
                name="contract_end_after_start",
            ),
        ]

    def __str__(self) -> str:
        if self.name:
            return f"{self.name} (Contract #{self.pk})"
        return f"Contract #{self.pk} ({self.start_date} → {self.end_date})"

    # Rollup metrics - computed fields (read-only)

    def get_assigned_budget_hours(self) -> Decimal:
        """Sum of all deliverables' assigned budget hours (from assignments)."""
        total = Decimal("0")
        for deliverable in self.deliverables.all():
            total += deliverable.get_assigned_budget_hours()
        return total

    def get_spent_hours(self) -> Decimal:
        """Sum of all deliverables' spent hours (from time entries)."""
        total = Decimal("0")
        for deliverable in self.deliverables.all():
            total += deliverable.get_spent_hours()
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

    def get_assigned_budget_hours_per_week(self) -> Decimal:
        """Assigned budget hours divided by planned weeks."""
        planned_weeks = self.get_planned_weeks()
        assigned_budget = self.get_assigned_budget_hours()
        return assigned_budget / Decimal(str(planned_weeks))

    def get_spent_hours_per_week(self) -> Decimal:
        """Spent hours divided by elapsed weeks."""
        elapsed_weeks = self.get_elapsed_weeks()
        spent_total = self.get_spent_hours()
        return spent_total / Decimal(str(elapsed_weeks))

    def get_remaining_budget_hours(self) -> Decimal:
        """Budget hours remaining (budget - spent hours)."""
        return self.budget_hours - self.get_spent_hours()

    def get_unspent_budget_hours(self) -> Decimal:
        """Unspent budget hours (budget - spent hours). Alias for get_remaining_budget_hours()."""
        return self.get_remaining_budget_hours()

    def get_unassigned_budget_hours(self) -> Decimal:
        """Unassigned budget hours (budget - assigned budget hours)."""
        return self.budget_hours - self.get_assigned_budget_hours()

    # Health flags

    def is_over_budget(self) -> bool:
        """True if spent hours exceed budget."""
        return self.get_spent_hours() > self.budget_hours

    def is_overassigned(self) -> bool:
        """True if assigned budget hours exceed contract budget."""
        return self.get_assigned_budget_hours() > self.budget_hours

    def is_over_expected(self) -> bool:
        """True if spent hours exceed assigned budget hours (from assignments)."""
        return self.get_spent_hours() > self.get_assigned_budget_hours()
