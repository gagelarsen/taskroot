from django.db import models

from .deliverable import Deliverable
from .staff import Staff


class DeliverableStatusUpdate(models.Model):
    class Status(models.TextChoices):
        ON_TRACK = "on_track", "On track"
        AT_RISK = "at_risk", "At risk"
        OFF_TRACK = "off_track", "Off track"

    deliverable = models.ForeignKey(Deliverable, on_delete=models.CASCADE, related_name="status_updates")
    period_end = models.DateField()  # required
    status = models.CharField(max_length=20, choices=Status.choices)
    summary = models.TextField(blank=True, default="")

    created_by = models.ForeignKey(
        Staff, null=True, blank=True, on_delete=models.SET_NULL, related_name="status_updates"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["deliverable", "period_end"], name="uniq_deliverable_period_end"),
        ]
        indexes = [
            models.Index(fields=["deliverable", "period_end"]),
        ]

    def __str__(self) -> str:
        return f"{self.deliverable} {self.period_end}: {self.status}"
