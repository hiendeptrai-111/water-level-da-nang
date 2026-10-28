from django.utils import timezone
from rest_framework import serializers

from accounts.models import phone_validator
from catalog.models import RescueTeam
from core.services import get_config

from .models import SOS, FloodPoint
from .services import priority_band

IMAGE_MAGIC = {b"\xff\xd8\xff": "jpeg", b"\x89PNG": "png", b"RIFF": "webp"}


def validate_photo(f):
    """At most sos_photo_max_kb, and really a JPEG / PNG / WebP image (magic bytes)."""
    limit = get_config("sos_photo_max_kb") * 1024
    if f.size > limit:
        raise serializers.ValidationError(f"Ảnh tối đa {limit // 1024} KB.")
    head = f.read(12)
    f.seek(0)
    if not any(head.startswith(m) for m in IMAGE_MAGIC) or (head.startswith(b"RIFF") and head[8:12] != b"WEBP"):
        raise serializers.ValidationError("Chỉ nhận ảnh JPEG, PNG hoặc WebP.")
    return f


class LocationSerializer(serializers.Serializer):
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6, min_value=-90, max_value=90)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6, min_value=-180, max_value=180)


class SOSCreateSerializer(LocationSerializer):
    phone = serializers.CharField(required=False, allow_blank=True, validators=[phone_validator])
    accuracy_m = serializers.FloatField(required=False, allow_null=True, min_value=0)
    location_source = serializers.ChoiceField(choices=["gps", "map"], default="gps")
    device_id = serializers.CharField(required=False, allow_blank=True, max_length=64)


class SOSSupplementSerializer(serializers.Serializer):
    people_count = serializers.ChoiceField(choices=SOS.People.choices, required=False, allow_blank=True)
    vulnerable_groups = serializers.ListField(child=serializers.ChoiceField(choices=SOS.Vulnerable.choices),
                                              required=False, max_length=5)
    water_level = serializers.ChoiceField(choices=SOS.WaterLevel.choices, required=False, allow_blank=True)
    note = serializers.CharField(required=False, allow_blank=True, max_length=300)
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False)
    accuracy_m = serializers.FloatField(required=False, allow_null=True, min_value=0)


# Steps of the status flow shown to the sender (spec Hình 2).
FLOW = [SOS.Status.NEW, SOS.Status.RECEIVED, SOS.Status.MOVING, SOS.Status.RESCUED, SOS.Status.CLOSED]


def wait_minutes(sos):
    return round((timezone.now() - sos.created_at).total_seconds() / 60)


def team_brief(team, with_phone=False):
    if team is None:
        return None
    out = {"id": team.id, "name": team.name, "vehicles": team.vehicles}
    if with_phone:
        out["phone_number"] = team.phone_number
    return out


class SOSTrackSerializer(serializers.ModelSerializer):
    """For the sender (CN16): status steps with times, team, estimated arrival."""
    status_label = serializers.CharField(source="get_status_display")
    steps = serializers.SerializerMethodField()
    team = serializers.SerializerMethodField()
    ward_label = serializers.SerializerMethodField()

    class Meta:
        model = SOS
        fields = ["code", "status", "status_label", "steps", "team", "eta_seconds", "route_mode", "arrived_at",
                  "latitude", "longitude", "accuracy_m", "ward_label", "people_count", "vulnerable_groups",
                  "water_level", "note", "created_at", "finished_at"]

    def get_steps(self, obj):
        reached = {}
        for h in obj.history.all():
            reached.setdefault(h.to_status, h.time)
        steps = [{"status": s, "label": SOS.Status(s).label, "time": reached.get(s)} for s in FLOW]
        if obj.status in (SOS.Status.CANCELLED, SOS.Status.UNREACHABLE):
            steps.append({"status": obj.status, "label": obj.get_status_display(), "time": reached.get(obj.status)})
        return steps

    def get_team(self, obj):
        return team_brief(obj.team, with_phone=True)

    def get_ward_label(self, obj):
        return str(obj.ward) if obj.ward else None


