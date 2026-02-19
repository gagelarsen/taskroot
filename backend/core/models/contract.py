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

    class ContractType(models.TextChoices):
        FIXED_COST = "fixed_cost", "Fixed Cost"
        TIME_AND_MATERIALS = "time_and_materials", "Time and Materials"

    name = models.CharField(max_length=255, default="")
    client_name = models.CharField(max_length=255, default="")
    contract_number = models.CharField(max_length=100, blank=True, default="")
    start_date = models.DateField()
    end_date = models.DateField()
    budget_hours = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
    )
    contract_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
        null=True,
        blank=True,
    )
    contract_type = models.CharField(
        max_length=30,
        choices=ContractType.choices,
        default=ContractType.FIXED_COST,
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    tags = models.JSONField(default=list, blank=True)

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
        """
        Sum of assigned budget hours per week across all deliverables.
        Since assignment budget_hours represents hours per week,
        we just sum them directly without dividing by planned weeks.
        """
        return self.get_assigned_budget_hours()

    def get_spent_hours_per_week(self) -> Decimal:
        """Spent hours divided by elapsed weeks."""
        elapsed_weeks = self.get_elapsed_weeks()
        spent_total = self.get_spent_hours()
        return spent_total / Decimal(str(elapsed_weeks))

    def get_remaining_budget_hours(self) -> Decimal:
        """Budget hours remaining (budget - spent hours)."""
        return self.budget_hours - self.get_spent_hours()

    def get_invoiced_amount(self) -> Decimal:
        """Sum of all invoiced amounts for this contract."""
        total = Decimal("0")
        for update in self.invoice_updates.all():
            total += update.amount
        return total

    def get_remaining_contract_amount(self) -> Decimal | None:
        """Contract amount remaining (contract amount - invoiced), or None when contract amount is not set."""
        if self.contract_amount is None:
            return None
        return self.contract_amount - self.get_invoiced_amount()

    def get_unspent_budget_hours(self) -> Decimal:
        """Unspent budget hours (budget - spent hours). Alias for get_remaining_budget_hours()."""
        return self.get_remaining_budget_hours()

    def get_unassigned_budget_hours(self) -> Decimal:
        """Unassigned budget hours (budget - assigned budget hours)."""
        return self.budget_hours - self.get_assigned_budget_hours()

    def get_estimated_burn_rate(self) -> Decimal:
        """
        Estimated burn rate (hours per week) based on staff assignments across all deliverables.
        This is the amount of time allocated to staff each week.
        Alias for get_assigned_budget_hours_per_week().
        """
        return self.get_assigned_budget_hours_per_week()

    def get_actual_burn_rate(self, weeks: int = 4) -> Decimal:
        """
        Actual burn rate (hours per week) based on recent time entries across all deliverables.
        Calculates average hours per week from time entries over the last N weeks.

        Args:
            weeks: Number of weeks to look back (default: 4)

        Returns:
            Sum of actual burn rates from all deliverables.
            Returns Decimal("0") if no time entries exist in the period.
        """
        total = Decimal("0")
        for deliverable in self.deliverables.all():
            total += deliverable.get_actual_burn_rate(weeks=weeks)
        return total

    def get_estimated_percent_complete(self) -> Decimal:
        """
        Estimated completion percent for this contract from all deliverable tasks.

        Uses budget-weighted average when task budget_hours exist.
        Falls back to simple average when all task budgets are zero.
        Returns Decimal("0") when no tasks exist.
        """
        tasks = []
        for deliverable in self.deliverables.all():
            tasks.extend(list(deliverable.tasks.all()))

        if not tasks:
            return Decimal("0")

        total_budget_hours = sum((task.budget_hours for task in tasks), Decimal("0"))
        if total_budget_hours > 0:
            weighted_sum = sum((task.percent_complete * task.budget_hours for task in tasks), Decimal("0"))
            return weighted_sum / total_budget_hours

        total_percent = sum((task.percent_complete for task in tasks), Decimal("0"))
        return total_percent / Decimal(str(len(tasks)))

    # Health flags

    def is_over_budget(self) -> bool:
        """True if spent hours exceed budget."""
        return self.get_spent_hours() > self.budget_hours

    def is_overassigned(self) -> bool:
        """True if assigned budget hours exceed contract budget."""
        return self.get_assigned_budget_hours() > self.budget_hours

    def is_over_invoiced(self) -> bool:
        """True if total invoiced amount exceeds contract amount."""
        if self.contract_amount is None:
            return False
        return self.get_invoiced_amount() > self.contract_amount

    def is_over_expected(self) -> bool:
        """
        True if spending rate exceeds assigned rate.
        Compares spent_hours_per_week with assigned_budget_hours_per_week.
        """
        return self.get_spent_hours_per_week() > self.get_assigned_budget_hours_per_week()
