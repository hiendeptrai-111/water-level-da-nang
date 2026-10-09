"""Criterion g (CN10): notify on a rise; a lasting "warning" is repeated every 3 hours only;
rescue teams never receive "watch". The level always comes from the du_bao() result."""
from datetime import timedelta
from unittest import mock

import pandas as pd
from django.core import mail

from accounts.models import User
from accounts.tests.helpers import BaseAPITestCase
from alerts.models import Alert, Notification
from alerts.services import evaluate
from reservoirs.forecasting import save_forecast, to_aware, to_naive_local
from reservoirs.models import Reservoir, ReservoirWard

T0 = "2025-10-27 00:00"
MODEL_LEVEL = {"normal": "binh_thuong", "watch": "theo_doi", "warning": "canh_bao"}


def fake_result(level, suspicious=False):
    """Same shape as du_bao(): overall level + one entry per horizon."""
    model = MODEL_LEVEL[level]
    horizon = {"muc_nuoc_du_kien": 376.5, "thay_doi_du_kien_m": 0.42, "baseline_bao": level == "warning",
               "A_bao": level == "warning", "B_bao": level != "normal", "xac_suat_xgb": 0.9,
               "muc_canh_bao": model, "muc_canh_bao_tu_mo_hinh": model,
               "can_xac_nhan": suspicious, "ly_do_can_xac_nhan": None, "canh_bao_du_lieu": []}
    return {"ho": "a_vuong", "ten_ho": "A Vương", "muc_canh_bao_chung": model,
            "can_xac_nhan": suspicious, "ly_do_can_xac_nhan": None,
            "1h": dict(horizon), "3h": dict(horizon), "6h": dict(horizon, muc_nuoc_du_kien=None, A_bao=None)}


class AutoAlertTests(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        self.res = Reservoir.objects.create(code="av", model_key="a_vuong", name="A Vương",
                                            normal_water_level=380)
        ReservoirWard.objects.create(reservoir=self.res, ward=self.ward, zone="delta_downstream")
        self.admin = self.make_user("admin@example.com", "0922222222", role=User.Role.ADMIN)
        self.rescue = self.make_user("doi@example.com", "0933333333", role=User.Role.RESCUE_TEAM)
        self.citizen = self.make_user()
        self.hour = 0

    def step(self, level, simulation=False):
        t = to_aware(pd.Timestamp(T0)) + timedelta(hours=self.hour)
        self.hour += 1
        result = fake_result(level)
        rows = save_forecast(self.res, to_naive_local(t), result, is_simulation=simulation)
        return evaluate(self.res, t, result, rows, simulation=simulation, send_email=True)

    def web(self, user):
        return Notification.objects.filter(recipient=user, channel="web")

    def test_rise_then_reminder_every_three_hours(self):
        self.step("normal")                                   # h0
        self.assertEqual(Notification.objects.count(), 0)

        self.step("watch")                                    # h1: rise -> admin only
        self.assertEqual(self.web(self.admin).count(), 1)
        self.assertEqual(self.web(self.rescue).count(), 0)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.admin.email])

        self.step("warning")                                  # h2: rise -> admin + rescue
        self.assertEqual(self.web(self.admin).count(), 2)
        self.assertEqual(self.web(self.rescue).count(), 1)
        watch = Alert.objects.get(level="watch")
        self.assertIsNotNone(watch.ended_at)                  # the watch episode ended

        self.step("warning")                                  # h3: +1 hour -> nothing
        self.step("warning")                                  # h4: +2 hours -> nothing
        self.assertEqual(self.web(self.admin).count(), 2)
        self.assertEqual(self.web(self.rescue).count(), 1)

        self.step("warning")                                  # h5: +3 hours -> reminder
        self.assertEqual(self.web(self.admin).count(), 3)
        self.assertEqual(self.web(self.rescue).count(), 2)
        reminder = self.web(self.rescue).first()
        self.assertTrue(reminder.is_reminder)
        self.assertTrue(reminder.content.startswith("Nhắc lại"))

        self.step("warning")                                  # h6
        self.step("warning")                                  # h7
        self.assertEqual(self.web(self.rescue).count(), 2)
        self.step("warning")                                  # h8: +3 after h5
        self.assertEqual(self.web(self.rescue).count(), 3)

        # rescue teams never got a "watch" notification; citizens got nothing
        self.assertFalse(self.web(self.rescue).filter(alert__level="watch").exists())
        self.assertEqual(Notification.objects.filter(recipient=self.citizen).count(), 0)
        # one warning episode, still open, linked to the downstream commune
        warning = Alert.objects.get(level="warning")
        self.assertIsNone(warning.ended_at)
        self.assertEqual(list(warning.wards.all()), [self.ward])

    def test_watch_lasting_is_not_repeated(self):
        self.step("watch")
        for _ in range(6):
            self.step("watch")
        self.assertEqual(self.web(self.admin).count(), 1)

    def test_fall_ends_alert_without_notification(self):
        self.step("warning")
        n = Notification.objects.count()
        self.step("watch")
        self.step("normal")
        self.assertEqual(Notification.objects.count(), n)
        self.assertFalse(Alert.objects.filter(ended_at__isnull=True).exists())
        self.step("warning")                                  # a new rise notifies again
        self.assertEqual(self.web(self.rescue).count(), 2)

    def test_same_hour_twice_is_ignored(self):
        t = to_aware(pd.Timestamp(T0))
        result = fake_result("warning")
        rows = save_forecast(self.res, to_naive_local(t), result)
        evaluate(self.res, t, result, rows)
        self.assertEqual(evaluate(self.res, t, result, rows), "đã xét giờ này")
        self.assertEqual(self.web(self.admin).count(), 1)

    def test_simulation_never_emails(self):
        self.step("warning", simulation=True)
        self.assertEqual(mail.outbox, [])
        self.assertTrue(Alert.objects.get().is_simulation)


class NotificationApiTests(AutoAlertTests):
    def test_seen_records_who_and_when(self):
        self.step("warning")
        self.auth(self.rescue)
        res = self.client.get("/api/notifications/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["unseen_count"], 1)
        note = res.data["results"][0]
        self.assertIn("A Vương", note["content"])
        seen = self.client.post(f"/api/notifications/{note['id']}/seen/")
        self.assertEqual(seen.status_code, 200)
        self.assertIsNotNone(seen.data["seen_at"])
        self.assertEqual(self.client.get("/api/notifications/").data["unseen_count"], 0)
        # e-mail copy acknowledged too; the admin's own notification untouched
        self.assertFalse(Notification.objects.filter(recipient=self.rescue, seen_at__isnull=True).exists())
        self.assertTrue(Notification.objects.filter(recipient=self.admin, seen_at__isnull=True).exists())

    def test_cannot_mark_someone_elses_notification(self):
        self.step("warning")
        other = Notification.objects.filter(recipient=self.admin, channel="web").first()
        self.auth(self.rescue)
        self.assertEqual(self.client.post(f"/api/notifications/{other.pk}/seen/").status_code, 404)

    def test_public_alert_list(self):
        now = to_aware(pd.Timestamp(T0)) + timedelta(hours=1, minutes=30)
        patcher = mock.patch("django.utils.timezone.now", return_value=now)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.step("watch")
        self.assertEqual(self.client.get("/api/alerts/").json()["alerts"], [])   # watch: admins only
        self.step("warning")
        self.auth(self.citizen)
        alerts = self.client.get("/api/alerts/").json()["alerts"]
        self.assertEqual(len(alerts), 1)
        self.assertTrue(alerts[0]["in_my_ward"])
        self.assertNotIn("issued_by", alerts[0])
