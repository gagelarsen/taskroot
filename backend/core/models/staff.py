from django.conf import settings
from django.db import models


class Staff(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"

    class Role(models.TextChoices):
        STAFF = "staff", "Staff"
        MANAGER = "manager", "Manager"
        ADMIN = "admin", "Admin"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="staff",
        null=True,
        blank=True,
    )

    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STAFF)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["last_name", "first_name"]

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name} <{self.email}>"
