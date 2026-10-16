"""Model-bound parameters are shown but cannot be changed (API and Django admin)."""
from decimal import Decimal

from accounts.models import User
from accounts.tests.helpers import BaseAPITestCase
from core.config_defaults import MODEL_BOUND, READ_ONLY_KEYS
from core.models import AuditLog, SystemConfig


class ModelBoundConfigTests(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        self.admin = self.make_user("admin@example.com", "0922222222", role=User.Role.ADMIN)

    def test_api_refuses_change(self):
        self.auth(self.admin)
        for key in ("rapid_rise_threshold_m", "suspicious_jump_threshold_m"):
            with self.subTest(key=key):
                res = self.client.patch(f"/api/admin/config/{key}/", {"value": "0.5"}, format="json")
                self.assertEqual(res.status_code, 403)
                row = SystemConfig.objects.get(key=key)
                self.assertNotEqual(row.value, Decimal("0.5"))
                self.assertEqual(row.description, MODEL_BOUND)
        self.assertFalse(AuditLog.objects.filter(action=AuditLog.Action.CONFIG_CHANGED).exists())
        listing = {c["key"]: c for c in self.client.get("/api/admin/config/").data}
        self.assertTrue(listing["rapid_rise_threshold_m"]["read_only"])
        self.assertFalse(listing["stale_data_hours"]["read_only"])
        # other keys stay editable
        ok = self.client.patch("/api/admin/config/stale_data_hours/", {"value": 3}, format="json")
        self.assertEqual(ok.status_code, 200)

    def test_django_admin_is_view_only(self):
        self.client.force_login(self.admin)
        for key in READ_ONLY_KEYS:
            pk = SystemConfig.objects.get(key=key).pk
            url = f"/django-admin/core/systemconfig/{pk}/change/"
            page = self.client.get(url, SERVER_NAME="localhost")
            self.assertEqual(page.status_code, 200)            # can view
            self.assertNotContains(page, 'name="value"')        # no editable field
            res = self.client.post(url, {"value": "0.5"}, SERVER_NAME="localhost")
            self.assertEqual(res.status_code, 403)
            self.assertNotEqual(SystemConfig.objects.get(pk=pk).value, Decimal("0.5"))
