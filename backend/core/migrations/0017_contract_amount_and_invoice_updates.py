import decimal

import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0016_futurework"),
    ]

    operations = [
        migrations.AddField(
            model_name="contract",
            name="contract_amount",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=12,
                null=True,
                validators=[django.core.validators.MinValueValidator(decimal.Decimal("0"))],
            ),
        ),
        migrations.AddField(
            model_name="contract",
            name="contract_number",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
        migrations.CreateModel(
            name="ContractInvoiceUpdate",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("invoice_date", models.DateField()),
                (
                    "amount",
                    models.DecimalField(
                        decimal_places=2,
                        max_digits=12,
                        validators=[django.core.validators.MinValueValidator(decimal.Decimal("0.01"))],
                    ),
                ),
                ("note", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "contract",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="invoice_updates",
                        to="core.contract",
                    ),
                ),
            ],
        ),
        migrations.AddIndex(
            model_name="contractinvoiceupdate",
            index=models.Index(fields=["contract", "invoice_date"], name="core_contra_contrac_4505a4_idx"),
        ),
    ]
