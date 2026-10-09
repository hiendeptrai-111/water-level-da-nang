"""Fill the rainfall gap after the training data (which ends 31/12/2025).

Open-Meteo Historical API from --from to --to (default: the day after the last historical hour
of each reservoir, up to today - rain_archive_lag_days), then the Forecast API (past_days) for
the days after --to up to the current hour. Same configuration as the training data (see
reservoirs/rain.py). Each hour keeps its source (historical / forecast). Finally prints the
hours still missing.
"""
from datetime import date, timedelta

import pandas as pd
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count
from django.utils import timezone

from core.services import get_config
from reservoirs import rain
from reservoirs.forecasting import to_aware, to_naive_local
from reservoirs.models import Rainfall, Reservoir
from reservoirs.services import latest_rain_time, upsert_rain


def parse_date(text):
    try:
        return date.fromisoformat(text)
    except ValueError as e:
        raise CommandError(f"Ngày không hợp lệ: {text} (dạng YYYY-MM-DD)") from e


def missing_hours(reservoir, start, end):
    """Hours in [start, end] (naive local) with no Rainfall row, as a list of (from, to) gaps."""
    have = set(pd.DatetimeIndex([to_naive_local(t) for t in Rainfall.objects.filter(
        reservoir=reservoir, time__range=(to_aware(start), to_aware(end)))
        .values_list("time", flat=True)]))
    grid = pd.date_range(start, end, freq="h")
    miss = [t for t in grid if t not in have]
    gaps, run = [], []
    for t in miss:
        if run and t - run[-1] != pd.Timedelta(hours=1):
            gaps.append((run[0], run[-1]))
            run = []
        run.append(t)
    if run:
        gaps.append((run[0], run[-1]))
    return len(miss), gaps


class Command(BaseCommand):
    help = "Bù mưa sau dữ liệu huấn luyện: Open-Meteo Historical đến hôm nay − N ngày, Forecast cho phần sau"

    def add_arguments(self, parser):
        parser.add_argument("--from", dest="start", help="ngày đầu (YYYY-MM-DD)")
        parser.add_argument("--to", dest="end", help="ngày cuối của Historical API (YYYY-MM-DD)")
        parser.add_argument("--no-forecast", action="store_true",
                            help="không lấy Forecast API cho phần sau --to")

    def handle(self, *args, **opts):
        reservoirs = list(Reservoir.objects.all())
        if len(reservoirs) != 4:
            raise CommandError("Chưa nạp 4 hồ. Chạy trước: python manage.py load_reservoirs")
        today = timezone.localdate()
        end = parse_date(opts["end"]) if opts["end"] else \
            today - timedelta(days=get_config("rain_archive_lag_days"))
        now = pd.Timestamp(to_naive_local(timezone.now())).floor("h")
        report_from = None

        for res in reservoirs:
            if opts["start"]:
                start = parse_date(opts["start"])
            else:
                last = latest_rain_time(res, Rainfall.Source.HISTORICAL)
                start = timezone.localtime(last).date() + timedelta(days=1) if last else end
            report_from = min(report_from or start, start)
            if start <= end:
                series, dropped, raw = rain.fetch(Rainfall.Source.HISTORICAL, res.model_key,
                                                  start_date=start, end_date=end)
                n = upsert_rain(res, series, Rainfall.Source.HISTORICAL)
                self.stdout.write(f"{res.name}: Historical {start:%d/%m/%Y} → {end:%d/%m/%Y}: "
                                  f"{n:,} giờ ghi, {dropped} giờ thiếu điểm (bỏ) – {raw.name}")
            else:
                self.stdout.write(f"{res.name}: Historical đã có đến {end:%d/%m/%Y}")

            if not opts["no_forecast"]:
                past_days = min((today - end).days + 1, 92)
                series, dropped, raw = rain.fetch(Rainfall.Source.FORECAST, res.model_key,
                                                  past_days=past_days)
                series = series[(series.index > pd.Timestamp(end) + pd.Timedelta(hours=23))
                                & (series.index <= now)]
                n = upsert_rain(res, series, Rainfall.Source.FORECAST)
                self.stdout.write(f"{res.name}: Forecast (past_days={past_days}) sau "
                                  f"{end:%d/%m/%Y} → {now:%d/%m/%Y %H:%M}: {n:,} giờ ghi, "
                                  f"{dropped} giờ thiếu điểm (bỏ) – {raw.name}")

        start_ts = pd.Timestamp(report_from)
        self.stdout.write(f"\nGiờ còn thiếu mưa từ {start_ts:%d/%m/%Y %H:%M} đến {now:%d/%m/%Y %H:%M}:")
        for res in reservoirs:
            n, gaps = missing_hours(res, start_ts, now)
            by_source = dict(Rainfall.objects.filter(reservoir=res, time__gte=to_aware(start_ts))
                             .values_list("source").annotate(n=Count("id")).order_by())
            shown = "; ".join(f"{a:%d/%m %H:%M}→{b:%d/%m %H:%M}" for a, b in gaps[:5])
            self.stdout.write(f"  {res.name}: thiếu {n} giờ"
                              + (f" ({shown}{' …' if len(gaps) > 5 else ''})" if n else "")
                              + f"; đã có historical {by_source.get('historical', 0):,} giờ, "
                                f"forecast {by_source.get('forecast', 0):,} giờ")
