from django.db import models


class FutureWork(models.Model):
    class ConvertedToType(models.TextChoices):
        INITIATIVE = "initiative", "Initiative"
        CONTRACT = "contract", "Contract"

    name = models.CharField(max_length=255)
    owner = models.ForeignKey(
        "core.Staff",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="future_work_items",
    )
    tags = models.JSONField(default=list, blank=True)
    target_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")

    converted_to_type = models.CharField(max_length=20, choices=ConvertedToType.choices, null=True, blank=True)
    converted_to_id = models.PositiveIntegerField(null=True, blank=True)
    converted_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-id"]

    def __str__(self) -> str:
        return self.name

    def is_converted(self) -> bool:
        return bool(self.converted_to_type and self.converted_to_id and self.converted_at)
