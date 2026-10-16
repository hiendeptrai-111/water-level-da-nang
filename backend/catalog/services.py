"""Ward coordinates: validation (inside Da Nang) and audited manual edits (CN25)."""
from decimal import Decimal

from django.core.exceptions import ValidationError

from core.models import AuditLog
from core.services import audit

from . import geo
from .models import Ward


def check_in_da_nang(lat, lon):
    if (lat is None) != (lon is None):
        raise ValidationError("Nhập đủ cả vĩ độ và kinh độ, hoặc để trống cả hai.")
    if lat is not None and not geo.in_da_nang(lat, lon):
        raise ValidationError("Tọa độ nằm ngoài ranh giới TP Đà Nẵng.")


def set_coordinates_manually(ward, lat, lon, *, actor, request=None, via):
    """Admin edit: validated, marked 'manual' (kept by load_ward_centroids), logged."""
    check_in_da_nang(lat, lon)
    old = [str(ward.latitude), str(ward.longitude), ward.coord_confidence]
    ward.latitude = Decimal(str(lat)) if lat is not None else None
    ward.longitude = Decimal(str(lon)) if lon is not None else None
    ward.coord_confidence = Ward.Confidence.MANUAL if lat is not None else Ward.Confidence.MISSING
    ward.coord_source = f"Admin nhập ({actor})" if lat is not None else ""
    ward.save(update_fields=["latitude", "longitude", "coord_confidence", "coord_source"])
    audit(AuditLog.Action.WARD_COORDS_CHANGED, actor=actor, target=ward, request=request,
          details={"old": old, "new": [str(ward.latitude), str(ward.longitude),
                                       ward.coord_confidence], "via": via})
    return ward
