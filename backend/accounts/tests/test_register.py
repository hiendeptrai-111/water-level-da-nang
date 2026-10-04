"""Criteria a, b, g (registration)."""
from accounts.models import User

from .helpers import BaseAPITestCase


class RegisterTests(BaseAPITestCase):
    url = "/api/auth/register/"

    def post(self, **overrides):
        return self.client.post(self.url, self.register_payload(**overrides), format="json")

    def test_success_creates_unverified_citizen_and_sends_email(self):
        res = self.post()
        self.assertEqual(res.status_code, 201, res.data)
        user = User.objects.get(email="hien@gmail.com")
        self.assertEqual(user.role, User.Role.CITIZEN)
        self.assertFalse(user.email_verified)
        self.assertNotEqual(user.password, "Matkhau123")  # hashed
        self.assertTrue(user.check_password("Matkhau123"))
        self.assertEqual(len(self._outbox()), 1)
        self.assertIn("/verify-email?token=", self._outbox()[0].body)

    def _outbox(self):
        from django.core import mail
        return mail.outbox

    # a. missing email, wrong phone format, duplicate phone -> error on the right field
    def test_missing_email(self):
        data = self.register_payload()
        del data["email"]
        res = self.client.post(self.url, data, format="json")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(list(res.data), ["email"])

    def test_blank_email(self):
        res = self.post(email="")
        self.assertEqual(res.status_code, 400)
        self.assertIn("email", res.data)

    def test_invalid_email_format(self):
        res = self.post(email="khong-phai-email")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(list(res.data), ["email"])

    def test_wrong_phone_format(self):
        for bad in ["123", "1912345678", "091234567", "09123456789", "09123abc78"]:
            with self.subTest(phone=bad):
                res = self.post(phone_number=bad)
                self.assertEqual(res.status_code, 400)
                self.assertEqual(list(res.data), ["phone_number"], res.data)

    def test_duplicate_phone(self):
        self.make_user(email="khac@example.com", phone="0912345678")
        res = self.post()
        self.assertEqual(res.status_code, 400)
        self.assertEqual(list(res.data), ["phone_number"])
        self.assertIn("đã được sử dụng", str(res.data["phone_number"][0]))

    def test_password_rules(self):
        for pw, field in [("abc12", "password"), ("chiconchu", "password"),
                          ("12345678901", "password")]:
            with self.subTest(pw=pw):
                res = self.post(password=pw, password_confirm=pw)
                self.assertEqual(res.status_code, 400)
                self.assertIn(field, res.data)
        res = self.post(password_confirm="Khac12345")
        self.assertEqual(list(res.data), ["password_confirm"])

    def test_ward_required_and_must_exist(self):
        data = self.register_payload()
        del data["ward"]
        self.assertEqual(list(self.client.post(self.url, data, format="json").data), ["ward"])
        self.assertEqual(list(self.post(ward=99999).data), ["ward"])
        self.assertEqual(list(self.post(ward="Xã tự nhập").data), ["ward"])

    def test_terms_must_be_accepted(self):
        res = self.post(agree_terms=False)
        self.assertEqual(list(res.data), ["agree_terms"])

    def test_home_location_needs_both_coordinates(self):
        res = self.post(home_latitude="15.86")
        self.assertIn("home_latitude", res.data)
        res = self.post(home_latitude="15.860000", home_longitude="108.080000")
        self.assertEqual(res.status_code, 201, res.data)

    # b. same email with different case -> duplicate
    def test_duplicate_email_case_insensitive(self):
        self.assertEqual(self.post(email="Hien@gmail.com").status_code, 201)
        res = self.post(email="hien@gmail.com", phone_number="0987654321")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(list(res.data), ["email"])
        res = self.post(email="HIEN@GMAIL.COM", phone_number="0987654322")
        self.assertEqual(list(res.data), ["email"])
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(User.objects.get().email, "hien@gmail.com")

    def test_login_with_other_email_case(self):
        self.make_user(email="hien@gmail.com")
        self.assertEqual(self.login("HIEN@Gmail.com").status_code, 200)

    # g. no way to choose admin / rescue_team role when registering
    def test_cannot_self_assign_privileged_role(self):
        res = self.post(role="admin", is_staff=True, is_superuser=True,
                        rescue_team=self.team.pk, email_verified=True)
        self.assertEqual(res.status_code, 201, res.data)
        user = User.objects.get(email="hien@gmail.com")
        self.assertEqual(user.role, User.Role.CITIZEN)
        self.assertFalse(user.is_staff or user.is_superuser or user.email_verified)
        self.assertIsNone(user.rescue_team)

        res = self.post(email="b@example.com", phone_number="0900000999", role="rescue_team")
        self.assertEqual(User.objects.get(email="b@example.com").role, User.Role.CITIZEN)
