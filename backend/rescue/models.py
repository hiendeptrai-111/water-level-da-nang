import secrets

from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils.timezone import localtime

from accounts.models import phone_validator

CODE_ALPHABET = "ACDEFHJKMNPQRTUVWXY3479"     # no look-alikes (0/O, 1/I/L, 2/Z, 5/S, 6/G, 8/B)


def new_code():
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(6))


class SOS(models.Model):
    """A call for help (CN15). Status flow (spec Hình 2):
    new -> received -> moving -> rescued -> closed, with cancelled (by the sender) and
    unreachable (team could not reach / contact the sender). Every change is a SOSHistory row."""

    class Status(models.TextChoices):
        NEW = "new", "Mới gửi"
        RECEIVED = "received", "Đã tiếp nhận"
        MOVING = "moving", "Đang di chuyển"
        RESCUED = "rescued", "Đã cứu"
        CLOSED = "closed", "Đóng"
        CANCELLED = "cancelled", "Huỷ"
        UNREACHABLE = "unreachable", "Không liên lạc được"

    OPEN = (Status.NEW, Status.RECEIVED, Status.MOVING)
    FINISHED = (Status.CLOSED, Status.CANCELLED)            # anonymised after sos_anonymize_days

    class People(models.TextChoices):
        ONE = "1", "1 người"
        FEW = "2-4", "2–4 người"
        MANY = "5+", "5 người trở lên"

    class Vulnerable(models.TextChoices):
        ELDERLY = "elderly", "Người già"
        CHILD = "child", "Trẻ nhỏ"
        SICK = "sick", "Người bệnh"
        INJURED = "injured", "Người bị thương"
        PREGNANT = "pregnant", "Phụ nữ mang thai"

    class WaterLevel(models.TextChoices):
        KNEE = "knee", "Ngang gối"
        CHEST = "chest", "Ngang ngực"
        FIRST_FLOOR = "first_floor", "Ngập tầng 1"
        ROOF = "roof", "Phải lên mái"

    code = models.CharField("mã SOS", max_length=8, unique=True, default=new_code)
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="người gửi", on_delete=models.SET_NULL,
                               null=True, blank=True, related_name="sos_requests")
    phone = models.CharField("số điện thoại", max_length=10, blank=True, validators=[phone_validator])
    latitude = models.DecimalField("vĩ độ", max_digits=9, decimal_places=6)
    longitude = models.DecimalField("kinh độ", max_digits=9, decimal_places=6)
    accuracy_m = models.FloatField("độ chính xác GPS (m)", null=True, blank=True)
    location_source = models.CharField("nguồn vị trí", max_length=10, default="gps",
                                       choices=[("gps", "GPS"), ("map", "Chọn trên bản đồ")])
    ward = models.ForeignKey("catalog.Ward", verbose_name="phường/xã", on_delete=models.SET_NULL,
                             null=True, blank=True, related_name="sos_requests")
    people_count = models.CharField("số người", max_length=4, choices=People.choices, blank=True)
    vulnerable_groups = ArrayField(models.CharField(max_length=12, choices=Vulnerable.choices),
                                   verbose_name="nhóm cần ưu tiên", default=list, blank=True)
    water_level = models.CharField("mức nước", max_length=12, choices=WaterLevel.choices, blank=True)
    note = models.CharField("ghi chú", max_length=300, blank=True)
    photo = models.FileField("ảnh", upload_to="sos/%Y/%m/", blank=True)
    priority_score = models.FloatField("điểm ưu tiên", default=0, db_index=True)
    status = models.CharField("trạng thái", max_length=12, choices=Status.choices, default=Status.NEW,
                              db_index=True)
    team = models.ForeignKey("catalog.RescueTeam", verbose_name="đội phụ trách", on_delete=models.SET_NULL,
                             null=True, blank=True, related_name="sos_tasks")
    merged_into = models.ForeignKey("self", verbose_name="gộp vào", on_delete=models.SET_NULL,
                                    null=True, blank=True, related_name="merged")
    handled_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="admin tiếp nhận",
                                   on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    eta_seconds = models.FloatField("thời gian tiếp cận ước tính (giây)", null=True, blank=True)
    route = models.JSONField("tuyến đường gợi ý", default=list, blank=True)
    route_mode = models.CharField("phương tiện tuyến", max_length=6, blank=True)
    arrived_at = models.DateTimeField("đội đến nơi lúc", null=True, blank=True)
    claim_notified_at = models.DateTimeField("đã báo các đội tự nhận lúc", null=True, blank=True)
    device_id = models.CharField("mã thiết bị", max_length=64, blank=True)
    ip_address = models.GenericIPAddressField("địa chỉ IP", null=True, blank=True)
    created_at = models.DateTimeField("gửi lúc", auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField("cập nhật lúc", auto_now=True)
    finished_at = models.DateTimeField("kết thúc lúc", null=True, blank=True)
    anonymized_at = models.DateTimeField("ẩn danh hoá lúc", null=True, blank=True)
    is_demo = models.BooleanField("dữ liệu demo", default=False)

    class Meta:
        verbose_name = "SOS"
        verbose_name_plural = "SOS"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "created_at"]), models.Index(fields=["phone", "status"])]

    def __str__(self):
        return f"SOS {self.code} ({self.get_status_display()})"

    @property
    def is_open(self):
        return self.status in self.OPEN


