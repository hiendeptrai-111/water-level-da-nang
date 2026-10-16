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


class WardCoordinatesSerializer(serializers.ModelSerializer):
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6, allow_null=True, required=True)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6, allow_null=True, required=True)

    class Meta:
        model = Ward
        fields = ["id", "name", "kind", "latitude", "longitude", "coord_confidence", "coord_source"]
        read_only_fields = ["id", "name", "kind", "coord_confidence", "coord_source"]
