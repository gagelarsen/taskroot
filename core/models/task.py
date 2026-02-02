from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from .deliverable import Deliverable
from .staff import Staff


class Task(models.Model):
    class Status(models.TextChoices):
        TODO = "todo", "To do"
        IN_PROGRESS = "in_progress", "In progress"
        DONE = "done", "Done"
        BLOCKED = "blocked", "Blocked"

    deliverable = models.ForeignKey(Deliverable, on_delete=models.CASCADE, related_name="tasks")
    assignee = models.ForeignKey(Staff, null=True, blank=True, on_delete=models.SET_NULL, related_name="tasks")
    planned_hours = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
        default=Decimal("0"),
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.TODO)
    title = models.CharField(max_length=255)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["deliverable"]),
        ]

    def __str__(self) -> str:
        return self.title
