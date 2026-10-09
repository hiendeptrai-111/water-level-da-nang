"""Base data of phase 2 (spec Appendix A and B). Safe to run again: nothing is duplicated.

- 4 reservoirs with MNDBT.
- Regulatory thresholds, Tables A.1 and A.2 (Decision 1865/QĐ-TTg, Article 6).
- The example directives of Table A.4, inactive.
- Reservoir – commune links of Table B.1/B.2. Names are matched exactly against the Ward
  table; a name that does not match is listed and skipped, never guessed.
"""
import unicodedata
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from catalog.models import Ward
from reservoirs.models import OperatingDirective, RegulatoryThreshold, Reservoir, ReservoirWard

# code, du_bao key, name, MNDBT (m), display order. Dam coordinates are not in the spec:
# left empty, to be entered by an admin (Django admin).
RESERVOIRS = [
    ("av", "a_vuong", "A Vương", 380.0, 1),
    ("dm", "dak_mi_4", "Đăk Mi 4", 258.0, 2),
    ("sb", "song_bung_4", "Sông Bung 4", 222.5, 3),
    ("st", "song_tranh_2", "Sông Tranh 2", 175.0, 4),
]

DOC_1865 = "Quyết định 1865/QĐ-TTg, Điều 6"
PERIODS = [("09-01", "11-15"), ("11-16", "12-15")]
# kind -> code -> [(low, high) for each period]   (Tables A.1, A.2)
THRESHOLDS = {
    RegulatoryThreshold.Kind.MAX_BEFORE_FLOOD: {
        "av": [(376, 376), (377, 380)],
        "dm": [(255, 255), (256, 258)],
        "sb": [(217.5, 217.5), (218.5, 222.5)],
        "st": [(172, 172), (173, 175)],
    },
    RegulatoryThreshold.Kind.MIN_FLOOD_RECEPTION: {
        "av": [(370, 370), (377, 377)],
        "dm": [(251.5, 251.5), (256, 256)],
        "sb": [(216, 216), (218.5, 218.5)],
        "st": [(165, 165), (173, 173)],
    },
}

NOT_EXCEED = OperatingDirective.Requirement.NOT_EXCEED
LOWER_TO = OperatingDirective.Requirement.LOWER_TO
# Table A.4 (examples, 2025). (document, requirement, {code: level}, starts_at, deadline)
# The third document does not say "không vượt" or "hạ về": requirement left empty.
DIRECTIVES = [
    ("131/PTDS, 26/10/2025", NOT_EXCEED, {"dm": 253.5, "av": 372, "st": 168},
     "2025-10-26 12:30", None),
    ("3542/UBND-PTDS, 05/11/2025", LOWER_TO, {"dm": 251.5, "av": 373, "st": 169},
     None, "2025-11-06 22:00"),
    ("Chỉ đạo ngày 28/11/2025", "", {"dm": 256.2, "av": 378, "st": 173.2},
     None, "2025-12-01 06:30"),
]

DAM, NEAR, DELTA = (ReservoirWard.Zone.DAM_AREA, ReservoirWard.Zone.NEAR_DOWNSTREAM,
                    ReservoirWard.Zone.DELTA_DOWNSTREAM)
# Table B.1 ("*" = to be checked on a map) and B.2. "phường X" = a ward (not a commune).
VU_GIA = ["Thượng Đức", "Hà Nha", "Phú Thuận", "Vu Gia", "Đại Lộc"]
THU_BON = ["Nông Sơn", "Quế Phước"]
CONFLUENCE = ["Gò Nổi", "Điện Bàn Tây", "phường Điện Bàn", "Thu Bồn", "Duy Xuyên", "Nam Phước",
              "Duy Nghĩa", "phường Hội An", "phường Hội An Tây", "phường Hội An Đông"]
