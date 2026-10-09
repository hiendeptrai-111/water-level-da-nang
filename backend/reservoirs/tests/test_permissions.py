"""Criterion h: citizens and rescue teams get 403 on every phase-2 admin API."""
from .helpers import ReservoirTestCase

ADMIN_ENDPOINTS = [
    ("get", "/api/admin/thresholds/"),
    ("get", "/api/admin/directives/"),
    ("post", "/api/admin/directives/"),
    ("get", "/api/admin/alerts/"),
    ("get", "/api/admin/data-status/"),
    ("get", "/api/admin/reservoirs/av/export/?from=2025-10-01&to=2025-10-02"),
]


class Phase2PermissionTests(ReservoirTestCase):
    def setUp(self):
        super().setUp()
        self.make_staff()
        from reservoirs.models import OperatingDirective, RegulatoryThreshold
        self.threshold = RegulatoryThreshold.objects.first()
        self.directive = OperatingDirective.objects.first()

    def endpoints(self):
        return ADMIN_ENDPOINTS + [
            ("patch", f"/api/admin/thresholds/{self.threshold.pk}/"),
            ("get", f"/api/admin/directives/{self.directive.pk}/"),
            ("post", f"/api/admin/directives/{self.directive.pk}/deactivate/"),
        ]

    def call_all(self, expected):
        for method, url in self.endpoints():
            with self.subTest(method=method, url=url):
                res = getattr(self.client, method)(url, {"value_low": 1}, format="json")
                self.assertEqual(res.status_code, expected)

    def test_citizen_gets_403(self):
        self.auth(self.citizen)
        self.call_all(403)

    def test_rescue_team_gets_403(self):
        self.auth(self.rescue)
        self.call_all(403)

    def test_anonymous_gets_401(self):
        self.call_all(401)

    def test_admin_allowed(self):
        self.auth(self.admin)
        for method, url in ADMIN_ENDPOINTS:
            if method == "get":
                with self.subTest(url=url):
                    self.assertEqual(self.client.get(url).status_code, 200)

    def test_public_endpoints_need_no_login(self):
        for url in ("/api/reservoirs/", "/api/reservoirs/av/", "/api/reservoirs/av/forecast/",
                    "/api/reservoirs/av/history/", "/api/alerts/", "/api/reservoirs/simulation/"):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_history_limited_to_90_days(self):
        res = self.client.get("/api/reservoirs/av/history/?from=2025-01-01&to=2025-06-01")
        self.assertEqual(res.status_code, 400)
        ok = self.client.get("/api/reservoirs/av/history/?from=2025-10-01&to=2025-10-17")
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(len(ok.json()["points"]), 400)
