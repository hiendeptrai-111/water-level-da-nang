"""Phase 2: add the new SystemConfig keys and correct the description of the two keys that
only mirror the model's training values (the model keeps using its own constants)."""
from decimal import Decimal

from django.db import migrations

from core.config_defaults import DEFAULTS

REFERENCE_ONLY = ("rapid_rise_threshold_m", "suspicious_jump_threshold_m", "overview_refresh_minutes")


def seed(apps, schema_editor):
    SystemConfig = apps.get_model("core", "SystemConfig")
    for key, (value, unit, _min, description) in DEFAULTS.items():
        SystemConfig.objects.get_or_create(
            key=key, defaults={"value": Decimal(str(value)), "unit": unit,
                               "description": description})
    for key in REFERENCE_ONLY:
        SystemConfig.objects.filter(key=key).update(description=DEFAULTS[key][3])


class Migration(migrations.Migration):
    dependencies = [("core", "0004_alter_auditlog_action_alter_systemconfig_key")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
