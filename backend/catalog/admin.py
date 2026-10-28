from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError

from core.models import AuditLog
from core.services import audit
from reservoirs.models import ReservoirWard

from .models import RescueTeam, Ward
from .services import check_in_da_nang, set_coordinates_manually


class WardForm(forms.ModelForm):
    class Meta:
        model = Ward
        fields = "__all__"

    def clean(self):
        data = super().clean()
        try:
            check_in_da_nang(data.get("latitude"), data.get("longitude"))
        except ValidationError as e:
            raise ValidationError({"latitude": e.messages}) from e
        return data


def audit_link(request, link, action):
    audit(AuditLog.Action.RESERVOIR_WARD_CHANGED, actor=request.user, target=link.ward,
          request=request, details={"action": action, "reservoir": link.reservoir.code,
                                    "zone": link.zone, "needs_verification": link.needs_verification,
                                    "via": "django-admin"})


class ReservoirWardInline(admin.TabularInline):
    """CN25: reservoir – commune links (zone, needs verification) on the commune page."""
    model = ReservoirWard
    extra = 0
    fields = ("reservoir", "zone", "needs_verification")


@admin.register(Ward)
class WardAdmin(admin.ModelAdmin):
    """CN25: centre coordinates (validated inside Da Nang, every change logged) and links."""
    form = WardForm
    list_display = ("name", "kind", "priority", "latitude", "longitude", "coord_confidence")
    list_filter = ("kind", "coord_confidence")
    search_fields = ("name",)
    list_editable = ("priority",)
    fields = ("name", "kind", "priority", "latitude", "longitude", "coord_confidence",
              "coord_source", "coord_note", "osm_id")
    readonly_fields = ("name", "kind", "coord_confidence", "coord_source", "coord_note", "osm_id")
    inlines = [ReservoirWardInline]

    def has_add_permission(self, request):
        return False                       # the 94 units come from load_wards

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        lat, lon = obj.latitude, obj.longitude
        if change and {"latitude", "longitude"} & set(form.changed_data):
            stored = Ward.objects.get(pk=obj.pk)
            obj.latitude, obj.longitude = stored.latitude, stored.longitude
            super().save_model(request, obj, form, change)
            set_coordinates_manually(obj, lat, lon, actor=request.user, request=request,
                                     via="django-admin")
        else:
            super().save_model(request, obj, form, change)

    def save_formset(self, request, form, formset, change):
        links = formset.save(commit=False)
        for link in formset.deleted_objects:
            audit_link(request, link, "deleted")
            link.delete()
        for link in links:
            is_new = link.pk is None
            link.save()
            audit_link(request, link, "created" if is_new else "changed")
        formset.save_m2m()


@admin.register(RescueTeam)
class RescueTeamAdmin(admin.ModelAdmin):
    """CN26: name, base, members, phone, vehicles, communes usually covered."""
    list_display = ("name", "phone_number", "vehicles", "member_count", "base_name", "status",
                    "location_updated_at")
    list_filter = ("status",)
    search_fields = ("name", "phone_number", "base_name")
    filter_horizontal = ("service_wards",)
    fields = ("name", "phone_number", "vehicles", "member_count", "base_name", "base_latitude",
              "base_longitude", "service_wards", "status", "current_latitude", "current_longitude",
              "location_updated_at")
    readonly_fields = ("current_latitude", "current_longitude", "location_updated_at")

    def save_model(self, request, obj, form, change):
        try:
            check_in_da_nang(obj.base_latitude, obj.base_longitude)
        except ValidationError as e:
            from django.contrib import messages
            messages.warning(request, f"Căn cứ: {' '.join(e.messages)}")
        super().save_model(request, obj, form, change)