class SOSDispatchSerializer(serializers.ModelSerializer):
    """Admin (CN17): everything, including the phone number."""
    status_label = serializers.CharField(source="get_status_display")
    priority = serializers.SerializerMethodField()
    wait_minutes = serializers.SerializerMethodField()
    ward_label = serializers.SerializerMethodField()
    team = serializers.SerializerMethodField()
    handled_by = serializers.StringRelatedField()
    sender_name = serializers.SerializerMethodField()
    has_photo = serializers.SerializerMethodField()
    merged_into_code = serializers.CharField(source="merged_into.code", default=None)

    class Meta:
        model = SOS
        fields = ["id", "code", "status", "status_label", "priority", "priority_score", "wait_minutes",
                  "latitude", "longitude", "accuracy_m", "location_source", "ward", "ward_label", "phone",
                  "sender_name", "people_count", "vulnerable_groups", "water_level", "note", "has_photo",
                  "team", "handled_by", "eta_seconds", "route", "route_mode", "arrived_at", "merged_into",
                  "merged_into_code", "created_at", "finished_at", "is_demo"]

    def get_priority(self, obj):
        key, label = priority_band(obj.priority_score)
        return {"key": key, "label": label}

    def get_wait_minutes(self, obj):
        return wait_minutes(obj)

    def get_ward_label(self, obj):
        return str(obj.ward) if obj.ward else None

    def get_team(self, obj):
        return team_brief(obj.team, with_phone=True)

    def get_sender_name(self, obj):
        return obj.sender.full_name if obj.sender else None

    def get_has_photo(self, obj):
        return bool(obj.photo)


class SOSClaimableSerializer(serializers.ModelSerializer):
    """Rescue team, before claiming (CN19): position, priority, waiting time. NO phone."""
    priority = serializers.SerializerMethodField()
    wait_minutes = serializers.SerializerMethodField()
    ward_label = serializers.SerializerMethodField()

    class Meta:
        model = SOS
        fields = ["id", "code", "latitude", "longitude", "ward_label", "priority", "priority_score",
                  "wait_minutes", "people_count", "vulnerable_groups", "water_level", "created_at"]

    get_priority = SOSDispatchSerializer.get_priority
    get_wait_minutes = SOSDispatchSerializer.get_wait_minutes
    get_ward_label = SOSDispatchSerializer.get_ward_label


class SOSTaskSerializer(SOSClaimableSerializer):
    """Rescue team, task assigned / claimed: phone and details shown."""
    status_label = serializers.CharField(source="get_status_display")
    has_photo = serializers.SerializerMethodField()

    class Meta(SOSClaimableSerializer.Meta):
        fields = SOSClaimableSerializer.Meta.fields + [
            "status", "status_label", "phone", "note", "has_photo", "eta_seconds", "route", "route_mode",
            "arrived_at"]

    get_has_photo = SOSDispatchSerializer.get_has_photo


class TeamSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    position = serializers.SerializerMethodField()

    class Meta:
        model = RescueTeam
        fields = ["id", "name", "phone_number", "vehicles", "member_count", "base_name", "base_latitude",
                  "base_longitude", "status", "status_label", "current_latitude", "current_longitude",
                  "location_updated_at", "position"]
        read_only_fields = fields

    def get_position(self, obj):
        from .services import team_position
        pos = team_position(obj)
        return {"latitude": pos[0], "longitude": pos[1]} if pos else None


class FloodPointPublicSerializer(serializers.ModelSerializer):
    """Public map: approved points only, never the reporter."""
    level_label = serializers.CharField(source="get_level_display")

    class Meta:
        model = FloodPoint
        fields = ["id", "latitude", "longitude", "level", "level_label", "confirmed_at", "expires_at"]


class FloodPointAdminSerializer(FloodPointPublicSerializer):
    status_label = serializers.CharField(source="get_status_display")
    reporter = serializers.StringRelatedField()
    reporter_role = serializers.CharField(source="reporter.role", default=None)
    approved_by = serializers.StringRelatedField()
    has_photo = serializers.SerializerMethodField()

    class Meta(FloodPointPublicSerializer.Meta):
        fields = FloodPointPublicSerializer.Meta.fields + [
            "status", "status_label", "reporter", "reporter_role", "approved_by", "approved_at", "created_at",
            "merged_into", "has_photo", "is_demo"]

    def get_has_photo(self, obj):
        return bool(obj.photo)


class FloodReportSerializer(LocationSerializer):
    level = serializers.ChoiceField(choices=FloodPoint.Level.choices)
    photo = serializers.FileField(required=False, validators=[validate_photo])
