"""Reservoir data: loading into the database, suspicious flags, regulatory thresholds,
directives and the status shown to users (CN06, CN07, CN24)."""
from datetime import timedelta

import numpy as np
import pandas as pd
from django.utils import timezone

from core.services import get_config

from .forecasting import (FIELD_FROM_COLUMN, LEVEL_FROM_MODEL, LOCAL_TZ, model_info, modules,
                          patched)
from .models import (AlertLevel, Forecast, OperatingDirective, OperationRecord, Rainfall,
                     RegulatoryThreshold, Reservoir)

BATCH = 5000


def _aware_index(index):
    return pd.DatetimeIndex(index).tz_localize(LOCAL_TZ).to_pydatetime()


def _num(v):
    return None if pd.isna(v) else float(v)


# ---------------------------------------------------------------- operating data
def sync_operation_records(store, since=None):
    """Copy the data store (xl.doc_kho_van_hanh(): naive local hourly index, columns
    av_mn, av_den, ...) into OperationRecord. Existing hours are updated, so running it twice
    never duplicates anything. Returns {code: rows written}."""
    written = {}
    if since is not None:
        store = store[store.index >= pd.Timestamp(since)]
    for res in Reservoir.objects.all():
        cols = [f"{res.code}_{c}" for c in FIELD_FROM_COLUMN]
        sub = store[cols].dropna(how="all")
        objs = [OperationRecord(reservoir=res, time=t,
                                **{FIELD_FROM_COLUMN[c.split("_")[1]]: _num(v)
                                   for c, v in zip(cols, row)})
                for t, row in zip(_aware_index(sub.index), sub.itertuples(index=False))]
        OperationRecord.objects.bulk_create(
            objs, batch_size=BATCH, update_conflicts=True, unique_fields=["reservoir", "time"],
            update_fields=list(FIELD_FROM_COLUMN.values()))
        written[res.code] = len(objs)
    return written


def compute_suspicious(store, log=None):
    """Run the training cleaning pipeline (xl.nap_du_lieu_sach: range check, manual exclusions,
    spike filter, interpolation) on the data store instead of the .xls export, and return
    {code: sorted naive times whose published value the pipeline rejected}, plus the range
    the pipeline covers. Nothing is re-implemented: doc_du_lieu_tho is only swapped for a
    reader of the (already de-duplicated) store."""
    xl = modules().xl
    lines = log if log is not None else []

    def read_store(in_ra=print, tra_nhat_ky=False):
        df = store.copy()
        return (df, pd.DataFrame()) if tra_nhat_ky else df

    with patched(xl, doc_du_lieu_tho=read_store):
        clean = xl.nap_du_lieu_sach(in_ra=lambda *a: lines.append(" ".join(map(str, a))))
    raw = store.reindex(clean.index)
    flags = {}
    for code in ("av", "dm", "sb", "st"):
        cols = [f"{code}_{c}" for c in FIELD_FROM_COLUMN]
        r, c = raw[cols].to_numpy(dtype=float), clean[cols].to_numpy(dtype=float)
        rejected = ~np.isnan(r) & (np.isnan(c) | ~np.isclose(r, c, equal_nan=True))
        flags[code] = list(clean.index[rejected.any(axis=1)])
    return flags, (clean.index.min(), clean.index.max())


def apply_suspicious(flags, covered):
    """Write flags for the range the cleaning pipeline covered (outside it: untouched)."""
    start, end = (timezone.make_aware(t.to_pydatetime()) for t in covered)
    counts = {}
    for res in Reservoir.objects.all():
        times = [timezone.make_aware(t.to_pydatetime()) for t in flags.get(res.code, [])]
        in_range = OperationRecord.objects.filter(reservoir=res, time__range=(start, end))
        in_range.exclude(time__in=times).filter(suspicious=True).update(suspicious=False)
        counts[res.code] = in_range.filter(time__in=times).update(suspicious=True)
    return counts


