from rest_framework import serializers

from .models import RescueTeam, Ward


class WardSerializer(serializers.ModelSerializer):
    kind_label = serializers.CharField(source="get_kind_display", read_only=True)
    label = serializers.CharField(source="__str__", read_only=True)

    class Meta:
        model = Ward
        fields = ["id", "name", "kind", "kind_label", "label", "latitude", "longitude", "priority"]


class RescueTeamSerializer(serializers.ModelSerializer):
    class Meta:
        model = RescueTeam
        fields = ["id", "name", "phone_number", "vehicles"]
