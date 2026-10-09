from django.contrib import admin

from core.models import AuditLog
from core.services import audit

from .models import (Forecast, OperatingDirective, OperationRecord, Rainfall, RegulatoryThreshold,
                     Reservoir, ReservoirWard, UpdateRun)


class ReadOnlyAdmin(admin.ModelAdmin):
    """Data written by commands only: viewable here, never edited by hand."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Reservoir)
class ReservoirAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "normal_water_level", "latitude", "longitude", "display_order")
    readonly_fields = ("code", "model_key")

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ReservoirWard)
class ReservoirWardAdmin(admin.ModelAdmin):
    list_display = ("reservoir", "ward", "zone", "needs_verification")
    list_filter = ("reservoir", "zone", "needs_verification")


@admin.register(RegulatoryThreshold)
class RegulatoryThresholdAdmin(admin.ModelAdmin):
    list_display = ("reservoir", "kind", "start_day", "end_day", "value_low", "value_high", "document")
    list_filter = ("reservoir", "kind")

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if change and form.changed_data:
            audit(AuditLog.Action.THRESHOLD_CHANGED, actor=request.user, target=obj, request=request,
                  details={f: str(form.cleaned_data[f]) for f in form.changed_data} | {"via": "django-admin"})


@admin.register(OperatingDirective)
class OperatingDirectiveAdmin(admin.ModelAdmin):
    """Added and deactivated in the app (/admin/thresholds); never deleted."""
    list_display = ("reservoir", "requirement", "target_level", "starts_at", "deadline", "document",
                    "is_active")
    list_filter = ("reservoir", "is_active")

    def get_actions(self, request):
        return {}

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(OperationRecord)
class OperationRecordAdmin(ReadOnlyAdmin):
    list_display = ("reservoir", "time", "water_level", "inflow", "turbine_flow", "spillway_flow",
                    "suspicious")
    list_filter = ("reservoir", "suspicious")
    date_hierarchy = "time"


@admin.register(Rainfall)
class RainfallAdmin(ReadOnlyAdmin):
    list_display = ("reservoir", "time", "rain_mm", "source")
    list_filter = ("reservoir", "source")
    date_hierarchy = "time"


@admin.register(Forecast)
class ForecastAdmin(ReadOnlyAdmin):
    list_display = ("reservoir", "issued_at", "horizon", "expected_level", "alert_level",
                    "needs_confirmation", "is_simulation", "model_version")
    list_filter = ("reservoir", "is_simulation", "alert_level", "horizon")
    date_hierarchy = "issued_at"


@admin.register(UpdateRun)
class UpdateRunAdmin(ReadOnlyAdmin):
    list_display = ("started_at", "kind", "step", "reservoir", "success", "error")
    list_filter = ("kind", "step", "success")
