from django.conf import settings
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.cache import cache_control
from rest_framework import serializers
from rest_framework.response import Response

from catalog.models import Ward
from reservoirs.views import PublicView

from .services import map_values, ward_weather

DISCLAIMER = ("Thông tin tham khảo từ mô hình thời tiết Open-Meteo, không phải cảnh báo chính thức. "
              "Theo dõi thông báo của cơ quan khí tượng và chính quyền địa phương.")


class WardWeatherView(PublicView):
    """GET /api/weather/wards/<id>/ (CN13)."""

    def get(self, request, pk):
        ward = get_object_or_404(Ward, pk=pk)
        return Response({**ward_weather(ward), "disclaimer": DISCLAIMER})


class WeatherMapView(PublicView):
    """GET /api/weather/map/?metric=past24h|next24h (CN14)."""

    def get(self, request):
        metric = request.query_params.get("metric", "past24h")
        if metric not in ("past24h", "next24h"):
            raise serializers.ValidationError({"metric": "Chỉ nhận past24h hoặc next24h."})
        return Response({**map_values(metric), "disclaimer": DISCLAIMER})


@cache_control(public=True, max_age=86400)
def ward_boundaries(request):
    """GeoJSON of the commune boundaries (OpenStreetMap, ODbL) for the CN14 map."""
    path = settings.BASE_DIR / "data" / "ward_boundaries.geojson"
    return FileResponse(open(path, "rb"), content_type="application/geo+json")
