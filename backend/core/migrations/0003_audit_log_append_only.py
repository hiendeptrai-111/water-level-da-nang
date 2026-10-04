from django.db import migrations

# Database-level guarantee that the system log is append-only: any UPDATE or DELETE on
# core_auditlog (from Django, raw SQL or psql) raises an error.
FORWARD = """
CREATE OR REPLACE FUNCTION core_auditlog_append_only() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'core_auditlog is append-only (% not allowed)', TG_OP;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER core_auditlog_no_update_delete
BEFORE UPDATE OR DELETE ON core_auditlog
FOR EACH ROW EXECUTE FUNCTION core_auditlog_append_only();
"""

REVERSE = """
DROP TRIGGER IF EXISTS core_auditlog_no_update_delete ON core_auditlog;
DROP FUNCTION IF EXISTS core_auditlog_append_only();
"""


class Migration(migrations.Migration):
    dependencies = [("core", "0002_seed_system_config")]
    operations = [migrations.RunSQL(FORWARD, REVERSE)]