# ---------------------------------------------------------------- rainfall
def upsert_rain(reservoir, series, source):
    """Historical (archive) values win over forecast values: a forecast value never
    replaces a historical one, a historical value replaces a forecast one."""
    series = series.dropna()
    if series.empty:
        return 0
    times = list(_aware_index(series.index))
    values = series.to_numpy(dtype=float)
    if source == Rainfall.Source.FORECAST:
        historical = set(Rainfall.objects.filter(
            reservoir=reservoir, source=Rainfall.Source.HISTORICAL,
            time__range=(times[0], times[-1])).values_list("time", flat=True))
        keep = [i for i, t in enumerate(times) if t not in historical]
        times, values = [times[i] for i in keep], values[keep]
    objs = [Rainfall(reservoir=reservoir, time=t, rain_mm=float(v), source=source)
            for t, v in zip(times, values)]
    Rainfall.objects.bulk_create(objs, batch_size=BATCH, update_conflicts=True,
                                 unique_fields=["reservoir", "time"],
                                 update_fields=["rain_mm", "source"])
    return len(objs)


def latest_rain_time(reservoir, source=None):
    qs = Rainfall.objects.filter(reservoir=reservoir)
    if source:
        qs = qs.filter(source=source)
    return qs.order_by("-time").values_list("time", flat=True).first()


# ---------------------------------------------------------------- thresholds and directives
def thresholds_for(reservoir, day):
    """Regulatory thresholds in force on `day` (date). Empty list = outside the flood season."""
    return [t for t in reservoir.thresholds.all() if t.covers(day)]


def period_label(start_day, end_day):
    def fmt(md):
        m, d = md.split("-")
        return f"{int(d):02d}/{int(m)}"
    return f"{fmt(start_day)} – {fmt(end_day)}"


def threshold_block(reservoir, day):
    items = thresholds_for(reservoir, day)
    if not items:
        return {"in_season": False, "period": None, "label": "Ngoài mùa lũ", "items": []}
    first = items[0]
    return {
        "in_season": True,
        "period": period_label(first.start_day, first.end_day),
        "label": f"Thời kỳ {period_label(first.start_day, first.end_day)}",
        "items": [{"id": t.id, "kind": t.kind, "kind_label": t.get_kind_display(),
                   "value_low": t.value_low, "value_high": t.value_high,
                   "document": t.document} for t in items],
    }


def active_directives(reservoir):
    return [d for d in reservoir.directives.all() if d.is_active]


def directive_dict(d):
    """Public view of a directive (no personal data)."""
    return {"id": d.id, "requirement": d.requirement,
            "requirement_label": d.get_requirement_display() or "Mực nước mục tiêu",
            "target_level": d.target_level, "starts_at": d.starts_at, "deadline": d.deadline,
            "document": d.document}


def compare(level, low, high):
    """Neutral comparison of a water level with a value or a range (no colour judgement)."""
    if level is None:
        return None
    if level > high:
        return {"position": "above", "diff_m": round(level - high, 2)}
    if level < low:
        return {"position": "below", "diff_m": round(level - low, 2)}
    return {"position": "within" if low != high else "equal", "diff_m": 0.0}


# ---------------------------------------------------------------- status (CN06, CN07)
def reservoir_queryset():
    return Reservoir.objects.prefetch_related("thresholds", "directives")


def latest_forecast_rows(reservoir, *, at, simulation):
    issued = (Forecast.objects.filter(reservoir=reservoir, is_simulation=simulation,
                                      issued_at__lte=at)
              .order_by("-issued_at").values_list("issued_at", flat=True).first())
    if issued is None:
        return None, []
    return issued, list(Forecast.objects.filter(reservoir=reservoir, is_simulation=simulation,
                                                issued_at=issued).order_by("horizon"))


def forecast_available(record, issued_at, rows, stale):
    """CN07 / 6.3: show a forecast only when it was made at the latest hour that has a water
    level, that hour is recent, and du_bao() could compute it."""
    return bool(record and rows and not stale and issued_at == record.time
                and rows[0].expected_level is not None)


