from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from .deliverable import Deliverable
from .staff import Staff


class DeliverableAssignment(models.Model):
    deliverable = models.ForeignKey(Deliverable, on_delete=models.CASCADE, related_name="assignments")
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name="deliverable_assignments")
    budget_hours = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
        default=Decimal("0"),
    )
    is_lead = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["deliverable", "staff"], name="uniq_deliverable_staff_assignment"),
        ]
        indexes = [
            models.Index(fields=["deliverable"]),
            models.Index(fields=["staff"]),
        ]

    def __str__(self) -> str:
        return f"{self.deliverable} ↔ {self.staff}"
