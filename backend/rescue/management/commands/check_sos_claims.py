"""Every minute: SOS unassigned for longer than sos_self_claim_wait_minutes -> the nearest
available teams are notified (once per SOS); priority scores refreshed; flood points expire.
Prints a sample cron line; never installs it."""
import sys
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from rescue import services
from rescue.models import SOS


def cron_line():
    log = Path(settings.BASE_DIR) / "logs" / "check_sos_claims.log"
    return (f"* * * * * cd {settings.BASE_DIR} && {Path(sys.executable)} manage.py check_sos_claims "
            f">> {log} 2>&1")


class Command(BaseCommand):
    help = "Mỗi phút: báo các đội rảnh gần nhất về SOS quá thời gian chờ; cập nhật điểm ưu tiên; điểm ngập hết hạn"

    def add_arguments(self, parser):
        parser.add_argument("--print-cron", action="store_true")

    def handle(self, *args, **opts):
        if opts["print_cron"]:
            self.stdout.write(cron_line())
            return
        notified = services.notify_claimable()
        for sos in SOS.objects.filter(status__in=SOS.OPEN):
            services.refresh_priority(sos)
        expired = services.expire_floods()
        if notified or expired or opts["verbosity"] > 1:
            self.stdout.write(f"Báo tự nhận: {notified or 'không có'}; điểm ngập hết hạn: {expired}")
