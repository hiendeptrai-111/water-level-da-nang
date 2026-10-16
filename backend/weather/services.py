"""Weather per commune (CN13, CN14) from the Open-Meteo Forecast API.

One request for every commune with coordinates: Open-Meteo accepts comma-separated
coordinates and then answers a list ("Multiple coordinates can be comma separated ... the
JSON output changes to a list of structures", https://open-meteo.com/en/docs).
hourly = temperature_2m, precipitation, wind_speed_10m; past_days=1 (the last 24 hours) and
forecast_days=4 (covers the next 72 hours); timezone Asia/Bangkok (= Vietnam time).
Everything is downloaded and checked before anything is written, in one transaction: a
failed run leaves the stored data untouched.
"""
import json
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from catalog.models import Ward
from core.services import get_config

from .models import WeatherReading

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
TIMEZONE = "Asia/Bangkok"
HOURLY = ["temperature_2m", "precipitation", "wind_speed_10m"]
UNITS = {"temperature_2m": "°C", "precipitation": "mm", "wind_speed_10m": "km/h"}
PAST_HOURS, NEXT_HOURS, KEEP_DAYS = 24, 72, 7


class WeatherSourceError(RuntimeError):
    """Open-Meteo unreachable or unexpected answer: nothing is written."""


def current_hour(now=None):
    return timezone.localtime(now or timezone.now()).replace(minute=0, second=0, microsecond=0)


