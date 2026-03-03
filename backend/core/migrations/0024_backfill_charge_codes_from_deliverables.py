from django.db import migrations


def backfill_charge_codes_from_deliverables(apps, schema_editor):
    Deliverable = apps.get_model("core", "Deliverable")
    ChargeCode = apps.get_model("core", "ChargeCode")

    deliverables = Deliverable.objects.exclude(charge_code="").order_by("id")
    for deliverable in deliverables:
        code = (deliverable.charge_code or "").strip()
        if not code:
            continue

        charge_code, _ = ChargeCode.objects.get_or_create(
            code=code,
            defaults={
                "description": "",
                "is_active": True,
            },
        )

        if charge_code.deliverable_id is None:
            charge_code.deliverable_id = deliverable.id
            charge_code.save(update_fields=["deliverable", "updated_at"])


class Migration(migrations.Migration):
    dependencies = [
        (
            "core",
            "0023_rename_core_charge_start_d_4c8bd5_idx_core_charge_start_d_ccbb8f_idx_and_more",
        ),
    ]

    operations = [
        migrations.RunPython(backfill_charge_codes_from_deliverables, migrations.RunPython.noop),
    ]
