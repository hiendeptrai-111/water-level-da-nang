"""Phase 4: add the new SystemConfig keys (and refresh the dispatch description)."""
from decimal import Decimal

from django.db import migrations

from core.config_defaults import DEFAULTS


def seed(apps, schema_editor):
    SystemConfig = apps.get_model("core", "SystemConfig")
    for key, (value, unit, _min, description) in DEFAULTS.items():
        SystemConfig.objects.get_or_create(
            key=key, defaults={"value": Decimal(str(value)), "unit": unit, "description": description})
    SystemConfig.objects.filter(key="dispatch_refresh_seconds").update(
        description=DEFAULTS["dispatch_refresh_seconds"][3])


class Migration(migrations.Migration):
    dependencies = [("core", "0010_alter_auditlog_action")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
