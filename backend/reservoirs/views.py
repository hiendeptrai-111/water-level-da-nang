import csv
from datetime import datetime, time, timedelta

from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import mixins, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminRole
from core.models import AuditLog
from core.services import audit, get_config

from .forecasting import model_info
from .models import (Forecast, OperatingDirective, OperationRecord, Rainfall,
                     RegulatoryThreshold, Reservoir, UpdateRun)
from .pipeline import simulation_range
from .serializers import DirectiveSerializer, ThresholdSerializer
from .services import reservoir_queryset, reservoir_status


# ---------------------------------------------------------------- query parameters
def parse_time(text, field, end_of_day=False):
    """'YYYY-MM-DD' or 'YYYY-MM-DDTHH:MM' (local time) -> aware datetime."""
    try:
        if len(text) == 10:
            d = datetime.fromisoformat(text).date()
            value = datetime.combine(d, time(23) if end_of_day else time(0))
        else:
            value = datetime.fromisoformat(text)
    except ValueError as e:
        raise serializers.ValidationError(
            {field: "Thời điểm không hợp lệ (dạng YYYY-MM-DD hoặc YYYY-MM-DDTHH:MM)."}) from e
    return value if value.tzinfo else timezone.make_aware(value)


def view_mode(request):
    """(simulation, at). Live data by default; ?simulation=1[&at=...] shows replay results as
    they were at `at` (default: the last simulated hour)."""
    if request.query_params.get("simulation") not in ("1", "true"):
        return False, None
    first, last = simulation_range()
    if last is None:
        raise serializers.ValidationError(
            {"simulation": "Chưa có dữ liệu mô phỏng (chạy lệnh replay_forecasts)."})
    at = request.query_params.get("at")
    return True, parse_time(at, "at") if at else last


def simulation_info():
    first, last = simulation_range()
    return {"available": last is not None, "from": first, "to": last}


def local(data):
    """Aware datetimes -> local time (+07:00) in plain dict responses, like DRF serializers."""
    if isinstance(data, dict):
        return {k: local(v) for k, v in data.items()}
    if isinstance(data, list):
        return [local(v) for v in data]
    if isinstance(data, datetime) and data.tzinfo is not None:
        return timezone.localtime(data)
    return data


class PublicView(APIView):
    """Public data: no login, no personal information."""
    permission_classes = [AllowAny]
    authentication_classes = []

    def finalize_response(self, request, response, *args, **kwargs):
        if isinstance(getattr(response, "data", None), (dict, list)):
            response.data = local(response.data)
        return super().finalize_response(request, response, *args, **kwargs)


# ---------------------------------------------------------------- public (CN06, CN07)
class ReservoirListView(PublicView):
    def get(self, request):
        simulation, at = view_mode(request)
        return Response({
            "generated_at": timezone.now(),
            "refresh_minutes": get_config("overview_refresh_minutes"),
            "simulation": simulation,
            "at": at,
            "reservoirs": [reservoir_status(r, at=at, simulation=simulation)
                           for r in reservoir_queryset()],
        })


class SimulationInfoView(PublicView):
    def get(self, request):
        return Response(simulation_info())


class ReservoirDetailView(PublicView):
    def get(self, request, code):
        simulation, at = view_mode(request)
        reservoir = get_object_or_404(reservoir_queryset(), code=code)
        return Response(reservoir_status(reservoir, at=at, simulation=simulation,
                                         with_forecast=True))


class ReservoirForecastView(PublicView):
    def get(self, request, code):
        simulation, at = view_mode(request)
        reservoir = get_object_or_404(reservoir_queryset(), code=code)
        s = reservoir_status(reservoir, at=at, simulation=simulation, with_forecast=True)
        keys = ("code", "name", "data_time", "stale", "water_level", "forecast_available",
                "forecast_issued_at", "forecast", "forecast_message", "alert_level",
                "alert_level_label", "needs_confirmation", "confirmation_reason", "thresholds",
                "directives", "model", "simulation")
        return Response({k: s[k] for k in keys})


class ReservoirHistoryView(PublicView):
    """Hourly history, at most history_max_days per request. Default: the last 7 days."""

    def get(self, request, code):
        simulation, at = view_mode(request)
        reservoir = get_object_or_404(Reservoir, code=code)
        p = request.query_params
        end = parse_time(p["to"], "to", end_of_day=True) if p.get("to") else (at or timezone.now())
        start = parse_time(p["from"], "from") if p.get("from") else end - timedelta(days=7)
        max_days = get_config("history_max_days")
        if end < start:
            raise serializers.ValidationError({"to": "Thời điểm cuối phải sau thời điểm đầu."})
        if end - start > timedelta(days=max_days):
            raise serializers.ValidationError({"to": f"Tối đa {max_days} ngày mỗi lần xem."})
        if at and end > at:            # replay view: nothing after the simulated "now"
            end = at
        return Response({"code": reservoir.code, "from": start, "to": end,
                         "points": history_points(reservoir, start, end)})


