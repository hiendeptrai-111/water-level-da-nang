from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminRole
from reservoirs.models import AlertLevel, Forecast
from reservoirs.services import forecast_table
from reservoirs.views import local, parse_time, view_mode

from .models import Alert, Notification
from .serializers import AdminAlertSerializer, NotificationSerializer, PublicAlertSerializer

# Section 4.3: "Theo dõi" goes to admins only; the public sees "Cảnh báo" and "Khẩn cấp".
PUBLIC_LEVELS = [AlertLevel.WARNING, AlertLevel.EMERGENCY]


def active_at(qs, at):
    return qs.filter(starts_at__lte=at, valid_until__gt=at).filter(
        Q(ended_at__isnull=True) | Q(ended_at__gt=at))


class PublicAlertListView(APIView):
    """CN09: alerts in force. A logged-in citizen sees the alerts of their commune first."""
    permission_classes = [AllowAny]

    def get(self, request):
        simulation, at = view_mode(request)
        now = at or timezone.now()
        qs = active_at(Alert.objects.filter(is_simulation=simulation, level__in=PUBLIC_LEVELS), now)
        alerts = list(qs.prefetch_related("reservoirs", "wards"))
        ward_id = getattr(request.user, "ward_id", None) if request.user.is_authenticated else None
        data = PublicAlertSerializer(alerts, many=True, context={"ward_id": ward_id}).data
        data = sorted(data, key=lambda a: (not a["in_my_ward"],
                                           -PUBLIC_LEVELS.index(a["level"]), a["starts_at"]))
        return Response(local({"simulation": simulation, "at": at, "alerts": data}))


class NotificationPagination(PageNumberPagination):
    page_size = 30
    page_size_query_param = "page_size"
    max_page_size = 100


class NotificationViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """GET /api/notifications/ (web notifications of the current user), POST <id>/seen/,
    POST seen-all/. Seeing a notification records when (CN10 "Đã xem")."""
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationSerializer
    pagination_class = NotificationPagination

    def get_queryset(self):
        qs = (Notification.objects.filter(recipient=self.request.user,
                                          channel=Notification.Channel.WEB)
              .select_related("alert").prefetch_related("alert__reservoirs"))
        if self.request.query_params.get("unseen") in ("1", "true"):
            qs = qs.filter(seen_at__isnull=True)
        return qs

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        response.data["unseen_count"] = Notification.objects.filter(
            recipient=request.user, channel=Notification.Channel.WEB, seen_at__isnull=True).count()
        return response

    def _mark(self, qs):
        return qs.filter(seen_at__isnull=True).update(seen_at=timezone.now())

    @action(detail=True, methods=["post"])
    def seen(self, request, pk=None):
        note = self.get_object()
        # the e-mail copy of the same alert counts as acknowledged too
        self._mark(Notification.objects.filter(recipient=request.user, alert=note.alert,
                                               is_reminder=note.is_reminder))
        note.refresh_from_db()
        return Response(self.get_serializer(note).data)

    @action(detail=False, methods=["post"], url_path="seen-all")
    def seen_all(self, request):
        n = self._mark(Notification.objects.filter(recipient=request.user))
        return Response({"marked": n})


class AlertPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 200


class AdminAlertViewSet(viewsets.ReadOnlyModelViewSet):
    """CN12: every alert generated or issued, filtered by reservoir, level, source, period;
    ?active=1 for the alerts in force (all levels). Detail includes the forecast behind it."""
    permission_classes = [IsAdminRole]
    serializer_class = AdminAlertSerializer
    pagination_class = AlertPagination

    def get_queryset(self):
        p = self.request.query_params
        simulation = p.get("simulation") in ("1", "true")
        qs = (Alert.objects.filter(is_simulation=simulation)
              .select_related("issued_by", "forecast")
              .prefetch_related("reservoirs", "wards")
              .annotate(notification_count=Count("notifications",
                                                 filter=Q(notifications__channel="web")),
                        seen_count=Count("notifications", filter=Q(notifications__channel="web",
                                                                   notifications__seen_at__isnull=False)))
              .order_by("-starts_at", "-id"))
        if p.get("reservoir"):
            qs = qs.filter(reservoirs__code=p["reservoir"])
        if p.get("level"):
            qs = qs.filter(level=p["level"])
        if p.get("source"):
            qs = qs.filter(source=p["source"])
        if p.get("from"):
            qs = qs.filter(starts_at__gte=parse_time(p["from"], "from"))
        if p.get("to"):
            qs = qs.filter(starts_at__lte=parse_time(p["to"], "to", end_of_day=True))
        if p.get("active") in ("1", "true"):
            qs = active_at(qs, timezone.now())
        return qs

    def retrieve(self, request, *args, **kwargs):
        alert = self.get_object()
        data = self.get_serializer(alert).data
        data["forecast"] = None
        if alert.forecast_id:
            f = alert.forecast
            rows = list(Forecast.objects.filter(reservoir=f.reservoir, issued_at=f.issued_at,
                                                is_simulation=f.is_simulation).order_by("horizon"))
            data["forecast"] = {"reservoir": f.reservoir.code, "issued_at": f.issued_at,
                                "model_version": f.model_version,
                                "horizons": forecast_table(f.reservoir, rows, f.issued_at),
                                "details": f.details}
            data["forecast"] = local(data["forecast"])
        data["notifications"] = [
            {"recipient": str(n.recipient), "channel": n.channel, "is_reminder": n.is_reminder,
             "sent": n.sent, "created_at": n.created_at, "seen_at": n.seen_at}
            for n in alert.notifications.select_related("recipient").order_by("created_at")]
        return Response(data)