class SOSHistory(models.Model):
    """One row per status change (or event such as 'arrived', 'returned'). Processing-time
    statistics are computed from this table."""
    sos = models.ForeignKey(SOS, verbose_name="SOS", on_delete=models.CASCADE, related_name="history")
    from_status = models.CharField("từ trạng thái", max_length=12, choices=SOS.Status.choices, blank=True)
    to_status = models.CharField("sang trạng thái", max_length=12, choices=SOS.Status.choices)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="người thực hiện", on_delete=models.SET_NULL,
                              null=True, blank=True, related_name="+")
    actor_label = models.CharField("người thực hiện (lúc ghi)", max_length=255, blank=True)
    note = models.CharField("ghi chú", max_length=300, blank=True)
    time = models.DateTimeField("thời điểm", auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "lịch sử SOS"
        verbose_name_plural = "lịch sử SOS"
        ordering = ["time", "id"]

    def __str__(self):
        return f"{self.sos.code}: {self.from_status or '—'} → {self.to_status} {localtime(self.time):%d/%m %H:%M}"


class FloodPoint(models.Model):
    """A flooded road reported by a resident (pending) or a team/admin (approved at once)
    (CN20, CN21). Only approved, unexpired points affect routes and are shown publicly."""

    class Level(models.TextChoices):
        PASSABLE = "passable", "Đi lại được"
        NO_MOTORBIKE = "no_motorbike", "Xe máy không qua được"
        NO_CAR = "no_car", "Ô tô không qua được"
        BOAT_ONLY = "boat_only", "Chỉ ca nô"

    class Status(models.TextChoices):
        PENDING = "pending", "Chờ duyệt"
        APPROVED = "approved", "Đã duyệt"
        REJECTED = "rejected", "Từ chối"
        EXPIRED = "expired", "Hết hạn"

    latitude = models.DecimalField("vĩ độ", max_digits=9, decimal_places=6)
    longitude = models.DecimalField("kinh độ", max_digits=9, decimal_places=6)
    level = models.CharField("mức ngập", max_length=14, choices=Level.choices)
    photo = models.FileField("ảnh", upload_to="flood/%Y/%m/", blank=True)
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="người báo", on_delete=models.SET_NULL,
                                 null=True, blank=True, related_name="flood_reports")
    status = models.CharField("trạng thái", max_length=10, choices=Status.choices, default=Status.PENDING,
                              db_index=True)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="người duyệt", on_delete=models.SET_NULL,
                                    null=True, blank=True, related_name="+")
    approved_at = models.DateTimeField("duyệt lúc", null=True, blank=True)
    merged_into = models.ForeignKey("self", verbose_name="gộp vào", on_delete=models.SET_NULL,
                                    null=True, blank=True, related_name="merged")
    created_at = models.DateTimeField("báo lúc", auto_now_add=True)
    confirmed_at = models.DateTimeField("xác nhận gần nhất", auto_now_add=True)
    expires_at = models.DateTimeField("hết hạn lúc", db_index=True)
    is_demo = models.BooleanField("dữ liệu demo", default=False)

    class Meta:
        verbose_name = "điểm ngập"
        verbose_name_plural = "điểm ngập"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_level_display()} ({self.get_status_display()}) {localtime(self.created_at):%d/%m %H:%M}"