def reservoir_status(reservoir, *, at=None, simulation=False, with_forecast=False):
    now = at or timezone.now()
    record = (OperationRecord.objects.filter(reservoir=reservoir, time__lte=now,
                                             water_level__isnull=False)
              .order_by("-time").first())
    stale_after = timedelta(hours=get_config("stale_data_hours"))
    stale = record is None or now - record.time > stale_after
    issued_at, rows = latest_forecast_rows(reservoir, at=now, simulation=simulation)
    available = forecast_available(record, issued_at, rows, stale)
    details = rows[0].details if available else {}
    level = LEVEL_FROM_MODEL.get(details.get("muc_canh_bao_chung")) if available else None
    needs_confirmation = (bool(details.get("can_xac_nhan")) if available
                          else bool(record and record.suspicious))
    local_now = timezone.localtime(now)
    wl = record.water_level if record else None
    data = {
        "code": reservoir.code,
        "name": reservoir.name,
        "normal_water_level": reservoir.normal_water_level,
        "latitude": reservoir.latitude,
        "longitude": reservoir.longitude,
        "data_time": record.time if record else None,
        "stale": stale,
        "water_level": wl,
        "distance_to_normal_m": round(wl - reservoir.normal_water_level, 2) if wl is not None else None,
        "inflow": record.inflow if record else None,
        "turbine_flow": record.turbine_flow if record else None,
        "spillway_flow": record.spillway_flow if record else None,
        "suspicious": bool(record and record.suspicious),
        "needs_confirmation": needs_confirmation,
        "confirmation_reason": details.get("ly_do_can_xac_nhan") if available else None,
        "forecast_available": available,
        "forecast_issued_at": issued_at if available else None,
        "alert_level": level,
        "alert_level_label": AlertLevel(level).label if level else None,
        "trend": _trend(rows) if available else None,
        "thresholds": threshold_block(reservoir, local_now.date()),
        "directives": [directive_dict(d) for d in active_directives(reservoir)],
        "simulation": simulation,
    }
    if with_forecast:
        data["forecast"] = forecast_table(reservoir, rows, issued_at) if available else []
        data["forecast_message"] = None if available else "Chưa đủ dữ liệu để dự báo"
        data["model"] = model_info()
    return data


def _trend(rows):
    """Expected change over the next hours, for the plain-language sentence on the card."""
    by_h = {r.horizon: r for r in rows}
    r3 = by_h.get(3) or by_h.get(1)
    if r3 is None or r3.expected_level is None:
        return None
    change = r3.details[f"{r3.horizon}h"].get("thay_doi_du_kien_m")
    return {"horizon": r3.horizon, "change_m": change}


def forecast_table(reservoir, rows, issued_at):
    directives = active_directives(reservoir)
    table = []
    for r in rows:
        when = timezone.localtime(issued_at) + timedelta(hours=r.horizon)
        detail = r.details.get(f"{r.horizon}h", {})
        table.append({
            "horizon": r.horizon,
            "time": when,
            "expected_level": r.expected_level,
            "expected_change_m": detail.get("thay_doi_du_kien_m"),
            "alert_level": r.alert_level,
            "alert_level_label": AlertLevel(r.alert_level).label if r.alert_level else None,
            "baseline_alert": r.baseline_alert,
            "a_alert": r.a_alert,
            "b_alert": r.b_alert,
            "xgb_probability": detail.get("xac_suat_xgb"),
            "needs_confirmation": r.needs_confirmation,
            "data_warnings": detail.get("canh_bao_du_lieu", []),
            "thresholds": [
                {"kind": t.kind, "kind_label": t.get_kind_display(), "value_low": t.value_low,
                 "value_high": t.value_high,
                 "comparison": compare(r.expected_level, t.value_low, t.value_high)}
                for t in thresholds_for(reservoir, when.date())],
            "directives": [
                {**directive_dict(d),
                 "comparison": compare(r.expected_level, d.target_level, d.target_level)}
                for d in directives],
        })
    return table
