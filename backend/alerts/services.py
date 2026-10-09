"""Automatic alerts (CN10, section 4.3).

Each hour, after du_bao() ran for a reservoir, evaluate() compares its overall level
(du_bao()'s "muc_canh_bao_chung", never recomputed) with the previous one:
  - level rises            -> new alert + notifications;
  - "warning" lasts        -> one reminder every warning_reminder_hours forecast hours;
  - level falls            -> the open alert ends (a lower "watch" alert continues, silently);
  - same level otherwise   -> the open alert is only extended.
Admins receive watch and warning; rescue teams only warning. Web notification always, email
when the user accepts email and the run may send email (never during replays).
"""
import logging
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from core.services import get_config
from reservoirs.forecasting import LEVEL_FROM_MODEL
from reservoirs.models import LEVEL_ORDER, AlertLevel

from .models import Alert, AlertState, Notification

logger = logging.getLogger(__name__)

RECIPIENT_ROLES = {
    AlertLevel.WATCH: [User.Role.ADMIN],
    AlertLevel.WARNING: [User.Role.ADMIN, User.Role.RESCUE_TEAM],
}


def rank(level):
    return LEVEL_ORDER.index(level or AlertLevel.NORMAL)


def fmt(x, digits=2):
    return f"{x:,.{digits}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _reasons(r, horizon):
    out = []
    if r.get("baseline_bao"):
        out.append(f"Baseline (quy tắc quán tính): mực nước đã dâng hơn 0,3 m trong {horizon} giờ qua")
    if r.get("A_bao"):
        out.append(f"phương án A (hồi quy tuyến tính): dự kiến dâng {fmt(r['thay_doi_du_kien_m'])} m "
                   f"sau {horizon} giờ")
    if r.get("B_bao") and not (r.get("baseline_bao") or r.get("A_bao")):
        p = r.get("xac_suat_xgb")
        prob = f", xác suất {fmt(p * 100, 0)}%" if p is not None else ""
        out.append(f"phương án B (XGBoost{prob}): khả năng dâng hơn 0,3 m sau {horizon} giờ")
    if r.get("can_xac_nhan") and r.get("muc_canh_bao") != r.get("muc_canh_bao_tu_mo_hinh"):
        out.append("dữ liệu nghi ngờ (mức tối thiểu Theo dõi để người trực kiểm tra)")
    return out


def compose(reservoir, issued_local, result, level, *, reminder=False, simulation=False):
    """Text of an automatic alert: reservoir, horizons, expected level, reasons, suspicious data."""
    head = "[MÔ PHỎNG] " if simulation else ""
    head += "Nhắc lại: " if reminder else ""
    lines = [f"{head}{AlertLevel(level).label} – hồ {reservoir.name}, dự báo lúc "
             f"{issued_local:%H:%M %d/%m/%Y}."]
    for h in (1, 3, 6):
        r = result.get(f"{h}h") or {}
        h_level = LEVEL_FROM_MODEL.get(r.get("muc_canh_bao"))
        if rank(h_level) < rank(AlertLevel.WATCH):
            continue
        expected = (f"mực nước dự kiến {fmt(r['muc_nuoc_du_kien'])} m"
                    if r.get("muc_nuoc_du_kien") is not None else "mô hình không dự báo mực nước cho tầm này")
        why = "; ".join(_reasons(r, h)) or "—"
        lines.append(f"• Tầm {h} giờ: {expected}, mức {AlertLevel(h_level).label}. Lý do: {why}.")
    if result.get("can_xac_nhan"):
        lines.append(f"Dữ liệu nghi ngờ: CÓ – {result.get('ly_do_can_xac_nhan')}")
    else:
        lines.append("Dữ liệu nghi ngờ: không.")
    return "\n".join(lines)


def recipients(level):
    roles = RECIPIENT_ROLES.get(level, [])
    return list(User.objects.filter(role__in=roles, is_active=True))


