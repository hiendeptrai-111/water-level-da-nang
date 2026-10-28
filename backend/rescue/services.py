"""SOS life cycle (CN15–CN19), flood points (CN20–CN21) and team suggestions (CN18)."""
import json
import logging
from datetime import timedelta
from decimal import Decimal
from functools import lru_cache

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from accounts.models import User
from alerts.models import Alert, Notification
from catalog import geo
from catalog.models import RescueTeam, Ward
from core.services import get_config
from reservoirs.models import LEVEL_ORDER

from . import routing
from .models import SOS, FloodPoint, SOSHistory

logger = logging.getLogger(__name__)


class SOSConflict(Exception):
    """Someone else already took the action (receive / claim): HTTP 409."""


# ---------------------------------------------------------------- ward from coordinates
@lru_cache(maxsize=1)
def _ward_shapes():
    data = json.loads((settings.BASE_DIR / "data" / "ward_boundaries.geojson").read_text(encoding="utf-8"))
    return [((f["properties"]["kind"], f["properties"]["name"]), f["geometry"]) for f in data["features"]]


def ward_for_point(lat, lon):
    """The commune whose (OpenStreetMap) boundary contains the point, or None."""
    for key, geometry in _ward_shapes():
        if geo.contains(geometry, float(lat), float(lon)):
            return Ward.objects.filter(kind=key[0], name=key[1]).first()
    return None


# ---------------------------------------------------------------- priority (assumption)
# Priority score — ASSUMPTION of the project, documented in README:
WATER_POINTS = {"": 0, "knee": 10, "chest": 30, "first_floor": 45, "roof": 70}
VULNERABLE_POINTS, VULNERABLE_MAX = 10, 30
PEOPLE_POINTS = {"": 0, "1": 0, "2-4": 5, "5+": 10}
WAIT_POINTS_PER_MINUTES, WAIT_MAX = 3, 20          # 1 point per 3 minutes waited, at most 20
AREA_ALERT_POINTS = {None: 0, "normal": 0, "watch": 5, "warning": 15, "emergency": 25}
PRIORITY_BANDS = [(60, "very_high", "Rất cao"), (40, "high", "Cao"), (20, "medium", "Trung bình"),
                  (0, "low", "Thấp")]


def area_alert_level(ward, now=None):
    """Highest live (non-simulated) alert in force covering the commune."""
    if ward is None:
        return None
    now = now or timezone.now()
    levels = (Alert.objects.filter(is_simulation=False, wards=ward, starts_at__lte=now, valid_until__gt=now)
              .filter(Q(ended_at__isnull=True) | Q(ended_at__gt=now)).values_list("level", flat=True))
    return max(levels, key=LEVEL_ORDER.index, default=None)


def priority_score(sos, now=None):
    now = now or timezone.now()
    waited = max(0.0, (now - sos.created_at).total_seconds() / 60) if sos.created_at else 0.0
    score = (WATER_POINTS.get(sos.water_level or "", 0)
             + min(len(set(sos.vulnerable_groups or [])) * VULNERABLE_POINTS, VULNERABLE_MAX)
             + PEOPLE_POINTS.get(sos.people_count or "", 0)
             + min(waited / WAIT_POINTS_PER_MINUTES, WAIT_MAX)
             + AREA_ALERT_POINTS.get(area_alert_level(sos.ward, now), 0))
    return round(score, 1)


def priority_band(score):
    for minimum, key, label in PRIORITY_BANDS:
        if score >= minimum:
            return key, label
    return PRIORITY_BANDS[-1][1:]


def refresh_priority(sos, now=None, save=True):
    sos.priority_score = priority_score(sos, now)
    if save:
        SOS.objects.filter(pk=sos.pk).update(priority_score=sos.priority_score)
    return sos.priority_score


# ---------------------------------------------------------------- status changes
def record(sos, to_status, actor=None, note="", from_status=None):
    """actor: a user, or a short text such as "người gửi" for anonymous senders."""
    user = actor if getattr(actor, "is_authenticated", False) else None
    label = str(actor) if user else (actor if isinstance(actor, str) else "")
    SOSHistory.objects.create(
        sos=sos, from_status=sos.status if from_status is None else from_status, to_status=to_status,
        actor=user, actor_label=label[:255], note=note[:300])


