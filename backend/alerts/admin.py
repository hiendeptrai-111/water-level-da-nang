from django.contrib import admin

from .models import Alert, AlertState, Notification


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    """Automatic alerts are created by update_forecasts; viewable only."""
    list_display = ("starts_at", "level", "source", "valid_until", "ended_at", "is_simulation")
    list_filter = ("level", "source", "is_simulation")
    date_hierarchy = "starts_at"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("created_at", "recipient", "channel", "is_reminder", "sent", "seen_at")
    list_filter = ("channel", "is_reminder", "sent")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(AlertState)
class AlertStateAdmin(admin.ModelAdmin):
    list_display = ("reservoir", "is_simulation", "level", "evaluated_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
