"""Criteria b, c, d, i: stored forecasts, missing / stale data, replay."""
import json
from unittest import skipUnless

import pandas as pd
from django.core import mail

from alerts.models import Alert, Notification
from reservoirs.forecasting import modules
from reservoirs.models import Forecast, OperationRecord, Reservoir
from reservoirs.pipeline import forecast_one, run_replay
from core.services import get_config

from .helpers import END, RAMP_HOURS, REAL_STORE, START, ReservoirTestCase, aware, real_frames

PREFIX = {"a_vuong": "av", "dak_mi_4": "dm", "song_bung_4": "sb", "song_tranh_2": "st"}


def direct_frame(ops, rains, model_key, t, hours):
    """du_bao() input built straight from the data files (not through the database)."""
    p = PREFIX[model_key]
    grid = pd.date_range(t - pd.Timedelta(hours=hours - 1), t, freq="h", name="thoi_gian")
    frame = pd.DataFrame({k: ops[f"{p}_{k}"] for k in ("mn", "den", "may", "tran")}).reindex(grid)
    frame["mua"] = rains[model_key].reindex(grid)
    return frame.astype(float)


class StoredForecastMatchesDirectCall(ReservoirTestCase):
    """b. The forecast stored in the DB equals du_bao() called directly on the same data."""
    times = [START + pd.Timedelta(hours=h) for h in (200, 260, 320, 380, 399)]

    def test_five_times_all_reservoirs(self):
        n = get_config("forecast_input_hours")
        for res in Reservoir.objects.all():
            for t in self.times:
                with self.subTest(reservoir=res.code, t=t):
                    forecast_one(res, t, simulation=False)
                    expected = modules().du_bao(res.model_key,
                                                direct_frame(self.ops, self.rains, res.model_key, t, n))
                    expected = json.loads(json.dumps(expected))
                    rows = Forecast.objects.filter(reservoir=res, issued_at=aware(t),
                                                   is_simulation=False).order_by("horizon")
                    self.assertEqual(len(rows), 3)
                    for row in rows:
                        self.assertEqual(row.details, expected)
                        h = expected[f"{row.horizon}h"]
                        self.assertEqual(row.expected_level, h["muc_nuoc_du_kien"])
                        self.assertEqual(row.baseline_alert, h["baseline_bao"])
                        self.assertEqual(row.a_alert, h["A_bao"])
                        self.assertEqual(row.b_alert, h["B_bao"])
                    # 1h and 3h have a water level here (enough clean data)
                    self.assertIsNotNone(rows[0].expected_level)


@skipUnless((REAL_STORE / "van_hanh" / "van_hanh.csv").exists(), "chưa có kho_du_lieu/ trên máy này")
class StoredForecastMatchesDirectCallRealData(StoredForecastMatchesDirectCall):
    """b, on a slice of the real data store (October 2025 flood)."""
    frames = staticmethod(lambda: real_frames("2025-10-01 00:00", "2025-10-31 23:00"))
    times = [pd.Timestamp(t) for t in ("2025-10-20 08:00", "2025-10-26 18:00", "2025-10-27 06:00",
                                       "2025-10-28 12:00", "2025-10-30 23:00")]


