from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models
from django.utils.timezone import localtime

month_day_validator = RegexValidator(r"^(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$",
                                     "Dạng tháng-ngày, ví dụ 09-01.")


class AlertLevel(models.TextChoices):
    """Alert levels shared by forecasts and alerts (spec section 4.3). The automatic levels
    come straight from du_bao() (see forecasting.LEVEL_FROM_MODEL); EMERGENCY is manual (phase 5)."""
    NORMAL = "normal", "Bình thường"
    WATCH = "watch", "Theo dõi"
    WARNING = "warning", "Cảnh báo"
    EMERGENCY = "emergency", "Khẩn cấp"


LEVEL_ORDER = [AlertLevel.NORMAL, AlertLevel.WATCH, AlertLevel.WARNING, AlertLevel.EMERGENCY]


class Reservoir(models.Model):
    code = models.CharField("mã", max_length=4, unique=True)           # av, dm, sb, st
    model_key = models.CharField("khoá trong module dự báo", max_length=20, unique=True)
    name = models.CharField("tên hồ", max_length=100)
    normal_water_level = models.FloatField("MNDBT (m)")
    latitude = models.DecimalField("vĩ độ đập", max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField("kinh độ đập", max_digits=9, decimal_places=6,
                                    null=True, blank=True)
    display_order = models.PositiveSmallIntegerField("thứ tự hiển thị", default=0)

    class Meta:
        verbose_name = "hồ chứa"
        verbose_name_plural = "hồ chứa"
        ordering = ["display_order", "name"]

    def __str__(self):
        return self.name


class ReservoirWard(models.Model):
    """Appendix B: which communes lie in each reservoir's dam area / downstream."""

    class Zone(models.TextChoices):
        DAM_AREA = "dam_area", "Khu vực đập"
        NEAR_DOWNSTREAM = "near_downstream", "Hạ du gần"
        DELTA_DOWNSTREAM = "delta_downstream", "Hạ du đồng bằng"

    reservoir = models.ForeignKey(Reservoir, verbose_name="hồ", on_delete=models.CASCADE,
                                  related_name="ward_links")
    ward = models.ForeignKey("catalog.Ward", verbose_name="phường/xã", on_delete=models.CASCADE,
                             related_name="reservoir_links")
    zone = models.CharField("loại vùng", max_length=20, choices=Zone.choices)
    needs_verification = models.BooleanField(
        "cần xác minh trên bản đồ", default=False,
        help_text="Các xã đánh dấu (*) ở Phụ lục B: chưa chắc nằm phía trên hay phía dưới đập.")

    class Meta:
        verbose_name = "liên kết hồ – phường/xã"
        verbose_name_plural = "liên kết hồ – phường/xã"
        constraints = [models.UniqueConstraint(fields=["reservoir", "ward"],
                                               name="uniq_reservoir_ward")]

    def __str__(self):
        return f"{self.reservoir} – {self.ward} ({self.get_zone_display()})"


class OperationRecord(models.Model):
    """Hourly operating data of one reservoir (PCTT Da Nang portal), as stored in the data
    store kho_du_lieu/van_hanh/van_hanh.csv (duplicates already resolved by
    xu_ly_du_lieu.bo_trung_moc_gio). Values are kept as published; cleaning happens in
    du_bao() and in the suspicious flag below."""
    reservoir = models.ForeignKey(Reservoir, verbose_name="hồ", on_delete=models.CASCADE,
                                  related_name="records")
    time = models.DateTimeField("thời điểm", db_index=True)
    water_level = models.FloatField("mực nước (m)", null=True, blank=True)
    inflow = models.FloatField("lưu lượng đến (m³/s)", null=True, blank=True)
    turbine_flow = models.FloatField("lưu lượng qua máy (m³/s)", null=True, blank=True)
    spillway_flow = models.FloatField("lưu lượng qua tràn (m³/s)", null=True, blank=True)
    suspicious = models.BooleanField(
        "nghi ngờ", default=False,
        help_text="Bị quy trình làm sạch lúc huấn luyện loại bỏ (ngoài phạm vi, loại trừ thủ "
                  "công, gai), hoặc là giờ mới nhất mà du_bao() báo cần xác nhận.")

    class Meta:
        verbose_name = "số liệu vận hành"
        verbose_name_plural = "số liệu vận hành"
        ordering = ["reservoir", "time"]
        constraints = [models.UniqueConstraint(fields=["reservoir", "time"],
                                               name="uniq_operation_record")]

    def __str__(self):
        return f"{self.reservoir} {localtime(self.time):%d/%m/%Y %H:%M}"


class Rainfall(models.Model):
    """Hourly catchment rainfall = arithmetic mean of the points in
    du_bao/models/toa_do_mua.json (same as the training data)."""

    class Source(models.TextChoices):
        HISTORICAL = "historical", "Open-Meteo Historical (archive)"
        FORECAST = "forecast", "Open-Meteo Forecast (past_days)"

    reservoir = models.ForeignKey(Reservoir, verbose_name="hồ", on_delete=models.CASCADE,
                                  related_name="rainfall")
    time = models.DateTimeField("thời điểm", db_index=True)
    rain_mm = models.FloatField("mưa (mm)")
    source = models.CharField("nguồn", max_length=12, choices=Source.choices)

    class Meta:
        verbose_name = "lượng mưa"
        verbose_name_plural = "lượng mưa"
        ordering = ["reservoir", "time"]
        constraints = [models.UniqueConstraint(fields=["reservoir", "time"], name="uniq_rainfall")]

    def __str__(self):
        return f"{self.reservoir} {localtime(self.time):%d/%m/%Y %H:%M} {self.rain_mm} mm"


class Forecast(models.Model):
    """One horizon of one du_bao() call. `details` keeps the whole du_bao() result."""
    reservoir = models.ForeignKey(Reservoir, verbose_name="hồ", on_delete=models.CASCADE,
                                  related_name="forecasts")
    issued_at = models.DateTimeField("thời điểm dự báo", db_index=True,
                                     help_text="Giờ của số liệu mới nhất đưa vào mô hình.")
    horizon = models.PositiveSmallIntegerField("tầm (giờ)", choices=[(1, "1 giờ"), (3, "3 giờ"),
                                                                    (6, "6 giờ")])
    expected_level = models.FloatField("mực nước dự kiến (m)", null=True, blank=True)
    alert_level = models.CharField("mức cảnh báo", max_length=10, choices=AlertLevel.choices,
                                   null=True, blank=True)
    baseline_alert = models.BooleanField("Baseline báo", null=True, blank=True)
    a_alert = models.BooleanField("phương án A báo", null=True, blank=True)
    b_alert = models.BooleanField("phương án B báo", null=True, blank=True)
    needs_confirmation = models.BooleanField("cần xác nhận dữ liệu", default=False)
    model_version = models.CharField("phiên bản mô hình", max_length=40)
    is_simulation = models.BooleanField("mô phỏng", default=False, db_index=True)
    details = models.JSONField("chi tiết", default=dict)
    created_at = models.DateTimeField("tạo lúc", auto_now_add=True)

    class Meta:
        verbose_name = "kết quả dự báo"
        verbose_name_plural = "kết quả dự báo"
        ordering = ["reservoir", "-issued_at", "horizon"]
        constraints = [models.UniqueConstraint(
            fields=["reservoir", "issued_at", "horizon", "is_simulation"], name="uniq_forecast")]

    def __str__(self):
        sim = " [mô phỏng]" if self.is_simulation else ""
        return f"{self.reservoir} {localtime(self.issued_at):%d/%m/%Y %H:%M} +{self.horizon}h{sim}"


class RegulatoryThreshold(models.Model):
    """Appendix A.1/A.2 (Decision 1865/QĐ-TTg, Article 6). A range such as 377–380 is
    stored as value_low=377, value_high=380; a single value has value_low == value_high."""

    class Kind(models.TextChoices):
        MAX_BEFORE_FLOOD = "max_before_flood", "Mực nước cao nhất trước lũ"
        MIN_FLOOD_RECEPTION = "min_flood_reception", "Mực nước đón lũ thấp nhất"

    reservoir = models.ForeignKey(Reservoir, verbose_name="hồ", on_delete=models.CASCADE,
                                  related_name="thresholds")
    kind = models.CharField("loại ngưỡng", max_length=24, choices=Kind.choices)
    start_day = models.CharField("từ ngày (tháng-ngày)", max_length=5,
                                 validators=[month_day_validator])
    end_day = models.CharField("đến ngày (tháng-ngày)", max_length=5,
                               validators=[month_day_validator])
    value_low = models.FloatField("giá trị thấp (m)")
    value_high = models.FloatField("giá trị cao (m)")
    document = models.CharField("văn bản", max_length=255)
    updated_at = models.DateTimeField("cập nhật lúc", auto_now=True)

    class Meta:
        verbose_name = "ngưỡng quy định"
        verbose_name_plural = "ngưỡng quy định"
        ordering = ["reservoir", "kind", "start_day"]
        constraints = [
            models.UniqueConstraint(fields=["reservoir", "kind", "start_day"],
                                    name="uniq_threshold_period"),
            models.CheckConstraint(condition=models.Q(value_low__lte=models.F("value_high")),
                                   name="threshold_low_lte_high"),
        ]

    def __str__(self):
        return f"{self.reservoir} – {self.get_kind_display()} {self.start_day}→{self.end_day}"

    def covers(self, day):
        md = f"{day:%m-%d}"
        if self.start_day <= self.end_day:
            return self.start_day <= md <= self.end_day
        return md >= self.start_day or md <= self.end_day   # period across new year


class DirectiveQuerySet(models.QuerySet):
    def delete(self):
        raise PermissionError("Không xoá chỉ đạo điều hành; chỉ đánh dấu hết hiệu lực")


class OperatingDirective(models.Model):
    """City directive for one reservoir in one flood event (Appendix A.3). Never deleted:
    an old directive is only marked inactive, to keep the operating history (CN24)."""

    class Requirement(models.TextChoices):
        NOT_EXCEED = "not_exceed", "Không vượt"
        LOWER_TO = "lower_to", "Hạ về"

    reservoir = models.ForeignKey(Reservoir, verbose_name="hồ", on_delete=models.PROTECT,
                                  related_name="directives")
    requirement = models.CharField(
        "loại yêu cầu", max_length=12, choices=Requirement.choices, blank=True,
        help_text="Để trống chỉ khi văn bản gốc không ghi rõ (dữ liệu ví dụ Phụ lục A.4).")
    target_level = models.FloatField("mực nước mục tiêu (m)")
    starts_at = models.DateTimeField("bắt đầu", null=True, blank=True)
    deadline = models.DateTimeField("hạn hoàn thành", null=True, blank=True)
    document = models.CharField("văn bản", max_length=255,
                                help_text="Số, ngày văn bản và cơ quan ban hành")
    is_active = models.BooleanField("còn hiệu lực", default=True, db_index=True)
    entered_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="người nhập",
                                   on_delete=models.PROTECT, null=True, blank=True,
                                   related_name="+")
    created_at = models.DateTimeField("nhập lúc", auto_now_add=True)
    deactivated_at = models.DateTimeField("hết hiệu lực lúc", null=True, blank=True)
    deactivated_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="người đánh dấu",
                                       on_delete=models.PROTECT, null=True, blank=True,
                                       related_name="+")

    objects = DirectiveQuerySet.as_manager()

    class Meta:
        verbose_name = "chỉ đạo điều hành"
        verbose_name_plural = "chỉ đạo điều hành"
        ordering = ["-is_active", "-created_at", "reservoir"]

    def __str__(self):
        req = self.get_requirement_display() or "Mục tiêu"
        return f"{self.reservoir}: {req} {self.target_level} m ({self.document})"

    def delete(self, *args, **kwargs):
        raise PermissionError("Không xoá chỉ đạo điều hành; chỉ đánh dấu hết hiệu lực")


