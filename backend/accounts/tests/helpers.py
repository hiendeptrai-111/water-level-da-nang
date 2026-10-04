from django.core import mail
from django.core.cache import cache
from rest_framework.test import APITestCase

from accounts.models import User
from catalog.models import RescueTeam, Ward

PASSWORD = "Matkhau123"


class BaseAPITestCase(APITestCase):
    def setUp(self):
        cache.clear()  # throttling counters
        mail.outbox = []
        self.ward = Ward.objects.create(name="Đại Lộc", kind=Ward.Kind.COMMUNE, priority=3)
        self.ward2 = Ward.objects.create(name="Hội An", kind=Ward.Kind.WARD, priority=3)
        self.team = RescueTeam.objects.create(name="Đội test", phone_number="0905111222",
                                              vehicles=["boat"])

    def make_user(self, email="dan@example.com", phone="0911111111", role=User.Role.CITIZEN,
                  verified=True, **extra):
        if role == User.Role.RESCUE_TEAM:
            extra.setdefault("rescue_team", self.team)
        if role == User.Role.CITIZEN:
            extra.setdefault("ward", self.ward)
        return User.objects.create_user(email=email, password=PASSWORD, full_name="Người Thử",
                                        phone_number=phone, role=role, email_verified=verified,
                                        **extra)

    def register_payload(self, **overrides):
        data = {
            "full_name": "Trần Văn Hiền", "phone_number": "0912345678",
            "email": "hien@gmail.com", "password": PASSWORD, "password_confirm": PASSWORD,
            "ward": self.ward.pk, "address_detail": "Thôn 1", "agree_terms": True,
        }
        data.update(overrides)
        return data

    def login(self, identifier, password=PASSWORD):
        return self.client.post("/api/auth/login/", {"identifier": identifier,
                                                     "password": password}, format="json")

    def auth(self, user):
        """Log in through the API and attach the access token."""
        res = self.login(user.email)
        assert res.status_code == 200, res.data
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")
        return res.data

    def token_from_last_email(self):
        body = mail.outbox[-1].body
        return body.split("token=")[1].split()[0]