class MissingAndStaleData(ReservoirTestCase):
    def setUp(self):
        super().setUp()
        self.av = Reservoir.objects.get(code="av")
        self.dm = Reservoir.objects.get(code="dm")

    def get(self, code):
        res = self.client.get(f"/api/reservoirs/{code}/")
        self.assertEqual(res.status_code, 200)
        return res.json()

    # c. latest hour missing -> no forecast from the API
    def test_missing_latest_hour_gives_no_forecast(self):
        OperationRecord.objects.filter(reservoir=self.av, time=aware(END)).update(water_level=None)
        for res in (self.av, self.dm):
            forecast_one(res, END, simulation=False)
        self.at(END, minutes=30)
        av = self.get("av")
        self.assertFalse(av["forecast_available"])
        self.assertEqual(av["forecast"], [])
        self.assertEqual(av["forecast_message"], "Chưa đủ dữ liệu để dự báo")
        self.assertIsNone(av["alert_level"])
        forecast = self.client.get("/api/reservoirs/av/forecast/").json()
        self.assertFalse(forecast["forecast_available"])
        self.assertEqual(forecast["forecast"], [])
        # control: Đăk Mi 4 has its latest hour -> forecast shown
        dm = self.get("dm")
        self.assertTrue(dm["forecast_available"])
        self.assertEqual([f["horizon"] for f in dm["forecast"]], [1, 3, 6])

    # d. data older than 2 hours -> stale flag, and no forecast
    def test_stale_flag_after_two_hours(self):
        forecast_one(self.dm, END, simulation=False)
        self.at(END, minutes=60)
        fresh = self.get("dm")
        self.assertFalse(fresh["stale"])
        self.assertTrue(fresh["forecast_available"])

    def test_stale_flag_true_when_older(self):
        forecast_one(self.dm, END, simulation=False)
        self.at(END, minutes=3 * 60)
        old = self.get("dm")
        self.assertTrue(old["stale"])
        self.assertFalse(old["forecast_available"])
        listing = self.client.get("/api/reservoirs/").json()["reservoirs"]
        self.assertTrue(all(r["stale"] for r in listing))

    def test_public_data_has_no_personal_information(self):
        self.make_staff()
        from reservoirs.models import OperatingDirective
        OperatingDirective.objects.create(reservoir=self.av, requirement="lower_to",
                                          target_level=373, document="CV test",
                                          entered_by=self.admin)
        body = self.client.get("/api/reservoirs/av/").content.decode()
        self.assertIn("CV test", body)
        self.assertNotIn("entered_by", body)
        self.assertNotIn(self.admin.email, body)
        self.assertNotIn(self.admin.full_name, body)


class ReplayTests(ReservoirTestCase):
    """i. Replay sends no email and never overwrites live results."""

    def test_replay_sends_no_email_and_keeps_live_rows(self):
        self.make_staff()
        av = Reservoir.objects.get(code="av")
        live_t = END - pd.Timedelta(hours=2)
        forecast_one(av, live_t, simulation=False)
        live = {f.horizon: (f.pk, f.expected_level, f.alert_level, f.details)
                for f in Forecast.objects.filter(is_simulation=False)}
        mail.outbox = []

        start = END - pd.Timedelta(hours=RAMP_HOURS)
        run = run_replay(start, END, web_notifications=True)
        self.assertEqual(run.failures, 0)

        self.assertEqual(mail.outbox, [])
        self.assertEqual({f.horizon: (f.pk, f.expected_level, f.alert_level, f.details)
                          for f in Forecast.objects.filter(is_simulation=False)}, live)
        hours = RAMP_HOURS + 1
        self.assertEqual(Forecast.objects.filter(is_simulation=True).count(), 4 * hours * 3)
        # the A Vương rise produced simulated alerts and (web only) notifications
        sim_alerts = Alert.objects.filter(is_simulation=True)
        self.assertTrue(sim_alerts.filter(level="warning").exists())
        self.assertFalse(Alert.objects.filter(is_simulation=False).exists())
        notes = Notification.objects.filter(alert__is_simulation=True)
        self.assertTrue(notes.exists())
        self.assertFalse(notes.exclude(channel="web").exists())
        self.assertTrue(all(n.content.startswith("[MÔ PHỎNG]") for n in notes))

    def test_replay_view_is_marked_simulation(self):
        start = END - pd.Timedelta(hours=5)
        run_replay(start, END)
        res = self.client.get("/api/reservoirs/?simulation=1").json()
        self.assertTrue(res["simulation"])
        self.assertTrue(all(r["simulation"] for r in res["reservoirs"]))
        live = self.client.get("/api/reservoirs/").json()
        self.assertFalse(any(r["forecast_available"] for r in live["reservoirs"]))
