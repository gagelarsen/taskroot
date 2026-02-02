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

    external_source = models.CharField(max_length=100, blank=True, default="")
    external_id = models.CharField(max_length=200, blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["deliverable", "entry_date"]),
            models.Index(fields=["staff", "entry_date"]),
        ]

    def __str__(self) -> str:
        return f"{self.staff} {self.entry_date}: {self.hours}h"
