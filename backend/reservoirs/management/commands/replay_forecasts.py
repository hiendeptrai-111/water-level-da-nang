"""Replay the forecast pipeline hour by hour on historical data (spec step "phat_lai"),
e.g. October 2025, to demonstrate the system when the current weather is calm.

At hour t only data up to t is given to du_bao(). Results are stored with is_simulation=True
(live results are never overwritten) and no email is ever sent. Simulated alerts of a previous
replay are cleared first.
"""
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError

from reservoirs.models import Reservoir
from reservoirs.pipeline import run_replay


def parse(text):
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            pass
    raise CommandError(f"Thời điểm không hợp lệ: {text} (dạng 'YYYY-MM-DD' hoặc 'YYYY-MM-DD HH:MM')")


class Command(BaseCommand):
    help = "Phát lại dự báo theo từng giờ trên dữ liệu lịch sử (mô phỏng, không gửi email)"

    def add_arguments(self, parser):
        parser.add_argument("--from", dest="start", required=True, help="vd 2025-10-01")
        parser.add_argument("--to", dest="end", required=True,
                            help="vd 2025-10-31 (ngày không kèm giờ = đến 23:00 ngày đó)")
        parser.add_argument("--web-notifications", action="store_true",
                            help="tạo cả thông báo trên website (ghi rõ [MÔ PHỎNG]) để thử chuông "
                                 "thông báo; mặc định không tạo")

    def handle(self, *args, **opts):
        start, end = parse(opts["start"]), parse(opts["end"])
        if len(opts["end"]) == 10:
            end = end.replace(hour=23)
        if end < start:
            raise CommandError("--to phải sau --from")
        if Reservoir.objects.count() != 4:
            raise CommandError("Chưa nạp 4 hồ. Chạy load_reservoirs và load_history trước")
        self.stdout.write(f"Phát lại {start:%d/%m/%Y %H:%M} → {end:%d/%m/%Y %H:%M} (mô phỏng, không gửi email)")
        run = run_replay(start, end, out=self.stdout.write,
                         web_notifications=opts["web_notifications"])
        self.stdout.write(self.style.SUCCESS("Xong") if not run.failures
                          else self.style.WARNING(f"Xong, {run.failures} hồ lỗi"))
