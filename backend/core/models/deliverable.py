from datetime import date
from decimal import Decimal
from math import ceil

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Sum

from .contract import Contract


class Deliverable(models.Model):
    class Status(models.TextChoices):
        PLANNED = "planned", "Planned"
        IN_PROGRESS = "in_progress", "In progress"
        COMPLETE = "complete", "Complete"
        BLOCKED = "blocked", "Blocked"

    contract = models.ForeignKey(Contract, on_delete=models.PROTECT, related_name="deliverables")
    name = models.CharField(max_length=255, default="")
    budget_hours = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
        default=Decimal("0"),
    )
    start_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PLANNED)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["contract"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(due_date__gte=models.F("start_date"))
                | models.Q(due_date__isnull=True)
                | models.Q(start_date__isnull=True),
                name="deliverable_due_after_start",
            ),
        ]

    def __str__(self) -> str:
        return self.name or f"Deliverable #{self.pk}"

    # Rollup metrics - computed fields (read-only)

    def get_assigned_budget_hours(self) -> Decimal:
        """Sum of all task budget_hours for this deliverable."""
        result = self.tasks.aggregate(total=Sum("budget_hours"))["total"]
        return result or Decimal("0")

    def get_spent_hours(self) -> Decimal:
        """Sum of all time entry hours for this deliverable."""
        result = self.time_entries.aggregate(total=Sum("hours"))["total"]
        return result or Decimal("0")

    def get_planned_weeks(self) -> int:
        """
        Number of planned weeks for this deliverable.
        Uses deliverable start_date/due_date if present, else contract dates.
        Minimum is 1 week.
        """
        start = self.start_date or self.contract.start_date
        end = self.due_date or self.contract.end_date
        days = (end - start).days + 1
        return max(1, ceil(days / 7))

    def get_elapsed_weeks(self) -> int:
        """
        Number of elapsed weeks from start to today (capped at planned end).
        Minimum is 1 week.
        """
        start = self.start_date or self.contract.start_date
        end = self.due_date or self.contract.end_date
        today = date.today()
        actual_end = min(today, end)

        # If we haven't started yet, return 1
        if today < start:
            return 1

        days = (actual_end - start).days + 1
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
        """Budget hours remaining (budget - assigned budget hours)."""
        return self.budget_hours - self.get_assigned_budget_hours()

    def get_unspent_budget_hours(self) -> Decimal:
        """Unspent budget hours (budget - spent hours)."""
        return self.budget_hours - self.get_spent_hours()

    def get_variance_hours(self) -> Decimal:
        """Difference between spent and assigned budget hours (spent - assigned budget)."""
        return self.get_spent_hours() - self.get_assigned_budget_hours()

    # Health flags

    def is_over_budget(self) -> bool:
        """True if spent hours exceed deliverable budget."""
        return self.get_spent_hours() > self.budget_hours

    def is_overassigned(self) -> bool:
        """True if assigned budget hours exceed deliverable budget."""
        return self.get_assigned_budget_hours() > self.budget_hours

    def is_missing_budget(self) -> bool:
        """True if budget hours is 0 but has tasks."""
        return self.budget_hours == 0 and self.tasks.exists()

    def is_missing_lead(self) -> bool:
        """True if no assignment has is_lead=True."""
        return not self.assignments.filter(is_lead=True).exists()

    def get_latest_status_update(self):
        """
        Get the most recent status update by period_end.
        Returns None if no status updates exist.
        """
        return self.status_updates.order_by("-period_end").first()
