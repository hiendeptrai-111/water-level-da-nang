"""SystemConfig: seeded values, admin edits, JWT lifetimes read from it."""
from unittest import mock

from rest_framework.throttling import ScopedRateThrottle
from rest_framework_simplejwt.tokens import AccessToken as PlainAccessToken
from rest_framework_simplejwt.tokens import RefreshToken as PlainRefreshToken

from accounts.models import User
from accounts.tests.helpers import BaseAPITestCase
from core.config_defaults import DEFAULTS
from core.models import SystemConfig
from core.services import get_config


class SystemConfigTests(BaseAPITestCase):
    def test_all_parameters_seeded_with_spec_values(self):
        expected = {
            "sos_self_claim_wait_minutes": 15, "sos_anonymize_days": 90, "max_failed_logins": 5,
            "login_lockout_minutes": 15, "email_verification_ttl_hours": 24,
            "password_reset_ttl_minutes": 30, "jwt_access_minutes": 30, "jwt_refresh_days": 7,
            "rapid_rise_threshold_m": 0.3, "suspicious_jump_threshold_m": 0.8,
            "overview_refresh_minutes": 5, "dispatch_refresh_seconds": 30,
        }
        self.assertEqual(set(SystemConfig.objects.values_list("key", flat=True)), set(DEFAULTS))
        self.assertEqual({k: get_config(k) for k in expected}, expected)

    def test_jwt_lifetimes_follow_config(self):
        user = self.make_user()
        SystemConfig.objects.filter(key="jwt_access_minutes").update(value=5)
        SystemConfig.objects.filter(key="jwt_refresh_days").update(value=2)
        data = self.login("dan@example.com").data
        access, refresh = PlainAccessToken(data["access"]), PlainRefreshToken(data["refresh"])
        self.assertEqual(access["exp"] - access["iat"], 5 * 60)
        self.assertEqual(refresh["exp"] - refresh["iat"], 2 * 86400)
        self.assertEqual(access["ver"], user.token_version)
        new_access = self.client.post("/api/auth/token/refresh/", {"refresh": data["refresh"]},
                                      format="json").data["access"]
        new_access = PlainAccessToken(new_access)
        self.assertEqual(new_access["exp"] - new_access["iat"], 5 * 60)

    def test_admin_validation(self):
        admin = self.make_user("admin@example.com", "0922222222", role=User.Role.ADMIN)
        self.auth(admin)
        res = self.client.patch("/api/admin/config/max_failed_logins/", {"value": 0}, format="json")
        self.assertEqual(res.status_code, 400)
        res = self.client.patch("/api/admin/config/max_failed_logins/", {"value": 7},
                                format="json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(get_config("max_failed_logins"), 7)


class ThrottleTests(BaseAPITestCase):
    def test_register_login_forgot_are_rate_limited(self):
        rates = {"register": "2/hour", "login": "2/minute", "password_forgot": "2/hour",
                 "resend_verification": "2/hour"}
        with mock.patch.object(ScopedRateThrottle, "THROTTLE_RATES", rates):
            cases = [
                ("/api/auth/register/", {}),
                ("/api/auth/login/", {"identifier": "x@example.com", "password": "Sai123456"}),
                ("/api/auth/password/forgot/", {"email": "x@example.com"}),
                ("/api/auth/resend-verification/", {"identifier": "x@example.com"}),
            ]
            for url, body in cases:
                with self.subTest(url=url):
                    codes = [self.client.post(url, body, format="json").status_code
                             for _ in range(3)]
                    self.assertNotEqual(codes[0], 429)
                    self.assertEqual(codes[2], 429)
