"""Hourly update (update_forecasts) and historical replay (replay_forecasts).

Live run: PCTT portal -> data store -> DB; Open-Meteo rain -> DB; suspicious flags; du_bao()
on >= forecast_input_hours hours read from the DB; Forecast rows; automatic alerts.
Every step (and every reservoir inside a step) is recorded in UpdateRun; an error in one
reservoir never stops the others.
"""
import fcntl
import io
import traceback
import uuid
from contextlib import contextmanager, redirect_stdout
from datetime import timedelta

import pandas as pd
from django.utils import timezone

from alerts import services as alert_services
from alerts.models import Alert, AlertState
from core.services import get_config

from . import rain
from .forecasting import (hourly_frame, input_frame, modules, overall_level, run_du_bao,
                          save_forecast, to_aware, to_naive_local)
from .models import Forecast, OperationRecord, Rainfall, Reservoir, UpdateRun
from .services import (apply_suspicious, compute_suspicious, latest_rain_time,
                       sync_operation_records, upsert_rain)


class Run:
    def __init__(self, kind=UpdateRun.Kind.LIVE, out=None):
        self.id = uuid.uuid4()
        self.kind = kind
        self.out = out or (lambda msg: None)
        self.failures = 0

    @contextmanager
    def step(self, step, reservoir=None):
        rec = UpdateRun.objects.create(run_id=self.id, kind=self.kind, step=step,
                                       reservoir=reservoir, started_at=timezone.now())
        label = f"{UpdateRun.Step(step).label}" + (f" – {reservoir.name}" if reservoir else "")
        try:
            yield rec.details
            rec.success = True
            self.out(f"  ✓ {label}{_summary(rec.details)}")
        except Exception as e:
            rec.success = False
            rec.error = f"{type(e).__name__}: {e}"
            rec.details["traceback"] = traceback.format_exc()[-4000:]
            self.failures += 1
            self.out(f"  ✗ {label}: {rec.error}")
        finally:
            rec.finished_at = timezone.now()
            rec.save()


def _summary(details):
    shown = {k: v for k, v in details.items() if k in ("note", "rows", "hours", "level", "levels", "outcome")}
    return f" ({', '.join(f'{k}: {v}' for k, v in shown.items())})" if shown else ""


# ---------------------------------------------------------------- steps
def step_reservoir_data(run, force=False):
    """Call cap_nhat_du_lieu_ho.cap_nhat() (at most once per pctt_min_interval_minutes),
    then copy the new hours of the store into the DB."""
    with run.step(UpdateRun.Step.RESERVOIR_DATA) as d:
        min_gap = timedelta(minutes=get_config("pctt_min_interval_minutes"))
        last = (UpdateRun.objects.filter(step=UpdateRun.Step.RESERVOIR_DATA, kind=UpdateRun.Kind.LIVE,
                                         details__called_portal=True)
                .exclude(run_id=run.id).order_by("-started_at").first())
        if not force and last and timezone.now() - last.started_at < min_gap:
            d["note"] = (f"bỏ qua: đã gọi cổng PCTT lúc {timezone.localtime(last.started_at):%H:%M}, "
                         f"tối đa 1 lần mỗi {min_gap.seconds // 60} phút")
        else:
            m = modules()
            m.updater.KHO.mkdir(parents=True, exist_ok=True)
            d["called_portal"] = True
            printed = io.StringIO()
            with open(m.updater.F_KHOA, "w") as lock:
                try:
                    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError as e:
                    raise RuntimeError("một lần cập nhật kho khác đang chạy") from e
                try:
                    with redirect_stdout(printed):
                        result = m.updater.cap_nhat()
                except SystemExit as e:         # cap_nhat() exits when the store is missing
                    raise RuntimeError(str(e)) from e
                finally:
                    d["log"] = printed.getvalue()[-4000:]
            d["note"] = f"{result['so_gio_moi']} giờ mới, kho đến {result['moc_cuoi']:%d/%m/%Y %H:%M}"
            if result["gio_khac_nguon"]:
                d["note"] += f"; {result['gio_khac_nguon']} giờ nguồn đã sửa (kho giữ giá trị cũ)"
        # Always sync the tail of the store (also picks up a run of the standalone script).
        store = modules().xl.doc_kho_van_hanh(in_ra=lambda *a: None)
        latest = OperationRecord.objects.order_by("-time").values_list("time", flat=True).first()
        since = to_naive_local(latest) - timedelta(hours=24) if latest else None
        d["rows"] = sum(sync_operation_records(store, since=since).values())


def step_rain_archive(run, today=None):
    """Fill historical rain up to today - rain_archive_lag_days where it is missing."""
    today = today or timezone.localdate()
    end = today - timedelta(days=get_config("rain_archive_lag_days"))
    for res in Reservoir.objects.all():
        with run.step(UpdateRun.Step.RAIN_ARCHIVE, res) as d:
            last = latest_rain_time(res, Rainfall.Source.HISTORICAL)
            start = timezone.localtime(last).date() + timedelta(days=1) if last else end
            if start > end:
                d["note"] = f"đã đủ đến {end:%d/%m/%Y}"
                continue
            series, dropped, raw = rain.fetch(Rainfall.Source.HISTORICAL, res.model_key,
                                              start_date=start, end_date=end)
            d.update(rows=upsert_rain(res, series, Rainfall.Source.HISTORICAL), dropped=dropped,
                     raw=raw.name, period=f"{start} → {end}")