def change_status(sos, to_status, actor=None, note=""):
    """The only way a status changes: always one SOSHistory row."""
    record(sos, to_status, actor, note)
    sos.status = to_status
    if to_status in SOS.FINISHED and sos.finished_at is None:
        sos.finished_at = timezone.now()
    sos.save()
    return sos


def open_sos_for(user=None, phone=""):
    q = Q()
    if user is not None and user.is_authenticated:
        q |= Q(sender=user)
    if phone:
        q |= Q(phone=phone)
    if not q:
        return None
    return SOS.objects.select_for_update().filter(q, status__in=SOS.OPEN).order_by("-created_at").first()


@transaction.atomic
def submit(*, user, phone, latitude, longitude, accuracy_m=None, location_source="gps", device_id="",
           ip=None, extra=None):
    """CN15: create an SOS, or update the one still open for this account / phone number.
    Never depends on routing (works even when the road graph is missing)."""
    existing = open_sos_for(user, phone)
    if existing:
        sos, created = existing, False
        sos.latitude, sos.longitude = latitude, longitude
        sos.accuracy_m, sos.location_source = accuracy_m, location_source
        record(sos, sos.status, user if user and user.is_authenticated else "", "Gửi lại: cập nhật vị trí")
    else:
        created = True
        sos = SOS(sender=user if user and user.is_authenticated else None, phone=phone,
                  latitude=latitude, longitude=longitude, accuracy_m=accuracy_m,
                  location_source=location_source)
    sos.device_id, sos.ip_address = device_id[:64], ip
    sos.ward = ward_for_point(latitude, longitude)
    for field, value in (extra or {}).items():
        setattr(sos, field, value)
    sos.save()
    if created:
        record(sos, SOS.Status.NEW, user if user and user.is_authenticated else "người gửi", "Gửi SOS",
               from_status="")
    refresh_priority(sos)
    return sos, created


def supplement(sos, data, actor=None):
    """CN15/CN16: extra information sent after the location; optional new location."""
    for field in ("people_count", "vulnerable_groups", "water_level", "note", "accuracy_m"):
        if field in data:
            setattr(sos, field, data[field])
    if "latitude" in data and "longitude" in data:
        sos.latitude, sos.longitude = data["latitude"], data["longitude"]
        sos.ward = ward_for_point(sos.latitude, sos.longitude)
    sos.save()
    refresh_priority(sos)
    return sos


@transaction.atomic
def cancel(sos, actor=None, note="Người gửi huỷ: đã an toàn"):
    sos = SOS.objects.select_for_update().get(pk=sos.pk)
    if not sos.is_open:
        raise SOSConflict("SOS này đã kết thúc.")
    team = sos.team
    change_status(sos, SOS.Status.CANCELLED, actor, note)
    if team:
        _free_team(team)
    return sos


# ---------------------------------------------------------------- admin (CN17, CN18)
@transaction.atomic
def receive(sos_id, admin):
    """'Tiếp nhận' with a row lock: two admins cannot take the same SOS."""
    sos = SOS.objects.select_for_update().get(pk=sos_id)
    if sos.handled_by_id and sos.handled_by_id != admin.pk:
        raise SOSConflict(f"SOS đã được {sos.handled_by} tiếp nhận.")
    if sos.status != SOS.Status.NEW and sos.handled_by_id == admin.pk:
        return sos
    if sos.status != SOS.Status.NEW:
        raise SOSConflict("SOS không còn ở trạng thái Mới gửi.")
    sos.handled_by = admin
    return change_status(sos, SOS.Status.RECEIVED, admin, "Admin tiếp nhận")


def _team_busy(team):
    RescueTeam.objects.filter(pk=team.pk).update(status=RescueTeam.Status.BUSY)


