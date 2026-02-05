from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from .deliverable import Deliverable
from .staff import Staff


class DeliverableTimeEntry(models.Model):
    deliverable = models.ForeignKey(Deliverable, on_delete=models.CASCADE, related_name="time_entries")
    staff = models.ForeignKey(Staff, on_delete=models.PROTECT, related_name="time_entries")
    entry_date = models.DateField()
    hours = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],  # > 0
    )
    note = models.TextField(blank=True, default="")

    # Idempotency fields for integration safety
    # When external_source is set, (external_source, external_id) must be unique
    external_source = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Source system identifier (e.g., 'jira', 'harvest', 'toggl')",
    )
    external_id = models.CharField(
        max_length=200,
        blank=True,
        default="",
        help_text="External system's unique identifier for this time entry",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["deliverable", "entry_date"]),
            models.Index(fields=["staff", "entry_date"]),
            models.Index(fields=["external_source", "external_id"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["external_source", "external_id"],
                condition=models.Q(external_source__gt=""),
                name="unique_external_time_entry",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.staff} {self.entry_date}: {self.hours}h"
