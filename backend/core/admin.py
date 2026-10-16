from django.contrib import admin

from .config_defaults import READ_ONLY_KEYS
from .models import AuditLog, SystemConfig
from .services import audit


@admin.register(SystemConfig)
class SystemConfigAdmin(admin.ModelAdmin):
    list_display = ("key", "value", "unit", "description", "updated_at", "updated_by")
    readonly_fields = ("key", "unit", "description", "updated_at", "updated_by")
    fields = ("key", "value", "unit", "description", "updated_at", "updated_by")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        if obj is not None and obj.key in READ_ONLY_KEYS:
            return False                  # shown, never edited (model-bound value)
        return super().has_change_permission(request, obj)

    def save_model(self, request, obj, form, change):
        old = SystemConfig.objects.get(pk=obj.pk).value if obj.pk else None
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
        if old != obj.value:
            audit(AuditLog.Action.CONFIG_CHANGED, actor=request.user, target=obj, request=request,
                  details={"key": obj.key, "old": str(old), "new": str(obj.value), "via": "django-admin"})


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Read-only: no add, change or delete through the Django admin."""
    list_display = ("created_at", "actor_label", "action", "target_label", "ip_address")
    list_filter = ("action",)
    search_fields = ("actor_label", "target_label")
    date_hierarchy = "created_at"

    def get_actions(self, request):
        return {}

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
