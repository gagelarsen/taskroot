from datetime import date
from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Initiative(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        ON_HOLD = "on_hold", "On Hold"
        COMPLETED = "completed", "Completed"

    name = models.CharField(max_length=255)
    owner = models.ForeignKey(
        "core.Staff",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="initiatives",
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    tags = models.JSONField(default=list, blank=True)
    target_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-id"]

    def __str__(self) -> str:
        return self.name

    def get_latest_update(self):
        return self.weekly_updates.order_by("-period_end", "-id").first()

    def get_current_percent_complete(self) -> Decimal:
        latest = self.get_latest_update()
        if latest:
            return latest.percent_complete
        return Decimal("0")

    def is_update_stale(self, days: int = 7) -> bool:
        latest = self.get_latest_update()
        if not latest:
            return True
        return (date.today() - latest.period_end).days > days


class InitiativeWeeklyUpdate(models.Model):
    initiative = models.ForeignKey(Initiative, on_delete=models.CASCADE, related_name="weekly_updates")
    period_end = models.DateField()
    percent_complete = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))],
    )
    summary = models.TextField(blank=True, default="")
    created_by = models.ForeignKey(
        "core.Staff",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="initiative_updates_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-period_end", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["initiative", "period_end"],
                name="unique_initiative_weekly_update",
            )
        ]

    def __str__(self) -> str:
        return f"{self.initiative.name} - {self.period_end}"
