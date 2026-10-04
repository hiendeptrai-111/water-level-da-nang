"""Criterion e (lockout) and general login rules."""
from datetime import timedelta
from unittest import mock

from django.utils import timezone

from accounts.models import LoginAttempt, User
from core.models import AuditLog, SystemConfig

from .helpers import PASSWORD, BaseAPITestCase

GENERIC = "Thông tin đăng nhập không đúng"


class LoginTests(BaseAPITestCase):
    def test_login_by_email_or_phone(self):
        self.make_user()
        for ident in ["dan@example.com", "0911111111"]:
            res = self.login(ident)
            self.assertEqual(res.status_code, 200, res.data)
            self.assertIn("access", res.data)
            self.assertIn("refresh", res.data)
            self.assertEqual(res.data["user"]["role"], "citizen")

    def test_wrong_password_and_unknown_account_same_message(self):
        self.make_user()
        wrong = self.login("dan@example.com", "SaiMatKhau1")
        unknown = self.login("khongco@example.com", "SaiMatKhau1")
        unknown_phone = self.login("0999999999", "SaiMatKhau1")
        for res in (wrong, unknown, unknown_phone):
            self.assertEqual(res.status_code, 401)
            self.assertEqual(res.data["detail"], GENERIC)
        self.assertEqual(wrong.data, unknown.data)

    # e. 5 wrong passwords -> locked 15 minutes, same message for unknown accounts
    def test_lockout_after_five_failures(self):
        self.make_user()
        for _ in range(5):
            self.assertEqual(self.login("dan@example.com", "SaiMatKhau1").status_code, 401)
        res = self.login("dan@example.com", PASSWORD)  # correct password, but locked
        self.assertEqual(res.status_code, 429)
        self.assertEqual(res.data["code"], "login_locked")
        self.assertIn("15 phút", res.data["detail"])
        # the phone number of the same account is locked too
        self.assertEqual(self.login("0911111111", PASSWORD).status_code, 429)

        attempt = LoginAttempt.objects.get()
        remaining = attempt.locked_until - timezone.now()
        self.assertTrue(timedelta(minutes=14) < remaining <= timedelta(minutes=15))

        # after 15 minutes the account can log in again
        later = timezone.now() + timedelta(minutes=15, seconds=1)
        with mock.patch("django.utils.timezone.now", return_value=later):
            self.assertEqual(self.login("dan@example.com", PASSWORD).status_code, 200)

    def test_lockout_does_not_reveal_whether_account_exists(self):
        self.make_user()
        for _ in range(5):
            self.login("dan@example.com", "SaiMatKhau1")
            self.login("khongco@example.com", "SaiMatKhau1")
        existing = self.login("dan@example.com", "SaiMatKhau1")
        missing = self.login("khongco@example.com", "SaiMatKhau1")
        self.assertEqual(existing.status_code, missing.status_code)
        self.assertEqual(existing.data, missing.data)

    def test_success_resets_failure_counter(self):
        self.make_user()
        for _ in range(4):
            self.login("dan@example.com", "SaiMatKhau1")
        self.assertEqual(self.login("dan@example.com").status_code, 200)
        for _ in range(4):
            self.login("dan@example.com", "SaiMatKhau1")
        self.assertEqual(self.login("dan@example.com").status_code, 200)

    def test_lockout_values_come_from_config(self):
        SystemConfig.objects.filter(key="max_failed_logins").update(value=3)
        SystemConfig.objects.filter(key="login_lockout_minutes").update(value=20)
        self.make_user()
        for _ in range(3):
            self.login("dan@example.com", "SaiMatKhau1")
        res = self.login("dan@example.com")
        self.assertEqual(res.status_code, 429)
        self.assertIn("20 phút", res.data["detail"])

    def test_locked_account_cannot_login(self):
        self.make_user(is_active=False)
        self.assertEqual(self.login("dan@example.com", "SaiMatKhau1").data["detail"], GENERIC)
        res = self.login("dan@example.com")
        self.assertEqual(res.status_code, 403)
        self.assertEqual(res.data["code"], "account_locked")

    def test_admin_and_rescue_logins_are_audited_citizens_not(self):
        self.make_user()
        admin = self.make_user("admin@example.com", "0922222222", role=User.Role.ADMIN)
        rescue = self.make_user("doi@example.com", "0933333333", role=User.Role.RESCUE_TEAM)
        for u in ("dan@example.com", "admin@example.com", "doi@example.com"):
            self.assertEqual(self.login(u).status_code, 200)
        logs = AuditLog.objects.filter(action=AuditLog.Action.LOGIN)
        self.assertEqual({l.actor_id for l in logs}, {admin.pk, rescue.pk})

    def test_refresh_and_logout(self):
        self.make_user()
        tokens = self.login("dan@example.com").data
        res = self.client.post("/api/auth/token/refresh/", {"refresh": tokens["refresh"]},
                               format="json")
        self.assertEqual(res.status_code, 200, res.data)
        self.assertIn("access", res.data)
        self.client.post("/api/auth/logout/", {"refresh": tokens["refresh"]}, format="json")
        res = self.client.post("/api/auth/token/refresh/", {"refresh": tokens["refresh"]},
                               format="json")
        self.assertEqual(res.status_code, 401)
