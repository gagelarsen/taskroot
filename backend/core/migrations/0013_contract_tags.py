from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0012_task_percent_complete"),
    ]

    operations = [
        migrations.AddField(
            model_name="contract",
            name="tags",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
