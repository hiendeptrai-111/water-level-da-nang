from rest_framework import serializers

from .models import Alert, Notification


def _reservoirs(alert):
    return [{"code": r.code, "name": r.name} for r in alert.reservoirs.all()]


class PublicAlertSerializer(serializers.ModelSerializer):
    """CN09: no personal data (who issued it is not shown)."""
    level_label = serializers.CharField(source="get_level_display", read_only=True)
    source_label = serializers.CharField(source="get_source_display", read_only=True)
    reservoirs = serializers.SerializerMethodField()
    wards = serializers.SerializerMethodField()
    in_my_ward = serializers.SerializerMethodField()

    class Meta:
        model = Alert
        fields = ["id", "level", "level_label", "source", "source_label", "content", "reservoirs",
                  "wards", "starts_at", "valid_until", "ended_at", "is_simulation", "in_my_ward"]
        read_only_fields = fields

    def get_reservoirs(self, obj):
        return _reservoirs(obj)

    def get_wards(self, obj):
        return [{"id": w.id, "label": str(w)} for w in obj.wards.all()]

    def get_in_my_ward(self, obj):
        ward_id = self.context.get("ward_id")
        return bool(ward_id and any(w.id == ward_id for w in obj.wards.all()))


class AdminAlertSerializer(PublicAlertSerializer):
    issued_by = serializers.StringRelatedField()
    forecast_issued_at = serializers.DateTimeField(source="forecast.issued_at", read_only=True,
                                                   default=None)
    notification_count = serializers.IntegerField(read_only=True, default=0)
    seen_count = serializers.IntegerField(read_only=True, default=0)

    class Meta(PublicAlertSerializer.Meta):
        fields = PublicAlertSerializer.Meta.fields + [
            "issued_by", "forecast_issued_at", "last_notified_at", "notification_count", "seen_count"]
        read_only_fields = fields


class NotificationSerializer(serializers.ModelSerializer):
    alert_level = serializers.CharField(source="alert.level", read_only=True)
    alert_level_label = serializers.CharField(source="alert.get_level_display", read_only=True)
    reservoirs = serializers.SerializerMethodField()
    is_simulation = serializers.BooleanField(source="alert.is_simulation", read_only=True)

    class Meta:
        model = Notification
        fields = ["id", "alert", "alert_level", "alert_level_label", "reservoirs", "content",
                  "is_reminder", "is_simulation", "created_at", "seen_at"]
        read_only_fields = fields

    def get_reservoirs(self, obj):
        return _reservoirs(obj.alert)
