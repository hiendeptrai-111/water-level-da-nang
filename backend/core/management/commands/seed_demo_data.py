"""DEMO DATA ONLY: sample accounts and rescue teams to try the system. Do not use in production."""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.models import User
from catalog.models import RescueTeam, Ward

DEMO_PASSWORD = "Demo12345"

TEAMS = [
    ("[DEMO] Đội cứu hộ Đại Lộc", "0905000001", ["rescue_truck", "motorbike"]),
    ("[DEMO] Đội cứu hộ ca nô Hội An", "0905000002", ["boat", "motorbike"]),
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
        if Ward.objects.count() < 94:
            raise CommandError("Chưa nạp phường/xã. Chạy: python manage.py load_wards")
        teams = []
        for name, phone, vehicles in TEAMS:
            team, _ = RescueTeam.objects.update_or_create(
                name=name, defaults={"phone_number": phone, "vehicles": vehicles})
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

        self.stdout.write(self.style.WARNING(
            "\n=== DỮ LIỆU DEMO, chỉ dùng để thử hệ thống, KHÔNG dùng khi triển khai thật ==="))
        self.stdout.write(f"Mật khẩu chung của mọi tài khoản demo: {DEMO_PASSWORD}\n")
        for role, email, phone, extra in rows:
            self.stdout.write(f"  {role:<12} {email:<26} {phone}  {extra}")
        self.stdout.write("\nĐội cứu hộ demo:")
        for t in teams:
            labels = dict(RescueTeam.Vehicle.choices)
            self.stdout.write(f"  {t.name}: {', '.join(labels[v] for v in t.vehicles)}")
