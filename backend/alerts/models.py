from django.conf import settings
from django.db import models
from django.utils.timezone import localtime

from reservoirs.models import AlertLevel


class Alert(models.Model):
    """An alert episode. Automatic alerts (CN10) are opened when a reservoir's level rises,
    extended while it lasts and ended when it falls. Emergency alerts (manual) are phase 5."""

    class Source(models.TextChoices):
        AUTO = "auto", "Tự động"
        MANUAL = "manual", "Thủ công"

    level = models.CharField("mức", max_length=10,
                             choices=[c for c in AlertLevel.choices if c[0] != AlertLevel.NORMAL])
    source = models.CharField("nguồn", max_length=10, choices=Source.choices, default=Source.AUTO)
    content = models.TextField("nội dung")
    reservoirs = models.ManyToManyField("reservoirs.Reservoir", verbose_name="hồ liên quan",
                                        related_name="alerts")
    wards = models.ManyToManyField("catalog.Ward", verbose_name="phường/xã ảnh hưởng",
                                   related_name="alerts", blank=True)
    starts_at = models.DateTimeField("bắt đầu", db_index=True)
    valid_until = models.DateTimeField("hiệu lực đến")
    ended_at = models.DateTimeField("kết thúc lúc", null=True, blank=True)
    issued_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="người phát",
                                  on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    forecast = models.ForeignKey("reservoirs.Forecast", verbose_name="kết quả dự báo",
                                 on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name="alerts")
    is_simulation = models.BooleanField("mô phỏng", default=False, db_index=True)
    # Data time (not wall-clock) of the last notification sent for this episode: the
    # 3-hour reminder of a lasting "warning" counts in forecast hours, so replays behave
    # exactly like live runs.
    last_notified_at = models.DateTimeField("thông báo gần nhất (giờ số liệu)",
                                            null=True, blank=True)

    class Meta:
        verbose_name = "cảnh báo"
        verbose_name_plural = "cảnh báo"
        ordering = ["-starts_at", "-id"]

    def __str__(self):
        names = ", ".join(r.name for r in self.reservoirs.all()) if self.pk else ""
        sim = " [mô phỏng]" if self.is_simulation else ""
        return f"{self.get_level_display()} {names} {localtime(self.starts_at):%d/%m/%Y %H:%M}{sim}"


class AlertState(models.Model):
    """Last automatic level of each reservoir and the forecast hour it was evaluated at.
    Kept separately for live runs and replays so a replay never touches live alerts."""
    reservoir = models.ForeignKey("reservoirs.Reservoir", verbose_name="hồ",
                                  on_delete=models.CASCADE, related_name="+")
    is_simulation = models.BooleanField("mô phỏng", default=False)
    level = models.CharField("mức", max_length=10, choices=AlertLevel.choices,
                             default=AlertLevel.NORMAL)
    evaluated_at = models.DateTimeField("xét đến giờ", null=True, blank=True)

    class Meta:
        verbose_name = "trạng thái cảnh báo tự động"
        verbose_name_plural = "trạng thái cảnh báo tự động"
        constraints = [models.UniqueConstraint(fields=["reservoir", "is_simulation"],
                                               name="uniq_alert_state")]

    def __str__(self):
        return f"{self.reservoir}: {self.get_level_display()}"


class Notification(models.Model):
    class Channel(models.TextChoices):
        WEB = "web", "Website"
        EMAIL = "email", "Email"

    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="người nhận",
                                  on_delete=models.CASCADE, related_name="notifications")
    alert = models.ForeignKey(Alert, verbose_name="cảnh báo", on_delete=models.CASCADE,
                              related_name="notifications")
    channel = models.CharField("kênh", max_length=10, choices=Channel.choices)
    content = models.TextField("nội dung")
    is_reminder = models.BooleanField("nhắc lại", default=False)
    sent = models.BooleanField("đã gửi", default=False)
    created_at = models.DateTimeField("tạo lúc", auto_now_add=True, db_index=True)
    seen_at = models.DateTimeField("đã xem lúc", null=True, blank=True)

    class Meta:
        verbose_name = "thông báo"
        verbose_name_plural = "thông báo"
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["recipient", "channel", "seen_at"])]

    def __str__(self):
        return f"{self.recipient} – {self.get_channel_display()} – {self.alert_id}"
