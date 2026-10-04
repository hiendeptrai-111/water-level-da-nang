"""Helpers: read SystemConfig values and write audit log entries."""
import logging
from decimal import Decimal

from .config_defaults import DEFAULTS
from .models import AuditLog, SystemConfig

logger = logging.getLogger(__name__)


def get_config(key):
    """Current value of a SystemConfig key (int when whole, else float)."""
    if key not in DEFAULTS:
        raise KeyError(f"Không có tham số cấu hình '{key}'")
    value = SystemConfig.objects.filter(key=key).values_list("value", flat=True).first()
    if value is None:
        logger.warning("SystemConfig thiếu khoá %s, dùng giá trị khởi tạo", key)
        value = Decimal(str(DEFAULTS[key][0]))
    return int(value) if value == value.to_integral_value() else float(value)


def client_ip(request):
    if request is None:
        return None
    return request.META.get("REMOTE_ADDR") or None


def audit(action, *, actor=None, target=None, details=None, request=None):
    """Append one entry to the system log."""
    if actor is not None and not getattr(actor, "is_authenticated", False):
        actor = None
    return AuditLog.objects.create(
        action=action,
        actor=actor,
        actor_label=str(actor) if actor else "",
        target_type=target._meta.model_name if target is not None else "",
        target_id=str(target.pk) if target is not None else "",
        target_label=str(target)[:255] if target is not None else "",
        details=details or {},
        ip_address=client_ip(request),
    )
