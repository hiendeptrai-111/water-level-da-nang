"""Bridge to the research modules in du_bao/ (xu_ly_du_lieu.py, du_bao.py,
cap_nhat_du_lieu_ho.py). Those files are never edited: this module only imports them and
points their data paths at settings.DATA_STORE_DIR (./kho_du_lieu/) instead of
du_bao/kho_du_lieu/. Every cleaning step (duplicate hours, spike filter, manual exclusions,
real-time spike filter) is done by calling their functions, never re-implemented here.
"""
import hashlib
import importlib
import json
import sys
import threading
from contextlib import contextmanager

import numpy as np
import pandas as pd
from django.conf import settings
from django.utils import timezone

from .models import AlertLevel, Forecast, OperationRecord, Rainfall

LOCAL_TZ = "Asia/Ho_Chi_Minh"   # du_bao/ works in naive local time (UTC+7)
# du_bao() level names -> AlertLevel. Only a renaming: the level itself is never recomputed.
LEVEL_FROM_MODEL = {"binh_thuong": AlertLevel.NORMAL, "theo_doi": AlertLevel.WATCH,
                    "canh_bao": AlertLevel.WARNING}
# OperationRecord field <- column suffix used by xu_ly_du_lieu (COT_HO / COT)
FIELD_FROM_COLUMN = {"mn": "water_level", "den": "inflow", "may": "turbine_flow",
                     "tran": "spillway_flow"}

_lock = threading.Lock()
_modules = None


class ForecastModules:
    def __init__(self, xl, db, cn):
        self.xl, self.du_bao_module, self.updater = xl, db, cn

    def du_bao(self, model_key, frame):
        return self.du_bao_module.du_bao(model_key, frame)


def modules():
    """Import du_bao/ once; point its data paths at settings.DATA_STORE_DIR (every call, so a
    test can use a temporary store with override_settings)."""
    global _modules
    with _lock:
        if _modules is None:
            folder = str(settings.FORECAST_DIR)
            if folder not in sys.path:
                # du_bao/du_bao.py has the same name as its folder: the folder itself must be
                # on sys.path (see du_bao/NGUON.md).
                sys.path.insert(0, folder)
            _modules = ForecastModules(importlib.import_module("xu_ly_du_lieu"),
                                       importlib.import_module("du_bao"),
                                       importlib.import_module("cap_nhat_du_lieu_ho"))
        xl, cn = _modules.xl, _modules.updater
        store = settings.DATA_STORE_DIR
        xl.GOC = store                                    # tim_file(): mua_data/ under the store
        xl.F_NGOAI_LE = store / "ngoai_le_thu_cong.csv"
        xl.F_KHO_VAN_HANH = store / "van_hanh" / "van_hanh.csv"
        xl.doc_kho_van_hanh.__defaults__ = (xl.F_KHO_VAN_HANH, print)
        cn.KHO = xl.F_KHO_VAN_HANH.parent
        cn.F_KHO = xl.F_KHO_VAN_HANH
        cn.THU_MUC_THO = cn.KHO / "tho"
        cn.F_KHOA = cn.KHO / ".dang_chay.lock"
        cn.UA = settings.HTTP_USER_AGENT
        return _modules


@contextmanager
def patched(obj, **attrs):
    """Temporarily replace attributes of a module (restored even on error)."""
    old = {k: getattr(obj, k) for k in attrs}
    for k, v in attrs.items():
        setattr(obj, k, v)
    try:
        yield
    finally:
        for k, v in old.items():
            setattr(obj, k, v)


# ---------------------------------------------------------------- model metadata
_info = None


def model_info():
    """Version, training date and data range of the deployed models (metadata.json)."""
    global _info
    if _info is None:
        path = settings.FORECAST_DIR / "models" / "metadata.json"
        raw = path.read_bytes()
        md = json.loads(raw)
        ranges = [(ho[f"{h}h"]["du_lieu_tu"], ho[f"{h}h"]["du_lieu_den"])
                  for ho in md["mo_hinh"].values() for h in md["tam_du_bao_gio"]]
        _info = {
            "version": hashlib.sha256(raw).hexdigest()[:8],
            "trained_at": md["ngay_huan_luyen"],
            "data_range": md["du_lieu_nguon"].get("khoang_du_lieu_sau_lam_sach"),
            "training_from": min(r[0] for r in ranges),
            "training_to": max(r[1] for r in ranges),
            "min_input_hours": md["so_gio_toi_thieu_dau_vao"],
            "horizons": md["tam_du_bao_gio"],
            "library_versions": md["phien_ban"],
            "rapid_rise_threshold_m": md["muc_tieu"]["nguong_dang_nhanh_m"],
            "suspicious_jump_m": md["lam_sach"]["gai_lech_m"],
        }
    return _info


