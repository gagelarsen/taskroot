import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0015_initiative_tags"),
    ]

    operations = [
        migrations.CreateModel(
            name="FutureWork",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255)),
                ("tags", models.JSONField(blank=True, default=list)),
                ("target_date", models.DateField(blank=True, null=True)),
                ("notes", models.TextField(blank=True, default="")),
                (
                    "converted_to_type",
                    models.CharField(
                        blank=True,
                        choices=[("initiative", "Initiative"), ("contract", "Contract")],
                        max_length=20,
                        null=True,
                    ),
                ),
                ("converted_to_id", models.PositiveIntegerField(blank=True, null=True)),
                ("converted_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "owner",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="future_work_items",
                        to="core.staff",
                    ),
                ),
            ],
            options={"ordering": ["-id"]},
        ),
    ]
