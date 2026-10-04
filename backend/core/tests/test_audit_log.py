"""Criterion i: the system log cannot be edited or deleted (API, Django admin, ORM, SQL)."""
from django.db import connection, transaction
from django.db import DatabaseError

from accounts.models import User
from accounts.tests.helpers import BaseAPITestCase
from core.models import AuditLog
from core.services import audit


class AuditLogAppendOnlyTests(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        self.admin = self.make_user("admin@example.com", "0922222222", role=User.Role.ADMIN)
        self.entry = audit(AuditLog.Action.USER_CREATED, actor=self.admin, target=self.admin,
                           details={"x": 1})

    def assertUnchanged(self):
        self.assertTrue(AuditLog.objects.filter(pk=self.entry.pk, details={"x": 1}).exists())

    def test_api_is_read_only(self):
        self.auth(self.admin)  # creates one more LOGIN entry
        url = f"/api/admin/audit-logs/{self.entry.pk}/"
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(self.client.put(url, {"details": {}}, format="json").status_code, 405)
        self.assertEqual(self.client.patch(url, {"details": {}}, format="json").status_code, 405)
        self.assertEqual(self.client.delete(url).status_code, 405)
        self.assertEqual(self.client.post("/api/admin/audit-logs/", {"action": "login"},
                                          format="json").status_code, 405)
        self.assertUnchanged()

    def test_django_admin_cannot_add_change_or_delete(self):
        self.client.force_login(self.admin)
        base = "/django-admin/core/auditlog/"
        self.assertEqual(self.client.get(base).status_code, 200)  # viewing is allowed
        change = self.client.post(f"{base}{self.entry.pk}/change/",
                                  {"action": "login", "details": "{}"})
        self.assertEqual(change.status_code, 403)
        self.assertEqual(self.client.post(f"{base}{self.entry.pk}/delete/", {"post": "yes"})
                         .status_code, 403)
        self.assertEqual(self.client.get(f"{base}add/").status_code, 403)
        bulk = self.client.post(base, {"action": "delete_selected",
                                       "_selected_action": [self.entry.pk], "post": "yes"})
        self.assertNotEqual(bulk.status_code, 500)
        self.assertUnchanged()

    def test_orm_update_and_delete_raise(self):
        self.entry.details = {"x": 2}
        with self.assertRaises(PermissionError):
            self.entry.save()
        with self.assertRaises(PermissionError):
            self.entry.delete()
        with self.assertRaises(PermissionError):
            AuditLog.objects.filter(pk=self.entry.pk).update(details={})
        with self.assertRaises(PermissionError):
            AuditLog.objects.all().delete()
        self.assertUnchanged()

    def test_database_trigger_blocks_raw_sql(self):
        for sql in ["UPDATE core_auditlog SET details = '{}'::jsonb",
                    "DELETE FROM core_auditlog"]:
            with self.subTest(sql=sql):
                with self.assertRaises(DatabaseError), transaction.atomic():
                    with connection.cursor() as cur:
                        cur.execute(sql)
        self.assertUnchanged()


class AuditedActionsTests(BaseAPITestCase):
    def test_config_change_is_logged(self):
        admin = self.make_user("admin@example.com", "0922222222", role=User.Role.ADMIN)
        self.auth(admin)
        res = self.client.patch("/api/admin/config/sos_self_claim_wait_minutes/", {"value": 20},
                                format="json")
        self.assertEqual(res.status_code, 200, res.data)
        log = AuditLog.objects.get(action=AuditLog.Action.CONFIG_CHANGED)
        self.assertEqual(log.actor, admin)
        self.assertEqual(log.details["key"], "sos_self_claim_wait_minutes")
        self.assertEqual(log.details["new"], "20.000")

    def test_user_created_is_logged(self):
        admin = self.make_user("admin@example.com", "0922222222", role=User.Role.ADMIN)
        self.auth(admin)
        self.client.post("/api/admin/users/", {
            "full_name": "Admin Hai", "phone_number": "0955555555", "email": "a2@example.com",
            "role": "admin"}, format="json")
        log = AuditLog.objects.get(action=AuditLog.Action.USER_CREATED)
        self.assertEqual(log.target_label, "Admin Hai <a2@example.com>")
