"""Load the data store into the database (spec step "nap_lich_su"). Safe to run again.

- kho_du_lieu/van_hanh/van_hanh.csv -> OperationRecord (read with xl.doc_kho_van_hanh).
- kho_du_lieu/mua_data/mua_*.csv (training rain, read with xl.doc_mua) -> Rainfall historical.
- Open-Meteo responses saved in kho_du_lieu/mua_tai_them/ (earlier downloads) -> Rainfall,
  so a rebuilt database never needs to download them again.
- Suspicious flags from the training cleaning pipeline (xl.nap_du_lieu_sach).
"""
import json
import time

import pandas as pd
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from reservoirs import rain
from reservoirs.forecasting import modules
from reservoirs.models import OperationRecord, Rainfall, Reservoir
from reservoirs.services import (apply_suspicious, compute_suspicious, sync_operation_records,
                                 upsert_rain)


class Command(BaseCommand):
    help = "Nạp kho dữ liệu (vận hành + mưa) vào cơ sở dữ liệu; chạy lại không bị nhân đôi"

    def handle(self, *args, **opts):
        if Reservoir.objects.count() != 4:
            raise CommandError("Chưa nạp 4 hồ. Chạy trước: python manage.py load_reservoirs")
        xl = modules().xl
        started = time.monotonic()

        store = xl.doc_kho_van_hanh(in_ra=self.stdout.write)
        written = sync_operation_records(store)
        self.stdout.write(f"Số liệu vận hành: {written} dòng ghi; trong DB "
                          f"{OperationRecord.objects.count():,} dòng")

        by_key = {r.model_key: r for r in Reservoir.objects.all()}
        for key, (name, _p, rain_file, _lim) in xl.HO.items():
            series = xl.doc_mua(rain_file)
            n = upsert_rain(by_key[key], series, Rainfall.Source.HISTORICAL)
            self.stdout.write(f"Mưa {name} ({rain_file}): {n:,} giờ "
                              f"({series.index.min():%d/%m/%Y} → {series.index.max():%d/%m/%Y})")

        saved = sorted((settings.DATA_STORE_DIR / "mua_tai_them").glob("*.json"))
        n_points = {k: len(v) for k, v in rain.coordinates().items()}
        for path in saved:
            kind = path.name.split("_", 1)[0]
            key = next(k for k in by_key if path.name.startswith(f"{kind}_{k}_"))
            payload = json.loads(path.read_text(encoding="utf-8"))["du_lieu"]
            series, _dropped = rain.mean_of_points(key, payload, n_points[key])
            if kind == Rainfall.Source.FORECAST:
                series = series[series.index <= path_time(path)]
            upsert_rain(by_key[key], series, kind)
        if saved:
            self.stdout.write(f"Mưa Open-Meteo đã tải trước đó (mua_tai_them/): {len(saved)} file")

        log = []
        flags, covered = compute_suspicious(store, log)
        counts = apply_suspicious(flags, covered)
        self.stdout.write(f"Số liệu nghi ngờ (quy trình làm sạch lúc huấn luyện, "
                          f"{covered[0]:%d/%m/%Y} → {covered[1]:%d/%m/%Y}): {counts}")
        in_exclusions = False
        for line in log:
            in_exclusions = ("Loại trừ thủ công" in line) or (in_exclusions and "Lọc gai" not in line)
            if in_exclusions or "đoạn gai" in line:
                self.stdout.write(f"  {line.strip()}")
        self.stdout.write(self.style.SUCCESS(f"Xong sau {time.monotonic() - started:.0f} giây."))


def path_time(path):
    """Download time encoded in a saved file name: <kind>_<key>_YYYYmmdd_HHMMSS_ffffff.json.
    A forecast response is only trusted up to the hour it was downloaded."""
    stamp = "_".join(path.stem.split("_")[-3:-1])
    return pd.to_datetime(stamp, format="%Y%m%d_%H%M%S").floor("h")
