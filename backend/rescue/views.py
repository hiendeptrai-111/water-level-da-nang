import logging
from datetime import timedelta

from django.db import transaction
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle
from rest_framework.views import APIView

from accounts.models import User
from accounts.permissions import IsAdminRole, IsRescueTeam
from catalog.models import RescueTeam
from core.services import client_ip, get_config
from reservoirs.views import local

from . import services
from .models import SOS, FloodPoint
from .serializers import (FloodPointAdminSerializer, FloodPointPublicSerializer, FloodReportSerializer,
                          SOSClaimableSerializer, SOSCreateSerializer, SOSDispatchSerializer,
                          SOSSupplementSerializer, SOSTaskSerializer, SOSTrackSerializer, TeamSerializer,
                          validate_photo)

logger = logging.getLogger(__name__)


def conflict(e):
    return Response({"detail": str(e), "code": "conflict"}, status=status.HTTP_409_CONFLICT)


# ---------------------------------------------------------------- rate limits (sos_rate_limit_per_hour)
class _SOSThrottle(SimpleRateThrottle):
    def get_rate(self):
        return f"{get_config('sos_rate_limit_per_hour')}/hour"


class SOSIPThrottle(_SOSThrottle):
    scope = "sos_ip"

    def get_cache_key(self, request, view):
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}


class SOSDeviceThrottle(_SOSThrottle):
    scope = "sos_device"

    def get_cache_key(self, request, view):
        device = (request.data.get("device_id") or request.headers.get("X-Device-Id") or "").strip()
        return self.cache_format % {"scope": self.scope, "ident": device[:64]} if device else None


# ---------------------------------------------------------------- sender (CN15, CN16)
def sender_access(request, code):
    """The SOS of the logged-in sender, or of an anonymous sender who gives code + phone."""
    sos = get_object_or_404(SOS.objects.select_related("team", "ward"), code=code.upper())
    user = request.user
    if user.is_authenticated and sos.sender_id == user.pk:
        return sos
    phone = (request.data.get("phone") if request.method != "GET" else None) or request.query_params.get("phone")
    if phone and sos.phone and phone.strip() == sos.phone:
        return sos
    raise Http404


