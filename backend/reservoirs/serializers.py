from rest_framework import serializers

from .models import OperatingDirective, RegulatoryThreshold, Reservoir


class ThresholdSerializer(serializers.ModelSerializer):
    reservoir_code = serializers.CharField(source="reservoir.code", read_only=True)
    reservoir_name = serializers.CharField(source="reservoir.name", read_only=True)
    kind_label = serializers.CharField(source="get_kind_display", read_only=True)

    class Meta:
        model = RegulatoryThreshold
        fields = ["id", "reservoir_code", "reservoir_name", "kind", "kind_label", "start_day",
                  "end_day", "value_low", "value_high", "document", "updated_at"]
        read_only_fields = ["id", "kind", "updated_at"]

    def validate(self, attrs):
        low = attrs.get("value_low", getattr(self.instance, "value_low", None))
        high = attrs.get("value_high", getattr(self.instance, "value_high", None))
        if low is not None and high is not None and low > high:
            raise serializers.ValidationError({"value_high": "Giá trị cao phải ≥ giá trị thấp."})
        return attrs


class DirectiveSerializer(serializers.ModelSerializer):
    """Admin view: includes who entered / deactivated the directive."""
    reservoir = serializers.SlugRelatedField(slug_field="code", queryset=Reservoir.objects.all())
    reservoir_name = serializers.CharField(source="reservoir.name", read_only=True)
    requirement = serializers.ChoiceField(choices=OperatingDirective.Requirement.choices)
    requirement_label = serializers.SerializerMethodField()
    entered_by = serializers.StringRelatedField()
    deactivated_by = serializers.StringRelatedField()

    class Meta:
        model = OperatingDirective
        fields = ["id", "reservoir", "reservoir_name", "requirement", "requirement_label",
                  "target_level", "starts_at", "deadline", "document", "is_active",
                  "entered_by", "created_at", "deactivated_at", "deactivated_by"]
        read_only_fields = ["id", "is_active", "entered_by", "created_at", "deactivated_at",
                            "deactivated_by"]
        extra_kwargs = {"document": {"allow_blank": False}}

    def get_requirement_label(self, obj):
        return obj.get_requirement_display() or "Không ghi rõ"

    def validate(self, attrs):
        start, deadline = attrs.get("starts_at"), attrs.get("deadline")
        if start and deadline and deadline < start:
            raise serializers.ValidationError({"deadline": "Hạn hoàn thành phải sau thời điểm bắt đầu."})
        return attrs
