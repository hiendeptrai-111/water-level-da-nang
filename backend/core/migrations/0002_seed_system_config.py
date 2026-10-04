from decimal import Decimal

from django.db import migrations

from core.config_defaults import DEFAULTS


def seed(apps, schema_editor):
    SystemConfig = apps.get_model("core", "SystemConfig")
    for key, (value, unit, _min, description) in DEFAULTS.items():
        SystemConfig.objects.get_or_create(
            key=key, defaults={"value": Decimal(str(value)), "unit": unit,
                               "description": description})


class Migration(migrations.Migration):
    dependencies = [("core", "0001_initial")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