class SOSCreateView(APIView):
    """POST /api/sos/: no login needed (then the phone number is required). Location + phone
    first; other details come with PATCH /api/sos/<code>/."""
    permission_classes = [AllowAny]
    throttle_classes = [SOSIPThrottle, SOSDeviceThrottle]

    def post(self, request):
        user = request.user if request.user.is_authenticated else None
        if user and user.role != User.Role.CITIZEN:
            raise PermissionDenied("Đội cứu hộ và admin không gửi SOS từ tài khoản này.")
        s = SOSCreateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        phone = d.get("phone") or (user.phone_number if user else "")
        if not phone:
            raise serializers.ValidationError({"phone": "Cần số điện thoại để đội cứu hộ liên lạc."})
        sos, created = services.submit(
            user=user, phone=phone, latitude=d["latitude"], longitude=d["longitude"],
            accuracy_m=d.get("accuracy_m"), location_source=d["location_source"],
            device_id=d.get("device_id", ""), ip=client_ip(request))
        data = SOSTrackSerializer(sos).data
        data["created"] = created
        return Response(local(data), status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class SOSDetailView(APIView):
    """GET (track), PATCH (extra details / new location) for the sender."""
    permission_classes = [AllowAny]

    def get(self, request, code):
        return Response(local(SOSTrackSerializer(sender_access(request, code)).data))

    def patch(self, request, code):
        sos = sender_access(request, code)
        if not sos.is_open:
            return conflict(services.SOSConflict("SOS này đã kết thúc."))
        s = SOSSupplementSerializer(data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        services.supplement(sos, s.validated_data, request.user)
        return Response(local(SOSTrackSerializer(sos).data))


class SOSCancelView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, code):
        sos = sender_access(request, code)
        try:
            sos = services.cancel(sos, request.user if request.user.is_authenticated else "người gửi",
                                  request.data.get("note") or "Người gửi huỷ: đã an toàn")
        except services.SOSConflict as e:
            return conflict(e)
        return Response(local(SOSTrackSerializer(sos).data))


class SOSPhotoUploadView(APIView):
    """One photo per SOS (compressed by the browser; size and type checked here)."""
    permission_classes = [AllowAny]

    def post(self, request, code):
        sos = sender_access(request, code)
        f = request.FILES.get("photo")
        if not f:
            raise serializers.ValidationError({"photo": "Chưa có ảnh."})
        validate_photo(f)
        if sos.photo:
            sos.photo.delete(save=False)
        sos.photo.save(f"{sos.code}{f.name[f.name.rfind('.'):] if '.' in f.name else '.jpg'}", f, save=True)
        return Response({"has_photo": True})


class MySOSView(APIView):
    """GET /api/sos/mine/: the logged-in resident's SOS (open first)."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = SOS.objects.filter(sender=request.user).select_related("team", "ward").prefetch_related("history")
        items = sorted(qs, key=lambda s: (not s.is_open, -s.created_at.timestamp()))
        return Response(local(SOSTrackSerializer(items, many=True).data))


# ---------------------------------------------------------------- photos (admin, assigned team)
class SOSPhotoView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        sos = get_object_or_404(SOS, pk=pk)
        user = request.user
        allowed = user.role == User.Role.ADMIN or (
            user.role == User.Role.RESCUE_TEAM and sos.team_id and sos.team_id == user.rescue_team_id)
        if not allowed or not sos.photo:
            raise Http404
        return FileResponse(sos.photo.open("rb"))


# ---------------------------------------------------------------- dispatch, admin only (CN17, CN18)
class DispatchListView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        p = request.query_params
        qs = SOS.objects.select_related("team", "ward", "handled_by", "sender", "merged_into")
        if p.get("status"):
            qs = qs.filter(status__in=p["status"].split(","))
        else:   # default: open SOS + those finished in the last 24 h
            qs = qs.filter(status__in=SOS.OPEN) | qs.filter(finished_at__gte=timezone.now() - timedelta(hours=24)) \
                | qs.filter(status__in=[SOS.Status.RESCUED, SOS.Status.UNREACHABLE])
        if p.get("ward"):
            qs = qs.filter(ward_id=p["ward"])
        items = list(qs.distinct())
        for s in items:
            if s.is_open:
                services.refresh_priority(s)
        items.sort(key=lambda s: (not s.is_open, -s.priority_score, s.created_at))
        teams = RescueTeam.objects.all()
        floods = services.active_floods()
        return Response(local({
            "refresh_seconds": get_config("dispatch_refresh_seconds"),
            "sos": SOSDispatchSerializer(items, many=True).data,
            "teams": TeamSerializer(teams, many=True).data,
            "flood_points": FloodPointPublicSerializer(floods, many=True).data,
        }))


class DispatchDetailView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request, pk):
        sos = get_object_or_404(SOS.objects.select_related("team", "ward", "handled_by", "sender"), pk=pk)
        data = SOSDispatchSerializer(sos).data
        data["history"] = [{"from": h.from_status, "to": h.to_status, "to_label": SOS.Status(h.to_status).label,
                            "actor": h.actor_label, "note": h.note, "time": h.time} for h in sos.history.all()]
        return Response(local(data))


class DispatchActionView(APIView):
    """POST /api/dispatch/sos/<id>/<action>/: receive, assign {team}, merge {into}, close."""
    permission_classes = [IsAdminRole]

    def post(self, request, pk, action):
        get_object_or_404(SOS, pk=pk)
        try:
            if action == "receive":
                sos = services.receive(pk, request.user)
            elif action == "assign":
                team = get_object_or_404(RescueTeam, pk=request.data.get("team"))
                sos = services.assign(pk, team.pk, request.user)
            elif action == "merge":
                into = get_object_or_404(SOS, code=str(request.data.get("into", "")).upper())
                sos = services.merge(pk, into.pk, request.user)
            elif action == "close":
                sos = services.close(pk, request.user, request.data.get("note") or "Admin đóng SOS")
            else:
                raise Http404
        except services.SOSConflict as e:
            return conflict(e)
        return Response(local(SOSDispatchSerializer(sos).data))


def route_dict(r, teams):
    t = teams.get(r.team_id)
    return {"team": TeamSerializer(t).data if t else None, "mode": r.mode, "seconds": r.seconds,
            "minutes": round(r.seconds / 60) if r.seconds is not None else None, "path": r.path, "note": r.note}


class DispatchSuggestView(APIView):
    """GET: the 3 best available teams with travel time and route. Suggestion only."""
    permission_classes = [IsAdminRole]

    def get(self, request, pk):
        sos = get_object_or_404(SOS, pk=pk)
        teams = {t.pk: t for t in RescueTeam.objects.filter(status=RescueTeam.Status.AVAILABLE)}
        try:
            routes = services.suggest(sos, teams=teams.values(), limit=3)
        except Exception as e:             # missing graph, etc.: the dispatch screen keeps working
            logger.exception("Gợi ý đội cho SOS %s lỗi", sos.code)
            return Response({"suggestions": [], "error": f"Không tính được tuyến đường: {e}"})
        return Response(local({"suggestions": [route_dict(r, teams) for r in routes]}))


# ---------------------------------------------------------------- rescue team (CN19)
def my_team(request):
    team = request.user.rescue_team
    if team is None:
        raise PermissionDenied("Tài khoản chưa được gắn với đội cứu hộ.")
    return team


class TeamTasksView(APIView):
    permission_classes = [IsRescueTeam]

    def get(self, request):
        team = my_team(request)
        assigned = SOS.objects.filter(team=team, status=SOS.Status.MOVING).select_related("ward")
        recent = SOS.objects.filter(team=team, status__in=[SOS.Status.RESCUED, SOS.Status.UNREACHABLE],
                                    updated_at__gte=timezone.now() - timedelta(hours=12))
        claimable = list(services.claimable_qs().select_related("ward"))
        pos = services.team_position(team)
        if pos:   # nearest first; travel time for the 10 nearest
            from .routing import haversine_m
            claimable.sort(key=lambda s: haversine_m(*pos, float(s.latitude), float(s.longitude)))
        items = []
        for i, s in enumerate(claimable):
            services.refresh_priority(s)
            row = SOSClaimableSerializer(s).data
            row["eta_seconds"] = None
            if i < 10 and pos:
                try:
                    r = services.suggest(s, teams=[team], limit=1)[0]
                    row["eta_seconds"], row["route_mode"] = r.seconds, r.mode
                except Exception:
                    logger.exception("ETA lỗi cho SOS %s", s.code)
            items.append(row)
        return Response(local({
            "team": TeamSerializer(team).data,
            "refresh_seconds": get_config("dispatch_refresh_seconds"),
            "claim_wait_minutes": get_config("sos_self_claim_wait_minutes"),
            "assigned": SOSTaskSerializer(assigned, many=True).data,
            "recent": SOSTaskSerializer(recent, many=True).data,
            "claimable": items,
        }))


class TeamTaskActionView(APIView):
    """POST /api/rescue/tasks/<id>/<action>/: claim, arrived, rescued, unreachable, return {note}."""
    permission_classes = [IsRescueTeam]

    def post(self, request, pk, action):
        team = my_team(request)
        get_object_or_404(SOS, pk=pk)
        try:
            if action == "claim":
                sos = services.claim(pk, team, request.user)
            elif action in ("arrived", "rescued", "unreachable", "return"):
                sos = services.team_update(pk, team, request.user, action, request.data.get("note", ""))
            else:
                raise Http404
        except SOS.DoesNotExist as e:
            raise Http404 from e
        except services.SOSConflict as e:
            return conflict(e)
        return Response(local(SOSTaskSerializer(sos).data))


class TeamLocationView(APIView):
    permission_classes = [IsRescueTeam]

    def post(self, request):
        team = my_team(request)
        from .serializers import LocationSerializer
        s = LocationSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        RescueTeam.objects.filter(pk=team.pk).update(
            current_latitude=s.validated_data["latitude"], current_longitude=s.validated_data["longitude"],
            location_updated_at=timezone.now())
        return Response({"ok": True})


class TeamStatusView(APIView):
    permission_classes = [IsRescueTeam]

    def post(self, request):
        team = my_team(request)
        value = request.data.get("status")
        if value not in RescueTeam.Status.values:
            raise serializers.ValidationError({"status": "Trạng thái không hợp lệ."})
        if value == RescueTeam.Status.AVAILABLE and SOS.objects.filter(team=team, status=SOS.Status.MOVING).exists():
            return conflict(services.SOSConflict("Đội đang có nhiệm vụ chưa xong."))
        RescueTeam.objects.filter(pk=team.pk).update(status=value)
        team.refresh_from_db()
        return Response(TeamSerializer(team).data)


# ---------------------------------------------------------------- flood points (CN20, CN21)
class FloodPointsView(APIView):
    """GET (public): approved points, without the reporter. POST (logged in): report."""

    def get_permissions(self):
        return [AllowAny()] if self.request.method == "GET" else [IsAuthenticated()]

    def get(self, request):
        return Response(local(FloodPointPublicSerializer(services.active_floods(), many=True).data))

    def post(self, request):
        s = FloodReportSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        point = services.report_flood(request.user, d["latitude"], d["longitude"], d["level"], d.get("photo"))
        return Response(local({**FloodPointPublicSerializer(point).data, "status": point.status,
                               "status_label": point.get_status_display()}), status=status.HTTP_201_CREATED)


class FloodConfirmView(APIView):
    """A team or an admin confirms a point is still flooded: expiry pushed back."""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if request.user.role not in (User.Role.RESCUE_TEAM, User.Role.ADMIN):
            raise PermissionDenied()
        now = timezone.now()
        n = FloodPoint.objects.filter(pk=pk, status=FloodPoint.Status.APPROVED).update(
            confirmed_at=now, expires_at=now + timedelta(hours=get_config("flood_point_ttl_hours")))
        if not n:
            raise Http404
        return Response({"ok": True})


class AdminFloodListView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        services.expire_floods()
        qs = FloodPoint.objects.select_related("reporter", "approved_by")
        if request.query_params.get("status"):
            qs = qs.filter(status=request.query_params["status"])
        else:
            qs = qs.filter(status__in=[FloodPoint.Status.PENDING, FloodPoint.Status.APPROVED])
        return Response(local(FloodPointAdminSerializer(qs[:300], many=True).data))


class AdminFloodActionView(APIView):
    """POST /api/admin/flood-points/<id>/<action>/: approve, reject, level {level}, merge {into}."""
    permission_classes = [IsAdminRole]

    @transaction.atomic
    def post(self, request, pk, action):
        point = get_object_or_404(FloodPoint.objects.select_for_update(), pk=pk)
        now = timezone.now()
        if action == "approve":
            point.status, point.approved_by, point.approved_at = FloodPoint.Status.APPROVED, request.user, now
            point.expires_at = now + timedelta(hours=get_config("flood_point_ttl_hours"))
        elif action == "reject":
            point.status = FloodPoint.Status.REJECTED
        elif action == "level":
            if request.data.get("level") not in FloodPoint.Level.values:
                raise serializers.ValidationError({"level": "Mức ngập không hợp lệ."})
            point.level = request.data["level"]
        elif action == "merge":
            target = get_object_or_404(FloodPoint, pk=request.data.get("into"))
            if target.pk == point.pk:
                raise serializers.ValidationError({"into": "Không gộp một điểm vào chính nó."})
            point.merged_into, point.status = target, FloodPoint.Status.REJECTED
            target.expires_at = max(target.expires_at, point.expires_at)
            target.save(update_fields=["expires_at"])
        else:
            raise Http404
        point.save()
        return Response(local(FloodPointAdminSerializer(point).data))


class FloodPhotoView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request, pk):
        point = get_object_or_404(FloodPoint, pk=pk)
        if not point.photo:
            raise Http404
        return FileResponse(point.photo.open("rb"))
