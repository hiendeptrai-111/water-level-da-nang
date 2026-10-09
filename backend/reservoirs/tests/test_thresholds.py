"""Criteria e, f: threshold period by date; directives cannot be deleted."""
from datetime import date

from core.models import AuditLog
from reservoirs.models import OperatingDirective, Reservoir
from reservoirs.services import threshold_block

from .helpers import ReservoirTestCase


class ThresholdPeriodTests(ReservoirTestCase):
    def setUp(self):
        super().setUp()
        self.av = Reservoir.objects.get(code="av")

    # e.
    def test_period_by_date(self):
        oct10 = threshold_block(self.av, date(2025, 10, 10))
        self.assertTrue(oct10["in_season"])
        self.assertEqual(oct10["period"], "01/9 – 15/11")
        self.assertEqual({i["kind"]: (i["value_low"], i["value_high"]) for i in oct10["items"]},
                         {"max_before_flood": (376, 376), "min_flood_reception": (370, 370)})

        nov20 = threshold_block(self.av, date(2025, 11, 20))
        self.assertEqual(nov20["period"], "16/11 – 15/12")
        self.assertEqual({i["kind"]: (i["value_low"], i["value_high"]) for i in nov20["items"]},
                         {"max_before_flood": (377, 380), "min_flood_reception": (377, 377)})

        mar1 = threshold_block(self.av, date(2026, 3, 1))
        self.assertFalse(mar1["in_season"])
        self.assertEqual(mar1["label"], "Ngoài mùa lũ")
        self.assertEqual(mar1["items"], [])

    def test_boundaries(self):
        self.assertEqual(threshold_block(self.av, date(2025, 11, 15))["period"], "01/9 – 15/11")
        self.assertEqual(threshold_block(self.av, date(2025, 11, 16))["period"], "16/11 – 15/12")
        self.assertFalse(threshold_block(self.av, date(2025, 12, 16))["in_season"])
        self.assertFalse(threshold_block(self.av, date(2025, 8, 31))["in_season"])

    def test_api_returns_current_period(self):
        self.at("2025-11-20 10:00")
        body = self.client.get("/api/reservoirs/av/").json()
        self.assertEqual(body["thresholds"]["label"], "Thời kỳ 16/11 – 15/12")


class DirectiveTests(ReservoirTestCase):
    def setUp(self):
        super().setUp()
        self.make_staff()
        self.auth(self.admin)

    def create(self):
        res = self.client.post("/api/admin/directives/", {
            "reservoir": "av", "requirement": "lower_to", "target_level": 373,
            "starts_at": "2025-11-05T08:00", "deadline": "2025-11-06T22:00",
            "document": "3542/UBND-PTDS, 05/11/2025"}, format="json")
        self.assertEqual(res.status_code, 201, res.data)
        return res.data["id"]

    # f.
    def test_cannot_delete_through_api(self):
        pk = self.create()
        before = OperatingDirective.objects.count()
        self.assertEqual(self.client.delete(f"/api/admin/directives/{pk}/").status_code, 405)
        self.assertEqual(self.client.patch(f"/api/admin/directives/{pk}/", {"is_active": False},
                                           format="json").status_code, 405)
        self.assertEqual(self.client.put(f"/api/admin/directives/{pk}/", {}, format="json")
                         .status_code, 405)
        self.assertEqual(OperatingDirective.objects.count(), before)
        self.assertTrue(OperatingDirective.objects.get(pk=pk).is_active)
        with self.assertRaises(PermissionError):
            OperatingDirective.objects.get(pk=pk).delete()
        with self.assertRaises(PermissionError):
            OperatingDirective.objects.all().delete()

    def test_deactivate_keeps_history_and_is_logged(self):
        pk = self.create()
        public = self.client.get("/api/reservoirs/av/").json()
        self.assertEqual([d["target_level"] for d in public["directives"]], [373])
        res = self.client.post(f"/api/admin/directives/{pk}/deactivate/")
        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.data["is_active"])
        self.assertEqual(self.client.get("/api/reservoirs/av/").json()["directives"], [])
        self.assertTrue(OperatingDirective.objects.filter(pk=pk).exists())
        actions = list(AuditLog.objects.values_list("action", flat=True))
        self.assertIn(AuditLog.Action.DIRECTIVE_CREATED, actions)
        self.assertIn(AuditLog.Action.DIRECTIVE_DEACTIVATED, actions)

    def test_threshold_edit_is_logged(self):
        t = self.client.get("/api/admin/thresholds/").json()[0]
        res = self.client.patch(f"/api/admin/thresholds/{t['id']}/", {"value_high": t["value_high"] + 1},
                                format="json")
        self.assertEqual(res.status_code, 200, res.data)
        self.assertTrue(AuditLog.objects.filter(action=AuditLog.Action.THRESHOLD_CHANGED).exists())
        bad = self.client.patch(f"/api/admin/thresholds/{t['id']}/", {"value_low": 999}, format="json")
        self.assertEqual(bad.status_code, 400)
