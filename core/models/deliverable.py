from django.db import models

from .contract import Contract


class Deliverable(models.Model):
    class Status(models.TextChoices):
        PLANNED = "planned", "Planned"
        IN_PROGRESS = "in_progress", "In progress"
        COMPLETE = "complete", "Complete"
        BLOCKED = "blocked", "Blocked"

    contract = models.ForeignKey(Contract, on_delete=models.PROTECT, related_name="deliverables")
    start_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PLANNED)

    name = models.CharField(max_length=255, default="")  # optional but helps in admin immediately

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["contract"]),
        ]

    def __str__(self) -> str:
        return self.name or f"Deliverable #{self.pk}"