# ---------------------------------------------------------------- time helpers
def to_naive_local(dt):
    """Aware datetime -> naive local time (the convention of du_bao/)."""
    return timezone.localtime(dt).replace(tzinfo=None)


def to_aware(ts):
    """Naive local time (pandas Timestamp or datetime) -> aware datetime."""
    return timezone.make_aware(pd.Timestamp(ts).to_pydatetime())


def _naive_index(values):
    return pd.DatetimeIndex(pd.to_datetime(list(values), utc=True)).tz_convert(LOCAL_TZ) \
        .tz_localize(None)


# ---------------------------------------------------------------- DB -> du_bao() input
def hourly_frame(reservoir, start, end):
    """Columns mn, den, may, tran, mua on a continuous hourly grid [start, end] (naive local),
    read from the database exactly as stored. Missing hours stay NaN: du_bao() decides."""
    grid = pd.date_range(start, end, freq="h", name="thoi_gian")
    frame = pd.DataFrame(index=grid, columns=["mn", "den", "may", "tran", "mua"], dtype=float)
    a, b = to_aware(start), to_aware(end)
    ops = list(OperationRecord.objects.filter(reservoir=reservoir, time__range=(a, b))
               .values_list("time", "water_level", "inflow", "turbine_flow", "spillway_flow"))
    if ops:
        df = pd.DataFrame([o[1:] for o in ops], index=_naive_index(o[0] for o in ops),
                          columns=["mn", "den", "may", "tran"], dtype=float)
        frame.loc[df.index, df.columns] = df.to_numpy()
    rain = list(Rainfall.objects.filter(reservoir=reservoir, time__range=(a, b))
                .values_list("time", "rain_mm"))
    if rain:
        s = pd.Series([r[1] for r in rain], index=_naive_index(r[0] for r in rain), dtype=float)
        frame.loc[s.index, "mua"] = s.to_numpy()
    return frame.astype(float)


def input_frame(reservoir, end, hours):
    """The `hours` hours ending at `end` (inclusive): the data du_bao() sees at time `end`."""
    end = pd.Timestamp(end)
    return hourly_frame(reservoir, end - pd.Timedelta(hours=hours - 1), end)


# ---------------------------------------------------------------- du_bao() -> DB
def _plain(value):
    """Make the du_bao() result JSON-serialisable (numpy scalars -> Python)."""
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, float) and np.isnan(value):
        return None
    return value


def run_du_bao(reservoir, frame):
    return _plain(modules().du_bao(reservoir.model_key, frame))


def overall_level(result):
    return LEVEL_FROM_MODEL.get(result.get("muc_canh_bao_chung"))


def save_forecast(reservoir, issued_at, result, *, is_simulation=False):
    """Store the three horizons of one du_bao() result (update if the same hour is rerun).
    Returns the Forecast rows ordered by horizon."""
    issued = to_aware(issued_at)
    version = model_info()["version"]
    rows = []
    for horizon in model_info()["horizons"]:
        r = result[f"{horizon}h"]
        row, _ = Forecast.objects.update_or_create(
            reservoir=reservoir, issued_at=issued, horizon=horizon, is_simulation=is_simulation,
            defaults={
                "expected_level": r["muc_nuoc_du_kien"],
                "alert_level": LEVEL_FROM_MODEL.get(r["muc_canh_bao"]),
                "baseline_alert": r["baseline_bao"],
                "a_alert": r["A_bao"],
                "b_alert": r["B_bao"],
                "needs_confirmation": bool(r["can_xac_nhan"]),
                "model_version": version,
                "details": result,
            })
        rows.append(row)
    return rows
