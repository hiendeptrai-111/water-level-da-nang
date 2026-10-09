"""Hourly run (spec step "cap_nhat_du_bao"). Prints a sample cron line; never installs it."""
import sys
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from reservoirs.pipeline import run_live


def cron_line():
    python = Path(sys.executable)
    manage = Path(settings.BASE_DIR) / "manage.py"
    log = Path(settings.BASE_DIR) / "logs" / "update_forecasts.log"
    return f"20 * * * * cd {settings.BASE_DIR} && {python} {manage} update_forecasts >> {log} 2>&1"


class Command(BaseCommand):
    help = ("Cập nhật mỗi giờ: dữ liệu hồ (cổng PCTT) → mưa Open-Meteo → ghi DB → du_bao() "
            "cho 4 hồ → lưu kết quả → cảnh báo và thông báo")

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true",
                            help="bỏ qua giới hạn 1 lần/giờ của cổng PCTT và tính lại dự báo đã có")
        parser.add_argument("--skip-portal", action="store_true", help="không gọi cổng PCTT")
        parser.add_argument("--skip-rain", action="store_true", help="không gọi Open-Meteo")
        parser.add_argument("--print-cron", action="store_true", help="chỉ in dòng cron mẫu")

    def handle(self, *args, **opts):
        if opts["print_cron"]:
            self.stdout.write(cron_line())
            return
        run = run_live(out=self.stdout.write, force=opts["force"],
                       skip_portal=opts["skip_portal"], skip_rain=opts["skip_rain"])
        status = self.style.SUCCESS("Xong") if not run.failures else \
            self.style.WARNING(f"Xong, {run.failures} bước lỗi (xem trang Tình trạng dữ liệu)")
        self.stdout.write(f"{status}. Lần chạy {run.id}")
        self.stdout.write("\nDòng cron mẫu (KHÔNG tự bật; thêm bằng `crontab -e` nếu muốn, "
                          "tạo thư mục logs/ trước):\n  " + cron_line())
