"""Criteria c, d (email verification)."""
from datetime import timedelta

from django.core import mail
from django.utils import timezone

from accounts.models import EmailToken, User
from core.models import SystemConfig

from .helpers import BaseAPITestCase


class VerifyEmailTests(BaseAPITestCase):
    def register(self):
        res = self.client.post("/api/auth/register/", self.register_payload(), format="json")
        self.assertEqual(res.status_code, 201, res.data)
        return self.token_from_last_email()

    def verify(self, token):
        return self.client.post("/api/auth/verify-email/", {"token": token}, format="json")

    # c. unverified -> cannot log in, gets a message and can resend
    def test_unverified_cannot_login_and_can_resend(self):
        old_token = self.register()
        res = self.login("hien@gmail.com")
        self.assertEqual(res.status_code, 403)
        self.assertEqual(res.data["code"], "email_not_verified")
        self.assertIn("chưa được xác thực", res.data["detail"])
        self.assertNotIn("access", res.data)
        # also by phone number
        self.assertEqual(self.login("0912345678").data["code"], "email_not_verified")

        res = self.client.post("/api/auth/resend-verification/",
                               {"identifier": "0912345678"}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(mail.outbox), 2)
        new_token = self.token_from_last_email()
        self.assertNotEqual(old_token, new_token)
        self.assertEqual(self.verify(old_token).status_code, 400)  # superseded by the new link
        self.assertEqual(self.verify(new_token).status_code, 200)
        self.assertEqual(self.login("hien@gmail.com").status_code, 200)

    def test_resend_same_answer_for_unknown_account(self):
        unknown = self.client.post("/api/auth/resend-verification/",
                                   {"identifier": "khongco@example.com"}, format="json")
        self.register()
        mail.outbox = []
        known = self.client.post("/api/auth/resend-verification/",
                                 {"identifier": "hien@gmail.com"}, format="json")
        self.assertEqual(known.status_code, unknown.status_code)
        self.assertEqual(known.data, unknown.data)

    def test_wrong_password_on_unverified_account_gives_generic_error(self):
        self.register()
        res = self.login("hien@gmail.com", "SaiMatKhau9")
        self.assertEqual(res.status_code, 401)
        self.assertEqual(res.data["detail"], "Thông tin đăng nhập không đúng")

    # d. expired or reused link -> rejected
    def test_link_used_twice_is_rejected(self):
        token = self.register()
        self.assertEqual(self.verify(token).status_code, 200)
        res = self.verify(token)
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.data["code"], "invalid_token")

    def test_expired_link_is_rejected(self):
        token = self.register()
        EmailToken.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
        res = self.verify(token)
        self.assertEqual(res.status_code, 400)
        self.assertFalse(User.objects.get().email_verified)

    def test_link_lifetime_comes_from_config(self):
        SystemConfig.objects.filter(key="email_verification_ttl_hours").update(value=2)
        self.register()
        t = EmailToken.objects.get()
        self.assertAlmostEqual((t.expires_at - t.created_at).total_seconds(), 2 * 3600, delta=5)

    def test_garbage_token_rejected(self):
        self.assertEqual(self.verify("abc").status_code, 400)
