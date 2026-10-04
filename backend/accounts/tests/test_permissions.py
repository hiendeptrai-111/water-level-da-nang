"""Criteria f, g (role checks in the API)."""
from accounts.models import User

from .helpers import BaseAPITestCase

ADMIN_ENDPOINTS = [
    ("get", "/api/admin/users/"),
    ("post", "/api/admin/users/"),
    ("get", "/api/admin/audit-logs/"),
    ("get", "/api/admin/config/"),
    ("patch", "/api/admin/config/jwt_access_minutes/"),
    ("get", "/api/admin/rescue-teams/"),
]


class PermissionTests(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        self.citizen = self.make_user()
        self.rescue = self.make_user("doi@example.com", "0933333333", role=User.Role.RESCUE_TEAM)
        self.admin = self.make_user("admin@example.com", "0922222222", role=User.Role.ADMIN)

    def call_all(self, expected):
        target = self.citizen.pk
        endpoints = ADMIN_ENDPOINTS + [
            ("get", f"/api/admin/users/{target}/"),
            ("patch", f"/api/admin/users/{target}/"),
            ("post", f"/api/admin/users/{target}/lock/"),
            ("post", f"/api/admin/users/{target}/unlock/"),
            ("post", f"/api/admin/users/{target}/change-role/"),
            ("post", f"/api/admin/users/{target}/reset-password/"),
        ]
        for method, url in endpoints:
            with self.subTest(method=method, url=url):
                res = getattr(self.client, method)(url, {"role": "admin", "value": 1},
                                                   format="json")
                self.assertEqual(res.status_code, expected, res.data)

    # f. citizen and rescue team -> 403 on every admin API
    def test_citizen_gets_403(self):
        self.auth(self.citizen)
        self.call_all(403)
        self.citizen.refresh_from_db()
        self.assertEqual(self.citizen.role, User.Role.CITIZEN)
        self.assertTrue(self.citizen.is_active)

    def test_rescue_team_gets_403(self):
        self.auth(self.rescue)
        self.call_all(403)

    def test_anonymous_gets_401(self):
        self.call_all(401)

    def test_admin_allowed(self):
        self.auth(self.admin)
        res = self.client.get("/api/admin/users/")
        self.assertEqual(res.status_code, 200)
        labels = {u["email"]: u["ward_label"] for u in res.data}
        self.assertEqual(labels["dan@example.com"], "Xã Đại Lộc")
        self.assertIsNone(labels["doi@example.com"])  # no ward -> null, not a repr
        self.assertIsNone(self.client.get("/api/me/").data["ward_label"])

    # g. a citizen cannot raise their own role through the profile API either
    def test_profile_update_cannot_change_role(self):
        self.auth(self.citizen)
        res = self.client.patch("/api/me/", {"role": "admin", "is_staff": True,
                                             "email_verified": False,
                                             "rescue_team": self.team.pk,
                                             "full_name": "Tên Mới"}, format="json")
        self.assertEqual(res.status_code, 200, res.data)
        self.citizen.refresh_from_db()
        self.assertEqual(self.citizen.full_name, "Tên Mới")
        self.assertEqual(self.citizen.role, User.Role.CITIZEN)
        self.assertFalse(self.citizen.is_staff)
        self.assertTrue(self.citizen.email_verified)
        self.assertIsNone(self.citizen.rescue_team)

    def test_only_admin_urls_can_set_a_role(self):
        """Walk every URL: the only route that changes a role lives under /api/admin/."""
        from django.urls import URLPattern, URLResolver, get_resolver

        def walk(patterns, prefix=""):
            for p in patterns:
                if isinstance(p, URLResolver):
                    yield from walk(p.url_patterns, prefix + str(p.pattern))
                elif isinstance(p, URLPattern):
                    yield (prefix + str(p.pattern)).replace("^", "").replace("$", "")

        api_routes = [r for r in walk(get_resolver().url_patterns) if r.startswith("api/")]
        role_routes = [r for r in api_routes if "role" in r]
        self.assertTrue(role_routes)
        self.assertTrue(all(r.startswith("api/admin/") for r in role_routes), role_routes)


class AdminUserManagementTests(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        self.admin = self.make_user("admin@example.com", "0922222222", role=User.Role.ADMIN)
        self.auth(self.admin)

    def test_create_rescue_account(self):
        res = self.client.post("/api/admin/users/", {
            "full_name": "Đội Một", "phone_number": "0944444444", "email": "Doi1@Example.com",
            "role": "rescue_team", "rescue_team": self.team.pk}, format="json")
        self.assertEqual(res.status_code, 201, res.data)
        self.assertTrue(res.data["temporary_password"])
        user = User.objects.get(email="doi1@example.com")
        self.assertEqual(user.rescue_team, self.team)
        self.assertTrue(user.email_verified)
        self.assertEqual(self.login("doi1@example.com", res.data["temporary_password"])
                         .status_code, 200)

    def test_rescue_account_requires_team_and_admin_cannot_create_citizen(self):
        base = {"full_name": "X Y", "phone_number": "0944444444", "email": "x@example.com"}
        res = self.client.post("/api/admin/users/", {**base, "role": "rescue_team"}, format="json")
        self.assertEqual(list(res.data), ["rescue_team"])
        res = self.client.post("/api/admin/users/", {**base, "role": "citizen"}, format="json")
        self.assertEqual(list(res.data), ["role"])

    def test_lock_unlock_change_role_reset_password(self):
        citizen = self.make_user()
        tokens = self.login("dan@example.com").data
        self.assertEqual(self.client.post(f"/api/admin/users/{citizen.pk}/lock/").status_code, 200)
        citizen.refresh_from_db()
        self.assertFalse(citizen.is_active)
        # existing sessions of the locked user stop working
        res = self.client.post("/api/auth/token/refresh/", {"refresh": tokens["refresh"]},
                               format="json")
        self.assertEqual(res.status_code, 401)
        self.assertEqual(self.client.post(f"/api/admin/users/{citizen.pk}/unlock/").status_code, 200)

        res = self.client.post(f"/api/admin/users/{citizen.pk}/change-role/",
                               {"role": "rescue_team", "rescue_team": self.team.pk}, format="json")
        self.assertEqual(res.status_code, 200, res.data)
        citizen.refresh_from_db()
        self.assertEqual((citizen.role, citizen.rescue_team), ("rescue_team", self.team))

        res = self.client.post(f"/api/admin/users/{citizen.pk}/change-role/", {"role": "citizen"},
                               format="json")
        citizen.refresh_from_db()
        self.assertEqual((citizen.role, citizen.rescue_team), ("citizen", None))

        res = self.client.post(f"/api/admin/users/{citizen.pk}/reset-password/")
        self.assertEqual(self.login("dan@example.com", res.data["temporary_password"]).status_code,
                         200)

        from core.models import AuditLog
        actions = list(AuditLog.objects.filter(target_id=str(citizen.pk))
                       .values_list("action", flat=True))
        for a in ["user_locked", "user_unlocked", "role_changed", "password_reset_by_admin"]:
            self.assertIn(a, actions)

    def test_admin_cannot_lock_or_demote_self(self):
        self.assertEqual(self.client.post(f"/api/admin/users/{self.admin.pk}/lock/").status_code, 400)
        res = self.client.post(f"/api/admin/users/{self.admin.pk}/change-role/",
                               {"role": "citizen"}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_no_delete_endpoint(self):
        citizen = self.make_user()
        self.assertEqual(self.client.delete(f"/api/admin/users/{citizen.pk}/").status_code, 405)
