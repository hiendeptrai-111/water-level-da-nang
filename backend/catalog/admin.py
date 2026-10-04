from django.contrib import admin

from .models import RescueTeam, Ward


@admin.register(Ward)
class WardAdmin(admin.ModelAdmin):
    list_display = ("name", "kind", "priority", "latitude", "longitude")
    list_filter = ("kind",)
    search_fields = ("name",)
    list_editable = ("priority",)


@admin.register(RescueTeam)
class RescueTeamAdmin(admin.ModelAdmin):
    list_display = ("name", "phone_number", "vehicles")
    search_fields = ("name", "phone_number")
