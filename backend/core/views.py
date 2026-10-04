from rest_framework import mixins, viewsets
from rest_framework.pagination import PageNumberPagination

from accounts.permissions import IsAdminRole

from .models import AuditLog, SystemConfig
from .serializers import AuditLogSerializer, SystemConfigSerializer
from .services import audit


class SystemConfigViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin,
                          mixins.UpdateModelMixin, viewsets.GenericViewSet):
    """GET /api/admin/config/, PATCH /api/admin/config/<key>/ {"value": ...}"""
    queryset = SystemConfig.objects.all()
    serializer_class = SystemConfigSerializer
    permission_classes = [IsAdminRole]
    lookup_field = "key"
    pagination_class = None
    http_method_names = ["get", "patch", "head", "options"]

    def perform_update(self, serializer):
        old = serializer.instance.value
        obj = serializer.save(updated_by=self.request.user)
        if old != obj.value:
            audit(AuditLog.Action.CONFIG_CHANGED, actor=self.request.user, target=obj,
                  request=self.request,
                  details={"key": obj.key, "old": str(old), "new": str(obj.value), "via": "api"})


class AuditLogPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 200


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only: the API offers no create/update/delete for the system log."""
    serializer_class = AuditLogSerializer
    permission_classes = [IsAdminRole]
    pagination_class = AuditLogPagination

    def get_queryset(self):
        qs = AuditLog.objects.all()
        action = self.request.query_params.get("action")
        if action:
            qs = qs.filter(action=action)
        return qs
