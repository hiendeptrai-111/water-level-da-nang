"""Phase 3 criteria a–h: ward coordinates, weather cache, weather API."""
import io
import tempfile
import urllib.error
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from unittest import mock

from django.core.management import call_command
from django.utils import timezone

from accounts.models import User
from accounts.tests.helpers import BaseAPITestCase
from catalog import geo
from catalog.models import Ward
from core.models import AuditLog
from reservoirs.models import UpdateRun
from reservoirs.pipeline import Run, step_weather
from weather import services
from weather.models import WeatherReading

T = timezone.make_aware(datetime(2025, 10, 27, 12, 0))      # "now" of the fake download


def rain_at(t):
    """Known hourly rain so 24-hour totals can be computed by hand."""
    return round((t.hour % 5) * 0.3 + (t.day % 3) * 0.1, 2)


def fake_payload(wards, now=T):
    """Open-Meteo-like answer: yesterday 00:00 .. +4 days, one structure per location."""
    start = timezone.localtime(now).replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
    times = [start + timedelta(hours=i) for i in range(24 * 5)]
    hourly = {"time": [timezone.localtime(t).strftime("%Y-%m-%dT%H:%M") for t in times],
              "temperature_2m": [25.0 + i % 7 for i in range(len(times))],
              "precipitation": [rain_at(timezone.localtime(t)) for t in times],
              "wind_speed_10m": [5.0] * len(times)}
    return [{"timezone": "Asia/Bangkok", "hourly_units": services.UNITS, "hourly": hourly}
            for _ in wards]