def http_get_json(url):
    """Separate function so tests can simulate a network failure."""
    req = urllib.request.Request(url, headers={"User-Agent": settings.HTTP_USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def fetch(wards, attempts=3):
    """[(ward, [(aware time, temperature, precipitation, wind), ...]), ...] for `wards`."""
    params = {"latitude": ",".join(str(w.latitude) for w in wards),
              "longitude": ",".join(str(w.longitude) for w in wards),
              "hourly": ",".join(HOURLY), "timezone": TIMEZONE,
              "past_days": 1, "forecast_days": 4}
    url = f"{FORECAST_URL}?{urllib.parse.urlencode(params)}"
    error = None
    for i in range(attempts):
        try:
            payload = http_get_json(url)
            break
        except Exception as e:                 # network error / bad JSON: retry, then give up
            error = e
            if i < attempts - 1:
                time.sleep(2 * (i + 1))
    else:
        raise WeatherSourceError(f"Không tải được Open-Meteo: {type(error).__name__}: {error}")
    if isinstance(payload, dict):
        if payload.get("error"):
            raise WeatherSourceError(f"Open-Meteo báo lỗi: {payload.get('reason')}")
        payload = [payload]
    if len(payload) != len(wards):
        raise WeatherSourceError(f"Open-Meteo trả {len(payload)} vị trí, mong đợi {len(wards)}")
    out = []
    for ward, point in zip(wards, payload):
        if point.get("timezone") != TIMEZONE:
            raise WeatherSourceError(f"{ward}: múi giờ {point.get('timezone')}, mong đợi {TIMEZONE}")
        units = point.get("hourly_units", {})
        if any(units.get(k) != u for k, u in UNITS.items()):
            raise WeatherSourceError(f"{ward}: đơn vị khác mong đợi ({units})")
        h = point["hourly"]
        times = [timezone.make_aware(datetime.fromisoformat(t)) for t in h["time"]]
        out.append((ward, list(zip(times, h["temperature_2m"], h["precipitation"], h["wind_speed_10m"]))))
    return out


@transaction.atomic
def store(results, now=None):
    """Hours up to the current hour -> observed, later hours (<= +72 h) -> forecast."""
    now = now or timezone.now()
    hour = current_hour(now)
    objs = []
    for ward, rows in results:
        for t, temp, rain, wind in rows:
            if t <= hour:
                kind = WeatherReading.Kind.OBSERVED
            elif t <= hour + timedelta(hours=NEXT_HOURS):
                kind = WeatherReading.Kind.FORECAST
            else:
                continue
            objs.append(WeatherReading(ward=ward, time=t, kind=kind, temperature=temp,
                                       precipitation=rain, wind_speed=wind, updated_at=now))
    WeatherReading.objects.bulk_create(
        objs, batch_size=5000, update_conflicts=True, unique_fields=["ward", "time", "kind"],
        update_fields=["temperature", "precipitation", "wind_speed", "updated_at"])
    # forecasts for hours now passed are superseded; keep a week of past hours
    WeatherReading.objects.filter(kind=WeatherReading.Kind.FORECAST, time__lte=hour).delete()
    WeatherReading.objects.filter(time__lt=hour - timedelta(days=KEEP_DAYS)).delete()
    return len(objs)


def update(now=None):
    """Fetch and store. Returns details for UpdateRun (raises WeatherSourceError on failure)."""
    wards = list(Ward.objects.filter(latitude__isnull=False, longitude__isnull=False).order_by("id"))
    skipped = [str(w) for w in Ward.objects.filter(Q(latitude__isnull=True) | Q(longitude__isnull=True))]
    details = {"wards": len(wards), "skipped_no_coordinates": skipped}
    if not wards:
        details["note"] = "không có phường/xã nào có tọa độ"
        return details
    details["rows"] = store(fetch(wards), now)
    details["note"] = f"{len(wards)} phường/xã" + (f", bỏ qua {len(skipped)} thiếu tọa độ: "
                                                    + ", ".join(skipped) if skipped else "")
    return details


# ---------------------------------------------------------------- reading (API)
def _stale(updated_at, now):
    return updated_at is None or now - updated_at > timedelta(hours=get_config("stale_data_hours"))


def ward_weather(ward, now=None):
    """CN13: current conditions, rain over the past 24 h, hourly rain for the next 72 h."""
    now = now or timezone.now()
    threshold = get_config("heavy_rain_threshold_mm")
    base = {"ward": {"id": ward.id, "label": str(ward)},
            "has_coordinates": ward.latitude is not None,
            "latitude": ward.latitude, "longitude": ward.longitude,
            "coord_confidence": ward.coord_confidence,
            "heavy_rain_threshold_mm": threshold}
    observed = list(ward.weather.filter(kind=WeatherReading.Kind.OBSERVED, time__lte=now)
                    .order_by("-time")[:PAST_HOURS])
    if not observed:
        return {**base, "available": False, "updated_at": None, "stale": True, "current": None,
                "rain_past_24h_mm": None, "rain_next_24h_mm": None, "forecast": []}
    ref = observed[0].time
    window = [r for r in observed if r.time > ref - timedelta(hours=PAST_HOURS)]
    forecast = list(ward.weather.filter(kind=WeatherReading.Kind.FORECAST, time__gt=ref,
                                        time__lte=ref + timedelta(hours=NEXT_HOURS)).order_by("time"))
    updated = max([r.updated_at for r in observed[:1] + forecast[:1]])
    past = rain_sum(window)
    nxt = rain_sum([r for r in forecast if r.time <= ref + timedelta(hours=24)])
    return {**base, "available": True, "updated_at": updated, "stale": _stale(updated, now),
            "current": {"time": ref, "temperature": observed[0].temperature,
                        "rain_last_hour_mm": observed[0].precipitation,
                        "wind_speed_kmh": observed[0].wind_speed},
            "rain_past_24h_mm": past, "rain_past_hours": len(window),
            "heavy_rain_past": past is not None and past >= threshold,
            "rain_next_24h_mm": nxt,
            "heavy_rain_next": nxt is not None and nxt >= threshold,
            "forecast": [{"time": r.time, "precipitation": r.precipitation,
                          "temperature": r.temperature, "wind_speed_kmh": r.wind_speed}
                         for r in forecast]}


def rain_sum(rows):
    values = [r.precipitation for r in rows if r.precipitation is not None]
    return round(sum(values), 1) if values else None


def map_values(metric, now=None):
    """CN14: rain over the past or next 24 h for every commune (no coordinates -> listed apart)."""
    now = now or timezone.now()
    threshold = get_config("heavy_rain_threshold_mm")
    latest = (WeatherReading.objects.filter(kind=WeatherReading.Kind.OBSERVED, time__lte=now)
              .order_by("-time").values_list("time", flat=True).first())
    rows = {}
    if latest is not None:
        if metric == "past24h":
            qs = WeatherReading.objects.filter(kind=WeatherReading.Kind.OBSERVED,
                                               time__gt=latest - timedelta(hours=24), time__lte=latest)
        else:
            qs = WeatherReading.objects.filter(kind=WeatherReading.Kind.FORECAST, time__gt=latest,
                                               time__lte=latest + timedelta(hours=24))
        for ward_id, rain, updated in qs.values_list("ward_id", "precipitation", "updated_at"):
            entry = rows.setdefault(ward_id, {"sum": 0.0, "n": 0, "updated": updated})
            if rain is not None:
                entry["sum"] += rain
                entry["n"] += 1
            entry["updated"] = max(entry["updated"], updated)
    units, missing = [], []
    for w in Ward.objects.order_by("priority", "name"):
        if w.latitude is None or w.longitude is None:
            missing.append({"id": w.id, "label": str(w), "note": w.coord_note})
            continue
        r = rows.get(w.id)
        value = round(r["sum"], 1) if r and r["n"] else None
        units.append({"id": w.id, "label": str(w), "kind": w.kind, "latitude": w.latitude,
                      "longitude": w.longitude, "coord_confidence": w.coord_confidence,
                      "value_mm": value, "heavy_rain": value is not None and value >= threshold})
    updated = max((r["updated"] for r in rows.values()), default=None)
    return {"metric": metric, "reference_time": latest, "updated_at": updated,
            "stale": _stale(updated, now), "heavy_rain_threshold_mm": threshold,
            "units": units, "missing_coordinates": missing}