def history_points(reservoir, start, end):
    points = {}
    for r in OperationRecord.objects.filter(reservoir=reservoir, time__range=(start, end)):
        points[r.time] = {"time": r.time, "water_level": r.water_level, "inflow": r.inflow,
                          "turbine_flow": r.turbine_flow, "spillway_flow": r.spillway_flow,
                          "suspicious": r.suspicious, "rain_mm": None, "rain_source": None}
    for r in Rainfall.objects.filter(reservoir=reservoir, time__range=(start, end)):
        p = points.setdefault(r.time, {"time": r.time, "water_level": None, "inflow": None,
                                       "turbine_flow": None, "spillway_flow": None,
                                       "suspicious": False})
        p.update(rain_mm=r.rain_mm, rain_source=r.source)
    return [points[t] for t in sorted(points)]


# ---------------------------------------------------------------- admin: thresholds, directives (CN24)
class AdminThresholdViewSet(mixins.ListModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    """GET /api/admin/thresholds/, PATCH /api/admin/thresholds/<id>/"""
    permission_classes = [IsAdminRole]
    serializer_class = ThresholdSerializer
    pagination_class = None
    http_method_names = ["get", "patch", "head", "options"]
    queryset = RegulatoryThreshold.objects.select_related("reservoir").order_by(
        "kind", "reservoir__display_order", "start_day")

    def perform_update(self, serializer):
        fields = ("start_day", "end_day", "value_low", "value_high", "document")
        before = {f: getattr(serializer.instance, f) for f in fields}
        obj = serializer.save()
        changed = {f: [str(v), str(getattr(obj, f))] for f, v in before.items() if v != getattr(obj, f)}
        if changed:
            audit(AuditLog.Action.THRESHOLD_CHANGED, actor=self.request.user, target=obj,
                  request=self.request, details=changed)


class AdminDirectiveViewSet(mixins.ListModelMixin, mixins.CreateModelMixin,
                            mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """No update, no delete: an old directive is only marked inactive (CN24)."""
    permission_classes = [IsAdminRole]
    serializer_class = DirectiveSerializer
    pagination_class = None
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        qs = OperatingDirective.objects.select_related("reservoir", "entered_by", "deactivated_by")
        p = self.request.query_params
        if p.get("reservoir"):
            qs = qs.filter(reservoir__code=p["reservoir"])
        if p.get("is_active") in ("true", "false"):
            qs = qs.filter(is_active=p["is_active"] == "true")
        return qs

    def perform_create(self, serializer):
        with transaction.atomic():
            obj = serializer.save(entered_by=self.request.user, is_active=True)
            audit(AuditLog.Action.DIRECTIVE_CREATED, actor=self.request.user, target=obj,
                  request=self.request,
                  details={"reservoir": obj.reservoir.code, "requirement": obj.requirement,
                           "target_level": obj.target_level, "document": obj.document})

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def deactivate(self, request, pk=None):
        obj = self.get_object()
        if obj.is_active:
            obj.is_active = False
            obj.deactivated_at = timezone.now()
            obj.deactivated_by = request.user
            obj.save(update_fields=["is_active", "deactivated_at", "deactivated_by"])
            audit(AuditLog.Action.DIRECTIVE_DEACTIVATED, actor=request.user, target=obj,
                  request=request, details={"reservoir": obj.reservoir.code})
        return Response(self.get_serializer(obj).data)


# ---------------------------------------------------------------- admin: data and model status (CN27)
class DataStatusView(PublicView):
    permission_classes = [IsAdminRole]
    authentication_classes = APIView.authentication_classes

    def get(self, request):
        now = timezone.now()
        steps = []
        for step in UpdateRun.Step:
            qs = UpdateRun.objects.filter(kind=UpdateRun.Kind.LIVE, step=step)
            ok = qs.filter(success=True).first()
            err = qs.filter(success=False).select_related("reservoir").first()
            steps.append({
                "step": step.value, "label": step.label,
                "last_success_at": ok.started_at if ok else None,
                "last_note": ok.details.get("note") if ok else None,
                "last_error_at": err.started_at if err else None,
                "last_error": err.error if err else None,
                "last_error_reservoir": err.reservoir.name if err and err.reservoir else None,
                "error_is_latest": bool(err and (not ok or err.started_at > ok.started_at)),
            })
        week_start = (timezone.localtime(now) - timedelta(days=7)).replace(minute=0, second=0,
                                                                           microsecond=0)
        hours_in_week = int((now - week_start).total_seconds() // 3600) + 1
        stale_after = timedelta(hours=get_config("stale_data_hours"))
        reservoirs = []
        for r in Reservoir.objects.all():
            recs = OperationRecord.objects.filter(reservoir=r, time__gte=week_start, time__lte=now)
            latest = OperationRecord.objects.filter(reservoir=r, water_level__isnull=False) \
                .order_by("-time").first()
            rain = Rainfall.objects.filter(reservoir=r).order_by("-time").first()
            suspicious = recs.filter(suspicious=True).order_by("-time")
            reservoirs.append({
                "code": r.code, "name": r.name,
                "latest_data_time": latest.time if latest else None,
                "stale": latest is None or now - latest.time > stale_after,
                "latest_rain_time": rain.time if rain else None,
                "latest_rain_source": rain.source if rain else None,
                "hours_in_week": hours_in_week,
                "missing_hours_week": hours_in_week - recs.filter(water_level__isnull=False).count(),
                "suspicious_hours_week": [
                    {"time": s.time, "water_level": s.water_level, "inflow": s.inflow,
                     "turbine_flow": s.turbine_flow, "spillway_flow": s.spillway_flow}
                    for s in suspicious[:50]],
                "latest_forecast_at": Forecast.objects.filter(reservoir=r, is_simulation=False)
                .order_by("-issued_at").values_list("issued_at", flat=True).first(),
            })
        return Response({"generated_at": now, "steps": steps, "reservoirs": reservoirs,
                         "model": model_info(), "simulation": simulation_info()})


# ---------------------------------------------------------------- admin: CSV export (CN08)
class ExportView(APIView):
    """CSV (UTF-8 with BOM so Excel opens it directly): operating data, rain and forecasts."""
    permission_classes = [IsAdminRole]
    MAX_DAYS = 366

    def get(self, request, code):
        reservoir = get_object_or_404(Reservoir, code=code)
        p = request.query_params
        if not p.get("from") or not p.get("to"):
            raise serializers.ValidationError({"from": "Cần chọn khoảng thời gian (from, to)."})
        start, end = parse_time(p["from"], "from"), parse_time(p["to"], "to", end_of_day=True)
        if end < start or end - start > timedelta(days=self.MAX_DAYS):
            raise serializers.ValidationError({"to": f"Khoảng thời gian không hợp lệ (tối đa {self.MAX_DAYS} ngày)."})
        simulation = p.get("simulation") in ("1", "true")
        rows = {pt["time"]: pt for pt in history_points(reservoir, start, end)}
        forecasts = {}
        for f in Forecast.objects.filter(reservoir=reservoir, is_simulation=simulation,
                                         issued_at__range=(start, end)):
            forecasts.setdefault(f.issued_at, {})[f.horizon] = f

        response = HttpResponse(content_type="text/csv; charset=utf-8")
        name = f"{reservoir.code}_{timezone.localtime(start):%Y%m%d}_{timezone.localtime(end):%Y%m%d}"
        name += "_mo_phong" if simulation else ""
        response["Content-Disposition"] = f'attachment; filename="{name}.csv"'
        response.write("﻿")
        w = csv.writer(response)
        w.writerow(["thoi_gian", "muc_nuoc_m", "luu_luong_den_m3s", "qua_may_m3s", "qua_tran_m3s",
                    "nghi_ngo", "mua_mm", "nguon_mua", "du_bao_1h_m", "muc_1h", "du_bao_3h_m",
                    "muc_3h", "muc_6h", "can_xac_nhan", "mo_phong"])
        for t in sorted(set(rows) | set(forecasts)):
            r = rows.get(t, {})
            fc = forecasts.get(t, {})
            w.writerow([
                f"{timezone.localtime(t):%Y-%m-%d %H:%M}", r.get("water_level"), r.get("inflow"),
                r.get("turbine_flow"), r.get("spillway_flow"), int(bool(r.get("suspicious"))),
                r.get("rain_mm"), r.get("rain_source"),
                getattr(fc.get(1), "expected_level", None), getattr(fc.get(1), "alert_level", None),
                getattr(fc.get(3), "expected_level", None), getattr(fc.get(3), "alert_level", None),
                getattr(fc.get(6), "alert_level", None),
                int(any(f.needs_confirmation for f in fc.values())) if fc else "",
                int(simulation)])
        return response