def notify(alert, level, content, *, reminder, send_email):
    created = []
    subject = f"[Cảnh báo lũ Đà Nẵng] {content.splitlines()[0]}"[:200]
    for user in recipients(level):
        created.append(Notification.objects.create(
            recipient=user, alert=alert, channel=Notification.Channel.WEB, content=content,
            is_reminder=reminder, sent=True))
        if send_email and user.notify_email:
            note = Notification(recipient=user, alert=alert, channel=Notification.Channel.EMAIL,
                                content=content, is_reminder=reminder)
            try:
                send_mail(subject, content, settings.DEFAULT_FROM_EMAIL, [user.email])
                note.sent = True
            except Exception:                # SMTP down: keep the web notification
                logger.exception("Không gửi được email cảnh báo tới %s", user.email)
            note.save()
            created.append(note)
    return created


def _open_alert(reservoir, simulation):
    return (Alert.objects.filter(source=Alert.Source.AUTO, reservoirs=reservoir,
                                 is_simulation=simulation, ended_at__isnull=True)
            .order_by("-starts_at").first())


def _new_alert(reservoir, level, content, t, forecast, simulation):
    valid = timedelta(hours=get_config("auto_alert_valid_hours"))
    alert = Alert.objects.create(level=level, source=Alert.Source.AUTO, content=content,
                                 starts_at=t, valid_until=t + valid, forecast=forecast,
                                 is_simulation=simulation, last_notified_at=t)
    alert.reservoirs.add(reservoir)
    alert.wards.set([link.ward_id for link in reservoir.ward_links.all()])
    return alert


@transaction.atomic
def evaluate(reservoir, issued_at, result, forecast_rows, *, simulation=False, send_email=True,
             notify_users=True):
    """issued_at: aware forecast hour. Returns a short description of what happened."""
    level = LEVEL_FROM_MODEL.get(result.get("muc_canh_bao_chung"))
    state, _ = AlertState.objects.select_for_update().get_or_create(
        reservoir=reservoir, is_simulation=simulation)
    if state.evaluated_at is not None and issued_at <= state.evaluated_at:
        return "đã xét giờ này"
    if level is None:                     # du_bao() could not compute: keep the state
        state.evaluated_at = issued_at
        state.save()
        return "không đủ dữ liệu, giữ nguyên trạng thái"

    t = issued_at
    local = timezone.localtime(t)
    forecast = next((r for r in forecast_rows if r.alert_level == level), forecast_rows[0])
    valid = timedelta(hours=get_config("auto_alert_valid_hours"))
    current = _open_alert(reservoir, simulation)
    prev = state.level
    outcome = "không đổi"

    if rank(level) > rank(prev):
        if current:
            current.ended_at = t
            current.save(update_fields=["ended_at"])
        content = compose(reservoir, local, result, level, simulation=simulation)
        alert = _new_alert(reservoir, level, content, t, forecast, simulation)
        if notify_users:
            notify(alert, level, content, reminder=False, send_email=send_email and not simulation)
        outcome = f"tăng {prev} → {level}"
    elif rank(level) < rank(prev):
        if current:
            current.ended_at = t
            current.save(update_fields=["ended_at"])
        if level != AlertLevel.NORMAL:
            content = compose(reservoir, local, result, level, simulation=simulation)
            _new_alert(reservoir, level, content, t, forecast, simulation)
        outcome = f"giảm {prev} → {level}"
    elif level != AlertLevel.NORMAL:
        if current is None:               # state kept but alert missing (e.g. deleted replay)
            content = compose(reservoir, local, result, level, simulation=simulation)
            current = _new_alert(reservoir, level, content, t, forecast, simulation)
        current.valid_until = t + valid
        current.forecast = forecast
        reminder_every = timedelta(hours=get_config("warning_reminder_hours"))
        if (level == AlertLevel.WARNING and current.last_notified_at is not None
                and t - current.last_notified_at >= reminder_every):
            content = compose(reservoir, local, result, level, reminder=True, simulation=simulation)
            if notify_users:
                notify(current, level, content, reminder=True,
                       send_email=send_email and not simulation)
            current.last_notified_at = t
            outcome = "nhắc lại"
        current.save(update_fields=["valid_until", "forecast", "last_notified_at"])

    state.level = level
    state.evaluated_at = t
    state.save()
    return outcome
