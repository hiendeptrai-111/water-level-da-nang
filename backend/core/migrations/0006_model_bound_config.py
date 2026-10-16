"""rapid_rise_threshold_m and suspicious_jump_threshold_m become read-only (model-bound)."""
from django.db import migrations

from core.config_defaults import DEFAULTS, READ_ONLY_KEYS


def describe(apps, schema_editor):
    SystemConfig = apps.get_model("core", "SystemConfig")
    for key in READ_ONLY_KEYS:
        SystemConfig.objects.filter(key=key).update(description=DEFAULTS[key][3])


class Migration(migrations.Migration):
    dependencies = [("core", "0005_seed_phase2_config")]
    operations = [migrations.RunPython(describe, migrations.RunPython.noop)]
