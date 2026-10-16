import unicodedata

from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from rest_framework import generics, serializers
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny

from accounts.permissions import IsAdminRole

from .models import RescueTeam, Ward
from .serializers import RescueTeamSerializer, WardCoordinatesSerializer, WardSerializer
from .services import set_coordinates_manually


def fold(text):
    """Lower-case and strip Vietnamese diacritics: "Hội An" -> "hoi an"."""
    text = unicodedata.normalize("NFD", text or "").replace("đ", "d").replace("Đ", "D")
    return "".join(c for c in text if not unicodedata.combining(c)).lower().strip()


class WardListView(generics.ListAPIView):
    """Public list of the 94 units, downstream communes first. ?search= filters by name,
    ignoring case and diacritics ("dai loc" finds "Đại Lộc")."""
    serializer_class = WardSerializer
    permission_classes = [AllowAny]
    authentication_classes = []
    pagination_class = None

    def get_queryset(self):
        wards = list(Ward.objects.all())
        q = fold(self.request.query_params.get("search", ""))
        if q:
            wards = [w for w in wards if q in fold(str(w))]
        return wards


class RescueTeamListView(generics.ListAPIView):
    """Admin-only list used to attach rescue accounts to a team (full CRUD in phase 4)."""
    serializer_class = RescueTeamSerializer
    permission_classes = [IsAdminRole]
    pagination_class = None
    queryset = RescueTeam.objects.all()


class AdminWardCoordinatesView(APIView):
    """PATCH /api/admin/wards/<id>/ {latitude, longitude}: admin only, inside Da Nang, logged."""
    permission_classes = [IsAdminRole]

    def patch(self, request, pk):
        ward = get_object_or_404(Ward, pk=pk)
        data = WardCoordinatesSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        try:
            set_coordinates_manually(ward, data.validated_data.get("latitude"),
                                     data.validated_data.get("longitude"), actor=request.user,
                                     request=request, via="api")
        except ValidationError as e:
            raise serializers.ValidationError({"latitude": e.messages}) from e
        return Response(WardCoordinatesSerializer(ward).data)
