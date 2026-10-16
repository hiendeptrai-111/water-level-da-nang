"""Load data/ward_centroids.csv into Ward (latitude, longitude, source, confidence).
Safe to run again. A coordinate outside the Da Nang boundary is rejected (left empty).
Coordinates entered by an admin (confidence 'manual') are kept unless --overwrite-manual."""
import csv
import unicodedata
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from catalog import geo
from catalog.models import Ward

DEFAULT_FILE = Path(settings.BASE_DIR) / "data" / "ward_centroids.csv"


class Command(BaseCommand):
    help = "Nạp tọa độ trung tâm phường/xã từ data/ward_centroids.csv (chạy lại không bị trùng)"

    def add_arguments(self, parser):
        parser.add_argument("--file", default=str(DEFAULT_FILE))
        parser.add_argument("--overwrite-manual", action="store_true",
                            help="ghi đè cả tọa độ admin đã nhập tay")

    @transaction.atomic
    def handle(self, *args, **opts):
        path = Path(opts["file"])
        if not path.exists():
            raise CommandError(f"Không thấy {path}. Chạy: python manage.py fetch_ward_centroids")
        with path.open(encoding="utf-8") as f:
            rows = list(csv.DictReader(unicodedata.normalize("NFC", line) for line in f
                                       if not line.startswith("#")))
        wards = {(w.kind, w.name): w for w in Ward.objects.all()}
        counts = {"boundary": 0, "needs_check": 0, "missing": 0, "rejected": 0, "kept_manual": 0}
        unknown = []
        for r in rows:
            w = wards.get((r["kind"], r["name"].strip()))
            if w is None:
                unknown.append(f"{r['kind']} {r['name']}")
                continue
            if w.coord_confidence == Ward.Confidence.MANUAL and not opts["overwrite_manual"]:
                counts["kept_manual"] += 1
                continue
            lat = Decimal(r["latitude"]) if r["latitude"] else None
            lon = Decimal(r["longitude"]) if r["longitude"] else None
            confidence, note = r["confidence"], r.get("note", "")
            if lat is not None and not geo.in_da_nang(lat, lon):
                lat = lon = None
                confidence, note = Ward.Confidence.MISSING, f"tọa độ {r['latitude']}, {r['longitude']} nằm ngoài TP Đà Nẵng: bỏ"
                counts["rejected"] += 1
            else:
                counts[confidence] += 1
            w.latitude, w.longitude = lat, lon
            w.coord_confidence = confidence
            w.coord_source = r.get("source", "") if lat is not None else ""
            w.coord_note = note[:255]
            w.osm_id = r.get("osm_id", "") if lat is not None else ""
            w.save(update_fields=["latitude", "longitude", "coord_confidence", "coord_source",
                                  "coord_note", "osm_id"])
        if opts["verbosity"] == 0:
            return
        self.stdout.write(self.style.SUCCESS(f"Đã nạp tọa độ: {counts}"))
        if unknown:
            self.stdout.write(self.style.WARNING("Dòng không khớp phường/xã nào (bỏ qua): " + ", ".join(unknown)))
        for w in Ward.objects.exclude(coord_confidence__in=[Ward.Confidence.BOUNDARY, Ward.Confidence.MANUAL]):
            self.stdout.write(f"  {w.get_coord_confidence_display()}: {w} – {w.coord_note}")
