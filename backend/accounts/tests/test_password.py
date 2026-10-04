"""Criterion h (old refresh tokens invalid after password change/reset) + password flows."""
from datetime import timedelta

from django.core import mail
from django.utils import timezone

from accounts.models import EmailToken

from .helpers import PASSWORD, BaseAPITestCase

NEW = "MatKhauMoi99"


class PasswordTests(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        self.user = self.make_user()

    def refresh(self, token):
        return self.client.post("/api/auth/token/refresh/", {"refresh": token}, format="json")

    def me(self, access):
        return self.client.get("/api/me/", HTTP_AUTHORIZATION=f"Bearer {access}")

    # h. change password -> old refresh tokens (all devices) invalid
    def test_change_password_invalidates_old_tokens(self):
        device1 = self.login("dan@example.com").data
        device2 = self.login("0911111111").data
        res = self.client.post("/api/me/change-password/", {
            "old_password": PASSWORD, "new_password": NEW, "new_password_confirm": NEW},
            format="json", HTTP_AUTHORIZATION=f"Bearer {device1['access']}")
        self.assertEqual(res.status_code, 200, res.data)
        for dev in (device1, device2):
            self.assertEqual(self.refresh(dev["refresh"]).status_code, 401)
            self.assertEqual(self.me(dev["access"]).status_code, 401)
        # the tokens returned by change-password work
        self.assertEqual(self.refresh(res.data["refresh"]).status_code, 200)
        self.assertEqual(self.me(res.data["access"]).status_code, 200)
        self.assertEqual(self.login("dan@example.com", PASSWORD).status_code, 401)
        self.assertEqual(self.login("dan@example.com", NEW).status_code, 200)

    def test_change_password_requires_old_password(self):
        access = self.login("dan@example.com").data["access"]
        res = self.client.post("/api/me/change-password/", {
            "old_password": "Sai123456", "new_password": NEW, "new_password_confirm": NEW},
            format="json", HTTP_AUTHORIZATION=f"Bearer {access}")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(list(res.data), ["old_password"])

    # h. reset password -> old refresh tokens invalid
    def test_reset_password_invalidates_old_tokens(self):
        old = self.login("dan@example.com").data
        self.client.post("/api/auth/password/forgot/", {"email": "DAN@example.com"}, format="json")
        token = self.token_from_last_email()
        self.assertIn("/reset-password?token=", mail.outbox[-1].body)
        res = self.client.post("/api/auth/password/reset/", {
            "token": token, "new_password": NEW, "new_password_confirm": NEW}, format="json")
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(self.refresh(old["refresh"]).status_code, 401)
        self.assertEqual(self.me(old["access"]).status_code, 401)
        self.assertEqual(self.login("dan@example.com", NEW).status_code, 200)

    def test_reset_link_single_use_and_expires(self):
        self.client.post("/api/auth/password/forgot/", {"email": "dan@example.com"}, format="json")
        token = self.token_from_last_email()
        body = {"token": token, "new_password": NEW, "new_password_confirm": NEW}
        self.assertEqual(self.client.post("/api/auth/password/reset/", body, format="json")
                         .status_code, 200)
        self.assertEqual(self.client.post("/api/auth/password/reset/", body, format="json")
                         .status_code, 400)

        self.client.post("/api/auth/password/forgot/", {"email": "dan@example.com"}, format="json")
        token = self.token_from_last_email()
        t = EmailToken.objects.filter(used_at__isnull=True).get()
        self.assertAlmostEqual((t.expires_at - t.created_at).total_seconds(), 30 * 60, delta=5)
        EmailToken.objects.filter(pk=t.pk).update(expires_at=timezone.now() - timedelta(seconds=1))
        body["token"] = token
        self.assertEqual(self.client.post("/api/auth/password/reset/", body, format="json")
                         .status_code, 400)

    def test_forgot_password_same_answer_for_unknown_email(self):
        a = self.client.post("/api/auth/password/forgot/", {"email": "dan@example.com"},
                             format="json")
        b = self.client.post("/api/auth/password/forgot/", {"email": "khongco@example.com"},
                             format="json")
        self.assertEqual((a.status_code, a.data), (b.status_code, b.data))
        self.assertEqual(len(mail.outbox), 1)


class ProfileTests(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        self.user = self.make_user()
        self.auth(self.user)

    def test_get_and_update_profile(self):
        res = self.client.get("/api/me/")
        self.assertEqual(res.data["email"], "dan@example.com")
        self.assertEqual(res.data["ward_label"], "Xã Đại Lộc")
        res = self.client.patch("/api/me/", {"ward": self.ward2.pk, "relative_phone": "0977777777",
                                             "notify_email": False}, format="json")
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data["ward_label"], "Phường Hội An")
        self.assertFalse(res.data["notify_email"])

    def test_phone_change_must_be_unique(self):
        self.make_user("khac@example.com", "0988888888")
        res = self.client.patch("/api/me/", {"phone_number": "0988888888"}, format="json")
        self.assertEqual(list(res.data), ["phone_number"])

    def test_email_change_requires_verification(self):
        res = self.client.patch("/api/me/", {"email": "Moi@Example.com"}, format="json")
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data["email"], "dan@example.com")  # unchanged until verified
        self.assertEqual(res.data["pending_email"], "moi@example.com")
        self.assertEqual(mail.outbox[-1].to, ["moi@example.com"])
        token = self.token_from_last_email()
        self.assertEqual(self.client.post("/api/auth/verify-email/", {"token": token},
                                          format="json").status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "moi@example.com")
        self.assertEqual(self.login("moi@example.com").status_code, 200)

    def test_citizen_cannot_clear_ward(self):
        res = self.client.patch("/api/me/", {"ward": None}, format="json")
        self.assertEqual(list(res.data), ["ward"])
