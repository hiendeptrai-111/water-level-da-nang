"""Every day: SOS closed or cancelled more than sos_anonymize_days ago are anonymised (phone,
photo, note, sender, device, IP and route removed; position -> centre of its commune)."""
import sys
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from rescue import services


class Command(BaseCommand):
    help = "Ẩn danh hoá SOS đã đóng quá số ngày cấu hình (sos_anonymize_days)"

    def add_arguments(self, parser):
        parser.add_argument("--print-cron", action="store_true")

    def handle(self, *args, **opts):
        if opts["print_cron"]:
            log = Path(settings.BASE_DIR) / "logs" / "anonymize_sos.log"
            self.stdout.write(f"30 2 * * * cd {settings.BASE_DIR} && {Path(sys.executable)} manage.py "
                              f"anonymize_sos >> {log} 2>&1")
            return
        n = services.anonymize()
        self.stdout.write(f"Đã ẩn danh hoá {n} SOS.")
