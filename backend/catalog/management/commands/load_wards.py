import csv
import unicodedata
from collections import Counter
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from catalog.models import Ward

DEFAULT_FILE = Path(settings.BASE_DIR) / "data" / "wards.csv"
EXPECTED = {"ward": 23, "commune": 70, "special_zone": 1}


class Command(BaseCommand):
    help = "Nạp 94 phường/xã/đặc khu của Đà Nẵng (Nghị quyết 1659/NQ-UBTVQH15) từ data/wards.csv"

    def add_arguments(self, parser):
        parser.add_argument("--file", default=str(DEFAULT_FILE))

    def handle(self, *args, **opts):
        path = Path(opts["file"])
        if not path.exists():
            raise CommandError(f"Không thấy {path}")
        with path.open(encoding="utf-8") as f:
            lines = [unicodedata.normalize("NFC", line) for line in f if not line.startswith("#")]
        rows = list(csv.DictReader(lines))

        counts = Counter(r["kind"] for r in rows)
        if len(rows) != 94 or dict(counts) != EXPECTED:
            raise CommandError(f"File phải có đúng 94 đơn vị {EXPECTED}, đang có {len(rows)} "
                               f"{dict(counts)}. Không nạp gì.")
        if len({(r["kind"], r["name"].strip()) for r in rows}) != 94:
            raise CommandError("Có tên trùng trong file. Không nạp gì.")

        created = updated = 0
        with transaction.atomic():
            for r in rows:
                _, is_new = Ward.objects.update_or_create(
                    kind=r["kind"], name=r["name"].strip(),
                    defaults={
                        "priority": int(r["priority"] or 100),
                        "latitude": Decimal(r["latitude"]) if r.get("latitude") else None,
                        "longitude": Decimal(r["longitude"]) if r.get("longitude") else None,
                    })
                created += is_new
                updated += not is_new
        in_file = {(r["kind"], r["name"].strip()) for r in rows}
        extra = [w for w in Ward.objects.all() if (w.kind, w.name) not in in_file]
        if opts["verbosity"] == 0:
            return
        self.stdout.write(self.style.SUCCESS(
            f"Đã nạp {len(rows)} đơn vị: {created} mới, {updated} cập nhật."))
        if extra:
            self.stdout.write(self.style.WARNING(
                f"Trong cơ sở dữ liệu còn {len(extra)} đơn vị không có trong file (không xoá): "
                + ", ".join(str(w) for w in extra)))
