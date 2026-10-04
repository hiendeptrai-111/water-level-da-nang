from rest_framework import serializers

from .config_defaults import DEFAULTS
from .models import AuditLog, SystemConfig


class SystemConfigSerializer(serializers.ModelSerializer):
    updated_by = serializers.StringRelatedField()

    class Meta:
        model = SystemConfig
        fields = ["key", "value", "unit", "description", "updated_at", "updated_by"]
        read_only_fields = ["key", "unit", "description", "updated_at", "updated_by"]

    def validate_value(self, value):
        minimum = DEFAULTS[self.instance.key][2]
        if value < minimum:
            raise serializers.ValidationError(f"Giá trị phải ≥ {minimum}")
        return value


class AuditLogSerializer(serializers.ModelSerializer):
    action_label = serializers.CharField(source="get_action_display", read_only=True)

    class Meta:
        model = AuditLog
        fields = ["id", "created_at", "actor", "actor_label", "action", "action_label",
                  "target_type", "target_id", "target_label", "details", "ip_address"]
        read_only_fields = fields
