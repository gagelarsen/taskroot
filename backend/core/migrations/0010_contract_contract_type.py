from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0009_remove_deliverable_start_date_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="contract",
            name="contract_type",
            field=models.CharField(
                choices=[("fixed_cost", "Fixed Cost"), ("time_and_materials", "Time and Materials")],
                default="fixed_cost",
                max_length=30,
            ),
        ),
    ]
