"""DEMO DATA ONLY: sample accounts and rescue teams to try the system. Do not use in production."""
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.models import User
from catalog.models import RescueTeam, Ward

DEMO_PASSWORD = "Demo12345"

# name, phone, vehicles, members, base commune (kind, name), communes usually covered
TEAMS = [
    ("[DEMO] Đội cứu hộ Đại Lộc", "0905000001", ["rescue_truck", "motorbike"], 12, ("commune", "Đại Lộc"),
     ["Đại Lộc", "Vu Gia", "Hà Nha", "Thượng Đức", "Phú Thuận"]),
    ("[DEMO] Đội cứu hộ ca nô Hội An", "0905000002", ["boat", "motorbike"], 8, ("ward", "Hội An"),
     ["Hội An", "Hội An Tây", "Hội An Đông", "Duy Xuyên", "Duy Nghĩa", "Nam Phước"]),
]
# Phase 4 demo: flood points (approved) and SOS near commune centres, offsets in degrees.
# (commune, d_lat, d_lon, level)
DEMO_FLOODS = [("Đại Lộc", 0.004, 0.012, "no_car"), ("Vu Gia", -0.003, 0.006, "no_motorbike"),
               ("Duy Xuyên", 0.002, -0.004, "boat_only"), ("Gò Nổi", 0.0, 0.003, "passable")]
# (commune, d_lat, d_lon, phone, minutes ago, people, groups, water level, note)
DEMO_SOS = [
    ("Đại Lộc", 0.006, -0.008, "0900000101", 25, "2-4", ["elderly"], "chest", "[DEMO] Nhà 1 tầng, nước đang lên"),
    ("Duy Xuyên", -0.004, 0.005, "0900000102", 6, "5+", ["child", "sick"], "roof", "[DEMO] Cả nhà trên mái"),
    ("Điện Bàn Tây", 0.003, 0.002, "0900000103", 40, "1", [], "knee", "[DEMO] Người già sống một mình"),
]

# (email, full name, phone, role, ward (kind, name), team index)
USERS = [
    ("admin@demo.example.com", "[DEMO] Quản trị viên", "0900000001", "admin", None, None),
    ("doi1@demo.example.com", "[DEMO] Đội cứu hộ Đại Lộc", "0900000011", "rescue_team", None, 0),
    ("doi2@demo.example.com", "[DEMO] Đội ca nô Hội An", "0900000012", "rescue_team", None, 1),
    ("dan1@demo.example.com", "[DEMO] Nguyễn Văn A", "0900000021", "citizen", ("commune", "Đại Lộc"), None),
    ("dan2@demo.example.com", "[DEMO] Trần Thị B", "0900000022", "citizen", ("commune", "Duy Xuyên"), None),
    ("dan3@demo.example.com", "[DEMO] Lê Văn C", "0900000023", "citizen", ("ward", "Hội An"), None),
]


class Command(BaseCommand):
    help = "Tạo DỮ LIỆU DEMO: 1 admin, 2 đội cứu hộ (1 đội có ca nô), 2 tài khoản đội, 3 người dân"

    @transaction.atomic
    def handle(self, *args, **opts):
        if not settings.DEBUG:
            raise CommandError(
                "TỪ CHỐI tạo dữ liệu demo vì DJANGO_DEBUG=false (môi trường triển khai thật). "
                "Tài khoản demo dùng mật khẩu công khai trong README, ai cũng đăng nhập được. "
                "Chỉ chạy lệnh này trên máy phát triển với DJANGO_DEBUG=true.")
        if Ward.objects.count() < 94:
            raise CommandError("Chưa nạp phường/xã. Chạy: python manage.py load_wards")
        teams = []
        for name, phone, vehicles, members, (kind, base), covered in TEAMS:
            base_ward = Ward.objects.get(kind=kind, name=base)
            team, _ = RescueTeam.objects.update_or_create(
                name=name, defaults={"phone_number": phone, "vehicles": vehicles, "member_count": members,
                                     "base_name": f"[DEMO] Trụ sở {base_ward}",
                                     "base_latitude": base_ward.latitude, "base_longitude": base_ward.longitude,
                                     "status": RescueTeam.Status.AVAILABLE})
            team.service_wards.set(Ward.objects.filter(name__in=covered))
            teams.append(team)
        rows = []
        for email, full_name, phone, role, ward_key, team_idx in USERS:
            ward = Ward.objects.get(kind=ward_key[0], name=ward_key[1]) if ward_key else None
            user = User.objects.filter(email=email).first() or User(email=email)
            user.full_name, user.phone_number, user.role = full_name, phone, role
            user.ward = ward
            user.rescue_team = teams[team_idx] if team_idx is not None else None
            user.email_verified, user.is_active = True, True
            user.set_password(DEMO_PASSWORD)
            user.save()
            rows.append((role, email, phone, str(ward or user.rescue_team or "")))

        self.seed_rescue_demo()
        self.stdout.write(self.style.WARNING(
            "\n=== DỮ LIỆU DEMO, chỉ dùng để thử hệ thống, KHÔNG dùng khi triển khai thật ==="))
        self.stdout.write(f"Mật khẩu chung của mọi tài khoản demo: {DEMO_PASSWORD}\n")
        for role, email, phone, extra in rows:
            self.stdout.write(f"  {role:<12} {email:<26} {phone}  {extra}")
        self.stdout.write("\nĐội cứu hộ demo:")
        for t in teams:
            labels = dict(RescueTeam.Vehicle.choices)
            self.stdout.write(f"  {t.name}: {', '.join(labels[v] for v in t.vehicles)}")


    def seed_rescue_demo(self):
        """Phase 4: demo flood points and SOS (is_demo=True), recreated on every run."""
        from datetime import timedelta
        from decimal import Decimal

        from django.utils import timezone

        from core.services import get_config
        from rescue import services
        from rescue.models import SOS, FloodPoint

        SOS.objects.filter(is_demo=True).delete()
        FloodPoint.objects.filter(is_demo=True).delete()
        admin = User.objects.get(email="admin@demo.example.com")
        now = timezone.now()
        ttl = timedelta(hours=get_config("flood_point_ttl_hours"))
        for name, dlat, dlon, level in DEMO_FLOODS:
            w = Ward.objects.filter(name=name, latitude__isnull=False).first()
            if w is None:
                continue
            FloodPoint.objects.create(latitude=w.latitude + Decimal(str(dlat)), longitude=w.longitude + Decimal(str(dlon)),
                                      level=level, status=FloodPoint.Status.APPROVED, approved_by=admin,
                                      approved_at=now, reporter=admin, expires_at=now + ttl, is_demo=True)
        for name, dlat, dlon, phone, ago, people, groups, water, note in DEMO_SOS:
            w = Ward.objects.filter(name=name, latitude__isnull=False).first()
            if w is None:
                continue
            sos, _ = services.submit(user=None, phone=phone, latitude=w.latitude + Decimal(str(dlat)),
                                     longitude=w.longitude + Decimal(str(dlon)), accuracy_m=15,
                                     extra={"people_count": people, "vulnerable_groups": groups,
                                            "water_level": water, "note": note, "is_demo": True})
            SOS.objects.filter(pk=sos.pk).update(created_at=now - timedelta(minutes=ago))
            sos.history.update(time=now - timedelta(minutes=ago))
            sos.refresh_from_db()
            services.refresh_priority(sos)
        self.stdout.write(f"Demo cứu hộ: {FloodPoint.objects.filter(is_demo=True).count()} điểm ngập (đã duyệt), "
                          f"{SOS.objects.filter(is_demo=True).count()} SOS mô phỏng (số điện thoại 090000010x)")
