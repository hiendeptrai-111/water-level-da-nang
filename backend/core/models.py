from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from .config_defaults import DEFAULTS


class SystemConfig(models.Model):
    """Tunable parameters (one row per key). Edited by admins, never hard-coded."""

    key = models.CharField("khoá", max_length=64, unique=True,
                           choices=[(k, k) for k in DEFAULTS])
    value = models.DecimalField("giá trị", max_digits=12, decimal_places=3)
    unit = models.CharField("đơn vị", max_length=20, blank=True)
    description = models.CharField("mô tả", max_length=255, blank=True)
    updated_at = models.DateTimeField("cập nhật lúc", auto_now=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="người cập nhật",
                                   on_delete=models.SET_NULL, null=True, blank=True, related_name="+")

    class Meta:
        verbose_name = "tham số cấu hình"
        verbose_name_plural = "cấu hình hệ thống"
        ordering = ["key"]

    def __str__(self):
        return f"{self.key} = {self.value} {self.unit}".strip()

    def clean(self):
        default = DEFAULTS.get(self.key)
        if default and self.value is not None and self.value < default[2]:
            raise ValidationError({"value": f"Giá trị phải ≥ {default[2]}"})


class AuditLogQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise PermissionError("Nhật ký hệ thống chỉ được thêm, không được sửa")

    def delete(self):
        raise PermissionError("Nhật ký hệ thống chỉ được thêm, không được xoá")


class AuditLog(models.Model):
    """Append-only system log (CN28). Also protected by a database trigger
    (migration 0003): UPDATE and DELETE on this table always fail."""

    class Action(models.TextChoices):
        LOGIN = "login", "Đăng nhập"
        USER_CREATED = "user_created", "Tạo tài khoản"
        USER_UPDATED = "user_updated", "Sửa tài khoản"
        USER_LOCKED = "user_locked", "Khoá tài khoản"
        USER_UNLOCKED = "user_unlocked", "Mở khoá tài khoản"
        ROLE_CHANGED = "role_changed", "Đổi vai trò"
        PASSWORD_RESET_BY_ADMIN = "password_reset_by_admin", "Admin đặt lại mật khẩu"
        CONFIG_CHANGED = "config_changed", "Sửa cấu hình"
        THRESHOLD_CHANGED = "threshold_changed", "Sửa ngưỡng quy định"
        DIRECTIVE_CREATED = "directive_created", "Thêm chỉ đạo điều hành"
        DIRECTIVE_DEACTIVATED = "directive_deactivated", "Đánh dấu chỉ đạo hết hiệu lực"

    created_at = models.DateTimeField("thời điểm", auto_now_add=True, db_index=True)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="người thực hiện",
                              on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    actor_label = models.CharField("người thực hiện (lúc ghi)", max_length=255, blank=True)
    action = models.CharField("thao tác", max_length=40, choices=Action.choices, db_index=True)
    target_type = models.CharField("loại đối tượng", max_length=50, blank=True)
    target_id = models.CharField("mã đối tượng", max_length=64, blank=True)
    target_label = models.CharField("đối tượng", max_length=255, blank=True)
    details = models.JSONField("chi tiết", default=dict, blank=True)
    ip_address = models.GenericIPAddressField("địa chỉ IP", null=True, blank=True)

    objects = AuditLogQuerySet.as_manager()

    class Meta:
        verbose_name = "nhật ký"
        verbose_name_plural = "nhật ký hệ thống"
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.created_at:%d/%m/%Y %H:%M} {self.actor_label} {self.get_action_display()}"

    def save(self, *args, **kwargs):
        if self.pk is not None or not self._state.adding:
            raise PermissionError("Nhật ký hệ thống chỉ được thêm, không được sửa")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionError("Nhật ký hệ thống chỉ được thêm, không được xoá")