LINKS = {
    "av": {DAM: ["Đông Giang*", "Sông Kôn*"], NEAR: ["Bến Hiên", "Sông Vàng*"],
           DELTA: VU_GIA + CONFLUENCE},
    "sb": {DAM: ["Nam Giang"], NEAR: ["Bến Giằng"], DELTA: VU_GIA + CONFLUENCE},
    "dm": {DAM: ["Khâm Đức"], NEAR: ["Thạnh Mỹ*"], DELTA: VU_GIA + CONFLUENCE},
    "st": {DAM: ["Trà Tân", "Trà Đốc", "Trà My*"],
           NEAR: ["Lãnh Ngọc", "Phước Trà", "Hiệp Đức", "Việt An"], DELTA: THU_BON + CONFLUENCE},
}


def nfc(text):
    return unicodedata.normalize("NFC", text).strip()


def find_ward(label):
    """'phường X' -> the ward named X; otherwise the unit named X if exactly one exists."""
    label = nfc(label)
    if label.startswith("phường "):
        return list(Ward.objects.filter(kind=Ward.Kind.WARD, name=label[len("phường "):]))
    return list(Ward.objects.filter(name=label))


def aware(text):
    return timezone.make_aware(datetime.strptime(text, "%Y-%m-%d %H:%M")) if text else None


class Command(BaseCommand):
    help = "Nạp dữ liệu nền giai đoạn 2: 4 hồ, ngưỡng quy định, chỉ đạo ví dụ, liên kết hồ – phường/xã"

    @transaction.atomic
    def handle(self, *args, **opts):
        if Ward.objects.count() < 94:
            raise CommandError("Chưa nạp phường/xã. Chạy: python manage.py load_wards")
        res = {}
        for code, key, name, mndbt, order in RESERVOIRS:
            res[code], _ = Reservoir.objects.update_or_create(
                code=code, defaults={"model_key": key, "name": name, "normal_water_level": mndbt,
                                     "display_order": order})
        self.stdout.write(f"Hồ chứa: {Reservoir.objects.count()}")

        n = 0
        for kind, per_res in THRESHOLDS.items():
            for code, values in per_res.items():
                for (start, end), (low, high) in zip(PERIODS, values):
                    RegulatoryThreshold.objects.update_or_create(
                        reservoir=res[code], kind=kind, start_day=start,
                        defaults={"end_day": end, "value_low": low, "value_high": high,
                                  "document": DOC_1865})
                    n += 1
        self.stdout.write(f"Ngưỡng quy định: {n} dòng (Bảng A.1, A.2)")

        n = 0
        for document, requirement, levels, start, deadline in DIRECTIVES:
            for code, level in levels.items():
                exists = OperatingDirective.objects.filter(reservoir=res[code], document=document)
                if not exists.exists():
                    OperatingDirective.objects.create(
                        reservoir=res[code], document=document, requirement=requirement,
                        target_level=level, starts_at=aware(start), deadline=aware(deadline),
                        is_active=False)
                    n += 1
        self.stdout.write(f"Chỉ đạo điều hành ví dụ (Bảng A.4, đã hết hiệu lực): thêm {n}, "
                          f"tổng {OperatingDirective.objects.count()}")

        linked, unmatched = 0, []
        for code, zones in LINKS.items():
            for zone, labels in zones.items():
                for label in labels:
                    check = label.endswith("*")
                    wards = find_ward(label.rstrip("*"))
                    if len(wards) != 1:
                        unmatched.append(f"{res[code].name}: '{label}' "
                                         f"({'không có' if not wards else f'{len(wards)} đơn vị trùng tên'})")
                        continue
                    ReservoirWard.objects.update_or_create(
                        reservoir=res[code], ward=wards[0],
                        defaults={"zone": zone, "needs_verification": check})
                    linked += 1
        self.stdout.write(f"Liên kết hồ – phường/xã: {linked} (tổng {ReservoirWard.objects.count()})")
        if unmatched:
            self.stdout.write(self.style.WARNING(
                "Tên KHÔNG khớp bảng phường/xã (bỏ qua, không tự đoán):\n  " + "\n  ".join(unmatched)))
        else:
            self.stdout.write(self.style.SUCCESS("Mọi tên trong Phụ lục B đều khớp bảng phường/xã."))
