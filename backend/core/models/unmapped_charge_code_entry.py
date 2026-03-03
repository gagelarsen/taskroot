from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from .charge_code import ChargeCode


class UnmappedChargeCodeEntry(models.Model):
    charge_code = models.ForeignKey(ChargeCode, on_delete=models.PROTECT, related_name="unmapped_entries")
    entry_date = models.DateField()
    hours = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    note = models.TextField(blank=True, default="")
    source_file = models.CharField(max_length=255, blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["charge_code", "entry_date"]),
            models.Index(fields=["entry_date"]),
        ]

    def __str__(self) -> str:
        return f"{self.charge_code.code} {self.entry_date}: {self.hours}h"
