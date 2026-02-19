from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from .contract import Contract


class ContractInvoiceUpdate(models.Model):
    contract = models.ForeignKey(Contract, on_delete=models.CASCADE, related_name="invoice_updates")
    invoice_date = models.DateField()
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    note = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["contract", "invoice_date"])]

    def __str__(self) -> str:
        return f"{self.contract} {self.invoice_date}: ${self.amount}"
