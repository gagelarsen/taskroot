from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0014_initiative_and_updates"),
    ]

    operations = [
        migrations.AddField(
            model_name="initiative",
            name="tags",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