def _free_team(team):
    if not SOS.objects.filter(team=team, status=SOS.Status.MOVING).exists():
        RescueTeam.objects.filter(pk=team.pk, status=RescueTeam.Status.BUSY).update(
            status=RescueTeam.Status.AVAILABLE)


def _set_route(sos, team):
    """ETA + route of the team (best effort: a routing error never blocks the assignment)."""
    try:
        best = {r.team_id: r for r in suggest(sos, teams=[team], limit=1)}
        r = best.get(team.pk)
        if r and r.seconds is not None:
            sos.eta_seconds, sos.route, sos.route_mode = r.seconds, r.path or [], r.mode
    except Exception:
        logger.exception("Không tính được tuyến đường cho SOS %s", sos.code)


@transaction.atomic
def assign(sos_id, team_id, admin):
    """'Phân công' (CN18): admin only, never automatic. Moves the SOS to 'Đang di chuyển'."""
    sos = SOS.objects.select_for_update().get(pk=sos_id)
    team = RescueTeam.objects.select_for_update().get(pk=team_id)
    if not sos.is_open:
        raise SOSConflict("SOS này đã kết thúc.")
    previous = sos.team
    if sos.status == SOS.Status.NEW:
        sos.handled_by = sos.handled_by or admin
        change_status(sos, SOS.Status.RECEIVED, admin, "Admin tiếp nhận khi phân công")
    sos.team = team
    _set_route(sos, team)
    change_status(sos, SOS.Status.MOVING, admin,
                  f"Phân công {team}" + (f" (chuyển từ {previous})" if previous and previous != team else ""))
    _team_busy(team)
    if previous and previous != team:
        _free_team(previous)
    notify_team(team, sos, f"Nhiệm vụ mới: SOS {sos.code}. Mở trang Nhiệm vụ để xem vị trí và tuyến đường.")
    return sos


@transaction.atomic
def merge(sos_id, into_id, admin):
    """Duplicate SOS: closed and linked to the SOS that is kept."""
    if sos_id == into_id:
        raise SOSConflict("Không gộp một SOS vào chính nó.")
    sos = SOS.objects.select_for_update().get(pk=sos_id)
    target = SOS.objects.get(pk=into_id)
    sos.merged_into = target
    change_status(sos, SOS.Status.CLOSED, admin, f"Trùng lặp, gộp vào SOS {target.code}")
    if sos.team and sos.team != target.team:
        team = sos.team
        sos.team = None
        sos.save(update_fields=["team"])
        _free_team(team)
    return sos


@transaction.atomic
def close(sos_id, admin, note="Admin đóng SOS"):
    sos = SOS.objects.select_for_update().get(pk=sos_id)
    if sos.status in SOS.FINISHED:
        raise SOSConflict("SOS đã đóng.")
    team = sos.team
    change_status(sos, SOS.Status.CLOSED, admin, note)
    if team:
        _free_team(team)
    return sos


# ---------------------------------------------------------------- rescue team (CN19)
def claim_wait():
    return timedelta(minutes=get_config("sos_self_claim_wait_minutes"))


def claimable_qs(now=None):
    """Unassigned open SOS waiting longer than the self-claim delay."""
    now = now or timezone.now()
    return SOS.objects.filter(status__in=[SOS.Status.NEW, SOS.Status.RECEIVED], team__isnull=True,
                              merged_into__isnull=True, created_at__lte=now - claim_wait())


@transaction.atomic
def claim(sos_id, team, actor):
    """'Nhận' with row locks on the SOS and the team: only one team can win."""
    team = RescueTeam.objects.select_for_update().get(pk=team.pk)
    sos = SOS.objects.select_for_update().get(pk=sos_id)
    if team.status != RescueTeam.Status.AVAILABLE:
        raise SOSConflict("Đội chỉ nhận thêm SOS khi đang ở trạng thái Rảnh.")
    if sos.team_id is not None or sos.status not in (SOS.Status.NEW, SOS.Status.RECEIVED):
        raise SOSConflict("SOS này đã có đội nhận.")
    if sos.created_at > timezone.now() - claim_wait():
        raise SOSConflict("SOS chưa quá thời gian chờ admin phân công.")
    sos.team = team
    _set_route(sos, team)
    change_status(sos, SOS.Status.MOVING, actor, f"{team} tự nhận")
    _team_busy(team)
    return sos


