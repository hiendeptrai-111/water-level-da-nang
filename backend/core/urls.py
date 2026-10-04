from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter()
router.register("admin/config", views.SystemConfigViewSet, basename="admin-config")
router.register("admin/audit-logs", views.AuditLogViewSet, basename="admin-audit-log")

urlpatterns = router.urls
