from django.contrib import admin

from .models import WeatherReading


@admin.register(WeatherReading)
class WeatherReadingAdmin(admin.ModelAdmin):
    """Cache written by update_weather: view only."""
    list_display = ("ward", "time", "kind", "temperature", "precipitation", "wind_speed", "updated_at")
    list_filter = ("kind",)
    search_fields = ("ward__name",)
    date_hierarchy = "time"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