@transaction.atomic
def team_update(sos_id, team, actor, action, note=""):
    """arrived (event only) / rescued / unreachable / return (back to the queue, with a reason)."""
    sos = SOS.objects.select_for_update().get(pk=sos_id, team=team)
    if sos.status != SOS.Status.MOVING:
        raise SOSConflict("Nhiệm vụ không còn ở trạng thái Đang di chuyển.")
    if action == "arrived":
        sos.arrived_at = timezone.now()
        sos.save(update_fields=["arrived_at"])
        record(sos, sos.status, actor, "Đội đã đến nơi")
        return sos
    if action == "return":
        if not note.strip():
            raise SOSConflict("Cần ghi lý do trả lại nhiệm vụ.")
        sos.team = None
        sos.eta_seconds, sos.route, sos.route_mode = None, [], ""
        sos.claim_notified_at = None
        change_status(sos, SOS.Status.RECEIVED, actor, f"Trả lại nhiệm vụ: {note}")
    elif action in ("rescued", "unreachable"):
        change_status(sos, action, actor, note or dict(SOS.Status.choices)[action])
    else:
        raise SOSConflict("Thao tác không hợp lệ.")
    _free_team(team)
    return sos


def team_position(team, now=None):
    """(lat, lon) used for routing: recent current position, otherwise the base."""
    now = now or timezone.now()
    max_age = timedelta(minutes=get_config("team_location_max_age_minutes"))
    if team.current_latitude is not None and team.location_updated_at and now - team.location_updated_at <= max_age:
        return float(team.current_latitude), float(team.current_longitude)
    if team.base_latitude is not None:
        return float(team.base_latitude), float(team.base_longitude)
    return None


# ---------------------------------------------------------------- suggestions (CN18)
def active_floods(now=None):
    now = now or timezone.now()
    return list(FloodPoint.objects.filter(status=FloodPoint.Status.APPROVED, expires_at__gt=now,
                                          merged_into__isnull=True))


def suggest(sos, teams=None, limit=3):
    """Best teams by travel time. Road teams: Dijkstra on the road graph with APPROVED flood
    points applied; boat teams: straight line / boat speed. Raises if the road graph is missing."""
    teams = list(teams if teams is not None else RescueTeam.objects.filter(status=RescueTeam.Status.AVAILABLE))
    target = (float(sos.latitude), float(sos.longitude))
    starts = {t.pk: team_position(t) for t in teams}
    results = []
    road = {t.pk: starts[t.pk] for t in teams if starts[t.pk] and t.has_road_vehicle}
    times = {}
    if road:
        rg = routing.load_graph()
        floods = [routing.Flood(float(f.latitude), float(f.longitude), f.level) for f in active_floods()]
        effects = routing.flood_effects(rg, floods, get_config("flood_point_radius_m"),
                                        float(get_config("flood_slowdown_factor")))
        times = routing.road_times(rg, target, road, effects)
    boat_kmh = get_config("boat_speed_kmh")
    for t in teams:
        start = starts[t.pk]
        if start is None:
            results.append(routing.Route(t.pk, "none", None, None, "Đội chưa có vị trí hoặc căn cứ"))
            continue
        options = []
        if t.pk in times and times[t.pk][0] is not None:
            options.append(routing.Route(t.pk, "road", times[t.pk][0], times[t.pk][1]))
        if t.has_boat:
            options.append(routing.Route(t.pk, "boat", routing.boat_time(start, target, boat_kmh),
                                         [list(start), list(target)],
                                         "Ca nô: tính theo đường thẳng (giả định đơn giản)"))
        if options:
            results.append(min(options, key=lambda r: r.seconds))
        else:
            results.append(routing.Route(t.pk, "none", None, None, "Không tiếp cận được bằng đường bộ"))
    results.sort(key=lambda r: (r.seconds is None, r.seconds or 0))
    return results[:limit] if limit else results