def step_rain_forecast(run, past_days=7):
    now = pd.Timestamp(to_naive_local(timezone.now())).floor("h")
    for res in Reservoir.objects.all():
        with run.step(UpdateRun.Step.RAIN_FORECAST, res) as d:
            series, dropped, raw = rain.fetch(Rainfall.Source.FORECAST, res.model_key,
                                              past_days=past_days)
            series = series[series.index <= now]          # never store future hours
            d.update(rows=upsert_rain(res, series, Rainfall.Source.FORECAST), dropped=dropped,
                     raw=raw.name)


def step_suspicious(run):
    with run.step(UpdateRun.Step.SUSPICIOUS_FLAGS) as d:
        log = []
        store = modules().xl.doc_kho_van_hanh(in_ra=lambda *a: None)
        flags, covered = compute_suspicious(store, log)
        d["rows"] = apply_suspicious(flags, covered)
        d["log"] = "\n".join(log)[-4000:]


def latest_data_hour():
    latest = OperationRecord.objects.order_by("-time").values_list("time", flat=True).first()
    return pd.Timestamp(to_naive_local(latest)) if latest else None


def forecast_one(reservoir, t, *, simulation, frame=None):
    """du_bao() at naive local hour t on the data the DB holds up to t. Returns (result, rows)."""
    n = get_config("forecast_input_hours")
    if frame is None:
        frame = input_frame(reservoir, t, n)
    result = run_du_bao(reservoir, frame)
    rows = save_forecast(reservoir, t, result, is_simulation=simulation)
    return result, rows


def step_forecast_and_alerts(run, t=None, force=False):
    t = t or latest_data_hour()
    if t is None:
        with run.step(UpdateRun.Step.FORECAST):
            raise RuntimeError("chưa có số liệu vận hành trong cơ sở dữ liệu (chạy load_history)")
    issued = to_aware(t)
    for res in Reservoir.objects.all():
        result = rows = None
        with run.step(UpdateRun.Step.FORECAST, res) as d:
            d["issued_at"] = f"{t:%Y-%m-%d %H:%M}"
            # Skip an hour already forecast, unless du_bao() lacked data then (late data).
            if not force and Forecast.objects.filter(reservoir=res, issued_at=issued,
                                                     is_simulation=False,
                                                     expected_level__isnull=False).exists():
                d["note"] = f"đã có dự báo lúc {t:%H:%M %d/%m}"
            else:
                result, rows = forecast_one(res, t, simulation=False)
                d["level"] = str(overall_level(result) or "không đủ dữ liệu")
                if result.get("can_xac_nhan"):
                    OperationRecord.objects.filter(reservoir=res, time=issued).update(suspicious=True)
        if rows:
            with run.step(UpdateRun.Step.ALERTS, res) as d:
                d["outcome"] = alert_services.evaluate(res, issued, result, rows,
                                                       simulation=False, send_email=True)


def run_live(out=None, force=False, skip_portal=False, skip_rain=False):
    run = Run(UpdateRun.Kind.LIVE, out)
    if not skip_portal:
        step_reservoir_data(run, force=force)
    if not skip_rain:
        step_rain_archive(run)
        step_rain_forecast(run)
    step_suspicious(run)
    step_forecast_and_alerts(run, force=force)
    return run


# ---------------------------------------------------------------- replay
def clear_simulated_alerts():
    """Simulated alerts belong to the last replay: start each replay from a clean state."""
    Alert.objects.filter(is_simulation=True).delete()
    AlertState.objects.filter(is_simulation=True).delete()


def run_replay(start, end, out=None, web_notifications=False):
    """Forecast every hour in [start, end] (naive local) as if it were live: at hour t only
    data up to t is given to du_bao(). Results are stored with is_simulation=True (live rows
    are never touched) and no email is ever sent."""
    run = Run(UpdateRun.Kind.REPLAY, out)
    n = get_config("forecast_input_hours")
    hours = pd.date_range(start, end, freq="h")
    clear_simulated_alerts()
    for res in Reservoir.objects.all():
        with run.step(UpdateRun.Step.FORECAST, res) as d:
            # Read the whole period once; each hour then sees exactly input_frame(res, t, n).
            full = hourly_frame(res, hours[0] - pd.Timedelta(hours=n - 1), hours[-1])
            levels = {}
            for t in hours:
                frame = full.loc[t - pd.Timedelta(hours=n - 1):t]
                result, rows = forecast_one(res, t, simulation=True, frame=frame)
                lv = str(overall_level(result) or "none")
                levels[lv] = levels.get(lv, 0) + 1
                alert_services.evaluate(res, to_aware(t), result, rows, simulation=True,
                                        send_email=False, notify_users=web_notifications)
            d.update(hours=len(hours), levels=levels, period=f"{start} → {end}")
    return run


def simulation_range():
    qs = Forecast.objects.filter(is_simulation=True)
    first = qs.order_by("issued_at").values_list("issued_at", flat=True).first()
    last = qs.order_by("-issued_at").values_list("issued_at", flat=True).first()
    return first, last