class UpdateRun(models.Model):
    """One step of one run of update_forecasts / replay_forecasts (CN27)."""

    class Kind(models.TextChoices):
        LIVE = "live", "Cập nhật hằng giờ"
        REPLAY = "replay", "Phát lại (mô phỏng)"

    class Step(models.TextChoices):
        RESERVOIR_DATA = "reservoir_data", "Dữ liệu hồ (cổng PCTT)"
        RAIN_ARCHIVE = "rain_archive", "Mưa Open-Meteo Historical"
        RAIN_FORECAST = "rain_forecast", "Mưa Open-Meteo Forecast"
        SUSPICIOUS_FLAGS = "suspicious_flags", "Đánh dấu số liệu nghi ngờ"
        FORECAST = "forecast", "Dự báo"
        ALERTS = "alerts", "Cảnh báo và thông báo"

    run_id = models.UUIDField("lần chạy", db_index=True)
    kind = models.CharField("loại", max_length=10, choices=Kind.choices, default=Kind.LIVE)
    step = models.CharField("bước", max_length=20, choices=Step.choices)
    reservoir = models.ForeignKey(Reservoir, verbose_name="hồ", on_delete=models.CASCADE,
                                  null=True, blank=True, related_name="+")
    started_at = models.DateTimeField("bắt đầu")
    finished_at = models.DateTimeField("kết thúc", null=True, blank=True)
    success = models.BooleanField("thành công", default=False)
    error = models.TextField("lỗi", blank=True)
    details = models.JSONField("chi tiết", default=dict, blank=True)

    class Meta:
        verbose_name = "lần cập nhật"
        verbose_name_plural = "lần cập nhật"
        ordering = ["-started_at", "-id"]
        indexes = [models.Index(fields=["step", "-started_at"])]

    def __str__(self):
        status = "OK" if self.success else "LỖI"
        return f"{localtime(self.started_at):%d/%m/%Y %H:%M} {self.get_step_display()} {status}"
