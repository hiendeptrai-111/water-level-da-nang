from django.contrib import admin

from .models import SOS, FloodPoint, SOSHistory


class SOSHistoryInline(admin.TabularInline):
    model = SOSHistory
    extra = 0
    can_delete = False
    fields = ("time", "from_status", "to_status", "actor_label", "note")
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(SOS)
class SOSAdmin(admin.ModelAdmin):
    """Read-only here: SOS are handled on /admin/sos (status changes must go through the
    services so that SOSHistory gets a row)."""
    list_display = ("code", "status", "priority_score", "ward", "team", "created_at", "anonymized_at", "is_demo")
    list_filter = ("status", "is_demo")
    search_fields = ("code", "phone")
    inlines = [SOSHistoryInline]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(FloodPoint)
class FloodPointAdmin(admin.ModelAdmin):
    list_display = ("created_at", "level", "status", "reporter", "expires_at", "is_demo")
    list_filter = ("status", "level", "is_demo")

    def has_add_permission(self, request):
        return False
