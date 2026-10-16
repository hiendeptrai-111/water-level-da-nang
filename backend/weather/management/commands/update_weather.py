"""Weather of every commune with coordinates (CN13, CN14). Also run by update_forecasts
every hour (same cron line); this command runs only the weather step."""
from django.core.management.base import BaseCommand

from reservoirs.models import UpdateRun
from reservoirs.pipeline import Run, step_weather


class Command(BaseCommand):
    help = "Cập nhật thời tiết phường/xã từ Open-Meteo (24 giờ qua, 72 giờ tới)"

    def handle(self, *args, **opts):
        run = Run(UpdateRun.Kind.LIVE, self.stdout.write)
        step_weather(run)
        if run.failures:
            self.stdout.write(self.style.WARNING("Lỗi: dữ liệu thời tiết cũ được giữ nguyên"))