class WeatherTestCase(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        call_command("load_wards", verbosity=0)
        call_command("load_ward_centroids", verbosity=0)
        self.dai_loc = Ward.objects.get(kind="commune", name="Đại Lộc")
        self.hoang_sa = Ward.objects.get(kind="special_zone")

    def load_fake(self, now=T):
        wards = list(Ward.objects.filter(latitude__isnull=False).order_by("id"))
        with mock.patch.object(services, "http_get_json", return_value=fake_payload(wards, now)):
            services.store(services.fetch(wards), now)


class CoordinateLoadTests(WeatherTestCase):
    # a.
    def test_load_twice_duplicates_nothing(self):
        before = list(Ward.objects.order_by("id").values_list("id", "latitude", "longitude",
                                                              "coord_confidence"))
        out = io.StringIO()
        call_command("load_ward_centroids", stdout=out)
        self.assertEqual(Ward.objects.count(), 94)
        self.assertEqual(list(Ward.objects.order_by("id").values_list(
            "id", "latitude", "longitude", "coord_confidence")), before)
        self.assertEqual(Ward.objects.filter(coord_confidence="boundary").count(), 93)
        self.assertIsNone(self.hoang_sa.latitude)

    def test_manual_coordinates_survive_reload(self):
        set_by_admin = (Decimal("15.900000"), Decimal("108.100000"))
        self.dai_loc.latitude, self.dai_loc.longitude = set_by_admin
        self.dai_loc.coord_confidence = Ward.Confidence.MANUAL
        self.dai_loc.save()
        call_command("load_ward_centroids", verbosity=0)
        self.dai_loc.refresh_from_db()
        self.assertEqual((self.dai_loc.latitude, self.dai_loc.longitude), set_by_admin)

    # b.
    def test_coordinates_outside_da_nang_are_dropped(self):
        self.assertTrue(geo.in_da_nang(16.0678, 108.2208))     # Hai Chau
        self.assertFalse(geo.in_da_nang(21.0285, 105.8542))    # Ha Noi
        self.assertFalse(geo.in_da_nang(16.5, 112.0))          # offshore, outside the boundary
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "c.csv"
            path.write_text(
                "kind,name,latitude,longitude,source,confidence,osm_id,note\n"
                "commune,Đại Lộc,21.0285,105.8542,test,boundary,R1,\n"
                "ward,Hải Châu,16.0678,108.2208,test,boundary,R2,\n", encoding="utf-8")
            out = io.StringIO()
            call_command("load_ward_centroids", file=str(path), stdout=out)
        self.dai_loc.refresh_from_db()
        self.assertIsNone(self.dai_loc.latitude)
        self.assertEqual(self.dai_loc.coord_confidence, "missing")
        self.assertIn("ngoài TP Đà Nẵng", self.dai_loc.coord_note)
        self.assertIn("'rejected': 1", out.getvalue())
        hai_chau = Ward.objects.get(kind="ward", name="Hải Châu")
        self.assertEqual(hai_chau.latitude, Decimal("16.067800"))


class CoordinateEditTests(WeatherTestCase):
    def setUp(self):
        super().setUp()
        self.admin = self.make_user("admin@example.com", "0922222222", role=User.Role.ADMIN)
        self.rescue = self.make_user("doi@example.com", "0933333333", role=User.Role.RESCUE_TEAM)
        self.citizen = self.make_user()
        self.url = f"/api/admin/wards/{self.dai_loc.pk}/"
        self.body = {"latitude": "15.880000", "longitude": "108.090000"}

    # h.
    def test_citizen_and_rescue_get_403(self):
        old = (self.dai_loc.latitude, self.dai_loc.longitude)
        for user in (self.citizen, self.rescue):
            with self.subTest(role=user.role):
                self.auth(user)
                self.assertEqual(self.client.patch(self.url, self.body, format="json").status_code, 403)
        self.client.credentials()
        self.assertEqual(self.client.patch(self.url, self.body, format="json").status_code, 401)
        self.dai_loc.refresh_from_db()
        self.assertEqual((self.dai_loc.latitude, self.dai_loc.longitude), old)

    def test_admin_edit_is_validated_and_logged(self):
        self.auth(self.admin)
        res = self.client.patch(self.url, self.body, format="json")
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data["coord_confidence"], "manual")
        log = AuditLog.objects.get(action=AuditLog.Action.WARD_COORDS_CHANGED)
        self.assertEqual(log.target_id, str(self.dai_loc.pk))
        bad = self.client.patch(self.url, {"latitude": "21.0285", "longitude": "105.8542"}, format="json")
        self.assertEqual(bad.status_code, 400)

    def test_django_admin_edit_is_logged(self):
        self.client.force_login(self.admin)
        url = f"/django-admin/catalog/ward/{self.dai_loc.pk}/change/"
        page = self.client.get(url, SERVER_NAME="localhost")
        self.assertEqual(page.status_code, 200)
        form = {"priority": 3, "latitude": "15.880000", "longitude": "108.090000",
                "reservoir_links-TOTAL_FORMS": 0, "reservoir_links-INITIAL_FORMS": 0}
        res = self.client.post(url, form, SERVER_NAME="localhost")
        self.assertEqual(res.status_code, 302, getattr(res, "context", None) and res.context["errors"])
        self.dai_loc.refresh_from_db()
        self.assertEqual(self.dai_loc.coord_confidence, "manual")
        self.assertTrue(AuditLog.objects.filter(action=AuditLog.Action.WARD_COORDS_CHANGED).exists())
        outside = dict(form, latitude="21.0285", longitude="105.8542")
        self.assertEqual(self.client.post(url, outside, SERVER_NAME="localhost").status_code, 200)  # form error
        self.dai_loc.refresh_from_db()
        self.assertEqual(self.dai_loc.latitude, Decimal("15.880000"))


