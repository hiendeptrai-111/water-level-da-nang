"""Catchment rainfall from Open-Meteo, configured exactly like the training data
(du_bao/models/toa_do_mua.json): hourly=precipitation, timezone=Asia/Bangkok (= UTC+7, local
time), no model parameter (Best Match), rain of a reservoir = arithmetic mean of its points.

Historical API (archive) for the past up to (today - rain_archive_lag_days); Forecast API with
past_days for the most recent days. Every raw response is saved in kho_du_lieu/mua_tai_them/.
"""
import json
import time
import urllib.parse
import urllib.request
from datetime import datetime

import pandas as pd
from django.conf import settings

from .models import Rainfall

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
TIMEZONE = "Asia/Bangkok"


class RainSourceError(RuntimeError):
    """Open-Meteo unreachable or answered something unexpected: nothing is written."""


def coordinates():
    data = json.loads((settings.FORECAST_DIR / "models" / "toa_do_mua.json")
                      .read_text(encoding="utf-8"))
    if data.get("mui_gio") != TIMEZONE:
        raise RainSourceError(f"toa_do_mua.json dùng múi giờ {data.get('mui_gio')}, mong đợi {TIMEZONE}")
    expected = data["so_diem_ky_vong"]
    points = {}
    for key, n in expected.items():
        if len(data[key]) != n:
            raise RainSourceError(f"{key}: có {len(data[key])} điểm, mong đợi {n}")
        points[key] = data[key]
    return points


def _get_json(url, params, attempts=3):
    full = f"{url}?{urllib.parse.urlencode(params)}"
    error = None
    for i in range(attempts):
        try:
            req = urllib.request.Request(full, headers={"User-Agent": settings.HTTP_USER_AGENT})
            with urllib.request.urlopen(req, timeout=60) as r:
                return full, json.loads(r.read().decode("utf-8"))
        except Exception as e:                  # network error or bad JSON: retry
            error = e
            time.sleep(3 * (i + 1))
    raise RainSourceError(f"Không tải được {full}: {type(error).__name__}: {error}")


def _save_raw(kind, model_key, url, payload):
    folder = settings.DATA_STORE_DIR / "mua_tai_them"
    folder.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    path = folder / f"{kind}_{model_key}_{stamp}.json"
    with open(path, "x", encoding="utf-8") as f:     # "x": never overwrite
        json.dump({"url": url, "lay_luc": stamp, "du_lieu": payload}, f, ensure_ascii=False)
    return path


def mean_of_points(model_key, payload, n_points):
    """Hourly mean of all points; an hour where any point is missing is dropped (counted)."""
    if isinstance(payload, dict):
        payload = [payload]
    if not isinstance(payload, list) or len(payload) != n_points:
        raise RainSourceError(f"{model_key}: Open-Meteo trả {len(payload) if isinstance(payload, list) else payload!r} "
                              f"điểm, mong đợi {n_points}")
    columns = {}
    times = None
    for i, point in enumerate(payload):
        if point.get("error"):
            raise RainSourceError(f"{model_key}: {point.get('reason')}")
        if point.get("timezone") != TIMEZONE or point["hourly_units"].get("precipitation") != "mm":
            raise RainSourceError(f"{model_key}: múi giờ/đơn vị khác mong đợi "
                                  f"({point.get('timezone')}, {point['hourly_units']})")
        t = pd.to_datetime(point["hourly"]["time"])
        if times is None:
            times = t
        elif not times.equals(t):
            raise RainSourceError(f"{model_key}: các điểm có mốc giờ khác nhau")
        columns[i] = pd.to_numeric(pd.Series(point["hourly"]["precipitation"], index=t),
                                   errors="coerce")
    df = pd.DataFrame(columns)
    complete = df.notna().all(axis=1)
    return df[complete].mean(axis=1), int((~complete).sum())


def fetch(kind, model_key, *, start_date=None, end_date=None, past_days=None):
    """kind 'historical' (archive, start/end dates) or 'forecast' (past_days).
    Returns (series of mm by naive local hour, hours dropped as incomplete, raw file)."""
    points = coordinates()[model_key]
    params = {"latitude": ",".join(str(p[0]) for p in points),
              "longitude": ",".join(str(p[1]) for p in points),
              "hourly": "precipitation", "timezone": TIMEZONE}
    if kind == Rainfall.Source.HISTORICAL:
        url = ARCHIVE_URL
        params.update(start_date=f"{start_date:%Y-%m-%d}", end_date=f"{end_date:%Y-%m-%d}")
    else:
        url = FORECAST_URL
        params.update(past_days=past_days, forecast_days=1)
    full, payload = _get_json(url, params)
    raw = _save_raw(kind, model_key, full, payload)
    series, dropped = mean_of_points(model_key, payload, len(points))
    return series, dropped, raw