# ---------------------------------------------------------------- notifications
def notify_team(team, sos, content, email=True):
    for user in User.objects.filter(rescue_team=team, is_active=True):
        Notification.objects.create(recipient=user, sos=sos, channel=Notification.Channel.WEB,
                                    content=content, sent=True)
        if email and user.notify_email:
            note = Notification(recipient=user, sos=sos, channel=Notification.Channel.EMAIL, content=content)
            try:
                send_mail(f"[Cứu hộ Đà Nẵng] {content[:80]}", content, settings.DEFAULT_FROM_EMAIL, [user.email])
                note.sent = True
            except Exception:
                logger.exception("Không gửi được email tới %s", user.email)
            note.save()


def notify_claimable(now=None):
    """SOS waiting longer than the self-claim delay: tell the nearest available teams (once)."""
    now = now or timezone.now()
    count = get_config("claim_notify_teams")
    done = []
    for sos in claimable_qs(now).filter(claim_notified_at__isnull=True):
        target = (float(sos.latitude), float(sos.longitude))
        teams = [(routing.haversine_m(*target, *pos), t) for t in RescueTeam.objects.filter(
            status=RescueTeam.Status.AVAILABLE) if (pos := team_position(t, now))]
        for _d, team in sorted(teams, key=lambda x: x[0])[:count]:
            notify_team(team, sos, f"SOS {sos.code} đã chờ hơn {get_config('sos_self_claim_wait_minutes')} phút "
                                   "chưa được phân công. Mở trang Nhiệm vụ để nhận.")
        SOS.objects.filter(pk=sos.pk).update(claim_notified_at=now)
        done.append(sos.code)
    return done


# ---------------------------------------------------------------- flood points (CN20, CN21)
def report_flood(user, latitude, longitude, level, photo=None):
    """Resident -> pending; rescue team / admin -> approved at once."""
    now = timezone.now()
    trusted = user.role in (User.Role.RESCUE_TEAM, User.Role.ADMIN)
    point = FloodPoint.objects.create(
        latitude=latitude, longitude=longitude, level=level, reporter=user, photo=photo or "",
        status=FloodPoint.Status.APPROVED if trusted else FloodPoint.Status.PENDING,
        approved_by=user if trusted else None, approved_at=now if trusted else None,
        expires_at=now + timedelta(hours=get_config("flood_point_ttl_hours")))
    return point


def expire_floods(now=None):
    now = now or timezone.now()
    return FloodPoint.objects.filter(status__in=[FloodPoint.Status.PENDING, FloodPoint.Status.APPROVED],
                                     expires_at__lte=now).update(status=FloodPoint.Status.EXPIRED)


# ---------------------------------------------------------------- anonymisation
def anonymize(now=None):
    """Finished SOS older than sos_anonymize_days: drop phone, photo, note, sender, device, IP
    and route; exact position -> centre of its commune. Times, commune, status, handling times,
    people count, groups and water level are kept for statistics."""
    now = now or timezone.now()
    days = get_config("sos_anonymize_days")
    done = 0
    for sos in SOS.objects.filter(status__in=SOS.FINISHED, finished_at__lte=now - timedelta(days=days),
                                  anonymized_at__isnull=True):
        if sos.photo:
            sos.photo.delete(save=False)
        ward = sos.ward
        if ward and ward.latitude is not None:
            sos.latitude, sos.longitude = ward.latitude, ward.longitude
        else:                                     # no commune centre: about 1 km precision
            sos.latitude = Decimal(sos.latitude).quantize(Decimal("0.01"))
            sos.longitude = Decimal(sos.longitude).quantize(Decimal("0.01"))
        sos.phone = sos.note = sos.device_id = ""
        sos.photo = ""
        sos.sender = None
        sos.ip_address = None
        sos.route, sos.accuracy_m = [], None
        sos.anonymized_at = now
        sos.save()
        done += 1
    return done