class WeatherUpdateTests(WeatherTestCase):
    def test_store_splits_observed_and_forecast(self):
        self.load_fake()
        rows = WeatherReading.objects.filter(ward=self.dai_loc)
        self.assertEqual(rows.filter(kind="forecast").count(), 72)
        self.assertTrue(rows.filter(kind="observed", time=T).exists())
        self.assertFalse(WeatherReading.objects.filter(ward=self.hoang_sa).exists())

    # c.
    @mock.patch("weather.services.time.sleep")
    def test_network_error_keeps_old_data_and_logs(self, _sleep):
        self.load_fake()
        before = list(WeatherReading.objects.order_by("id").values_list("id", "precipitation", "updated_at"))
        with mock.patch.object(services, "http_get_json",
                               side_effect=urllib.error.URLError("network down")):
            run = Run(UpdateRun.Kind.LIVE)
            step_weather(run)
        self.assertEqual(run.failures, 1)
        rec = UpdateRun.objects.get(step=UpdateRun.Step.WEATHER)
        self.assertFalse(rec.success)
        self.assertIn("network down", rec.error)
        self.assertEqual(list(WeatherReading.objects.order_by("id")
                              .values_list("id", "precipitation", "updated_at")), before)

    def test_missing_coordinates_are_skipped_and_recorded(self):
        wards = list(Ward.objects.filter(latitude__isnull=False).order_by("id"))
        with mock.patch.object(services, "http_get_json", return_value=fake_payload(wards)):
            run = Run(UpdateRun.Kind.LIVE)
            step_weather(run)
        rec = UpdateRun.objects.get(step=UpdateRun.Step.WEATHER)
        self.assertTrue(rec.success)
        self.assertEqual(rec.details["skipped_no_coordinates"], ["Đặc khu Hoàng Sa"])
        self.assertEqual(rec.details["wards"], 93)

    # e.
    def test_stale_after_two_hours(self):
        self.load_fake()
        self.assertFalse(services.ward_weather(self.dai_loc, now=T + timedelta(minutes=110))["stale"])
        self.assertTrue(services.ward_weather(self.dai_loc, now=T + timedelta(hours=2, minutes=5))["stale"])
        with mock.patch("django.utils.timezone.now", return_value=T + timedelta(hours=3)):
            body = self.client.get(f"/api/weather/wards/{self.dai_loc.pk}/").json()
            self.assertTrue(body["stale"])
            self.assertTrue(self.client.get("/api/weather/map/").json()["stale"])

    # f.
    def test_rain_24h_matches_hand_computation(self):
        self.load_fake()
        for ref in (T, T - timedelta(hours=5), T - timedelta(hours=11)):
            with self.subTest(ref=ref):
                expected = round(sum(rain_at(timezone.localtime(ref - timedelta(hours=i)))
                                     for i in range(24)), 1)
                got = services.ward_weather(self.dai_loc, now=ref + timedelta(minutes=10))
                self.assertEqual(got["rain_past_hours"], 24)
                self.assertEqual(got["rain_past_24h_mm"], expected)
        nxt = round(sum(rain_at(timezone.localtime(T + timedelta(hours=i))) for i in range(1, 25)), 1)
        now = services.ward_weather(self.dai_loc, now=T + timedelta(minutes=10))
        self.assertEqual(now["rain_next_24h_mm"], nxt)
        with mock.patch("django.utils.timezone.now", return_value=T + timedelta(minutes=10)):
            units = {u["id"]: u for u in self.client.get("/api/weather/map/?metric=next24h").json()["units"]}
        self.assertEqual(units[self.dai_loc.pk]["value_mm"], nxt)

    def test_heavy_rain_follows_config(self):
        self.load_fake()
        from core.models import SystemConfig
        SystemConfig.objects.filter(key="heavy_rain_threshold_mm").update(value=1)
        got = services.ward_weather(self.dai_loc, now=T + timedelta(minutes=10))
        self.assertTrue(got["heavy_rain_past"])
        self.assertEqual(got["heavy_rain_threshold_mm"], 1)

    # g.
    def test_map_api_with_missing_coordinates(self):
        self.load_fake()
        Ward.objects.filter(pk=self.dai_loc.pk).update(latitude=None, longitude=None)
        with mock.patch("django.utils.timezone.now", return_value=T + timedelta(minutes=10)):
            for metric in ("past24h", "next24h"):
                with self.subTest(metric=metric):
                    res = self.client.get(f"/api/weather/map/?metric={metric}")
                    self.assertEqual(res.status_code, 200)
                    body = res.json()
                    missing = {m["label"] for m in body["missing_coordinates"]}
                    self.assertEqual(missing, {"Xã Đại Lộc", "Đặc khu Hoàng Sa"})
                    self.assertEqual(len(body["units"]), 92)
            ward = self.client.get(f"/api/weather/wards/{self.hoang_sa.pk}/")
            self.assertEqual(ward.status_code, 200)
            self.assertFalse(ward.json()["available"])
        self.assertEqual(self.client.get("/api/weather/map/?metric=bad").status_code, 400)
        self.assertEqual(self.client.get("/api/weather/boundaries/").status_code, 200)
