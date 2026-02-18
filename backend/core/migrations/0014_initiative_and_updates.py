import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0013_contract_tags"),
    ]

    operations = [
        migrations.CreateModel(
            name="Initiative",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255)),
                (
                    "status",
                    models.CharField(
                        choices=[("active", "Active"), ("on_hold", "On Hold"), ("completed", "Completed")],
                        default="active",
                        max_length=20,
                    ),
                ),
                ("target_date", models.DateField(blank=True, null=True)),
                ("notes", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "owner",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="initiatives",
                        to="core.staff",
                    ),
                ),
            ],
            options={"ordering": ["-id"]},
        ),
        migrations.CreateModel(
            name="InitiativeWeeklyUpdate",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("period_end", models.DateField()),
                ("percent_complete", models.DecimalField(decimal_places=2, max_digits=5)),
                ("summary", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="initiative_updates_created",
                        to="core.staff",
                    ),
                ),
                (
                    "initiative",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="weekly_updates",
                        to="core.initiative",
                    ),
                ),
            ],
            options={"ordering": ["-period_end", "-id"]},
        ),
        migrations.AddConstraint(
            model_name="initiativeweeklyupdate",
            constraint=models.UniqueConstraint(
                fields=("initiative", "period_end"), name="unique_initiative_weekly_update"
            ),
        ),
    ]
