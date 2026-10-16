"""Small GeoJSON helpers (no GIS dependency): area-weighted centroid, point in polygon,
and the Da Nang city boundary used to reject coordinates outside the city."""
import json
from functools import lru_cache

from django.conf import settings

CITY_BOUNDARY_FILE = settings.BASE_DIR / "data" / "danang_boundary.geojson"


def _polygons(geometry):
    """GeoJSON Polygon / MultiPolygon -> list of polygons, each a list of rings [[lon, lat], ...]."""
    if geometry["type"] == "Polygon":
        return [geometry["coordinates"]]
    if geometry["type"] == "MultiPolygon":
        return geometry["coordinates"]
    raise ValueError(f"Không hỗ trợ hình học {geometry['type']}")


def _ring_area_centroid(ring):
    a = cx = cy = 0.0
    for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]):
        cross = x1 * y2 - x2 * y1
        a += cross
        cx += (x1 + x2) * cross
        cy += (y1 + y2) * cross
    a /= 2
    if a == 0:
        return 0.0, ring[0][0], ring[0][1]
    return a, cx / (6 * a), cy / (6 * a)


def centroid(geometry):
    """Area-weighted centroid (lat, lon) of a Polygon/MultiPolygon; holes subtract."""
    total = sx = sy = 0.0
    for polygon in _polygons(geometry):
        for i, ring in enumerate(polygon):
            a, x, y = _ring_area_centroid([tuple(p[:2]) for p in ring])
            a = abs(a) if i == 0 else -abs(a)          # outer ring adds, holes subtract
            total += a
            sx += a * x
            sy += a * y
    if total == 0:
        raise ValueError("Đa giác có diện tích bằng 0")
    return sy / total, sx / total


def _in_ring(lon, lat, ring):
    inside = False
    for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]):
        if (y1 > lat) != (y2 > lat) and lon < (x2 - x1) * (lat - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


def contains(geometry, lat, lon):
    for polygon in _polygons(geometry):
        rings = [[tuple(p[:2]) for p in r] for r in polygon]
        if _in_ring(lon, lat, rings[0]) and not any(_in_ring(lon, lat, h) for h in rings[1:]):
            return True
    return False


@lru_cache(maxsize=1)
def city_geometry():
    return json.loads(CITY_BOUNDARY_FILE.read_text(encoding="utf-8"))["features"][0]["geometry"]


def in_da_nang(lat, lon):
    """True when (lat, lon) lies inside the Da Nang city boundary (OpenStreetMap)."""
    if lat is None or lon is None:
        return False
    return contains(city_geometry(), float(lat), float(lon))


def _rdp(points, tol):
    """Douglas–Peucker on a list of (x, y)."""
    if len(points) < 3:
        return points
    (x1, y1), (x2, y2) = points[0], points[-1]
    dx, dy = x2 - x1, y2 - y1
    norm = (dx * dx + dy * dy) ** 0.5
    best, index = 0.0, 0
    for i, (x, y) in enumerate(points[1:-1], 1):
        d = abs(dy * x - dx * y + x2 * y1 - y2 * x1) / norm if norm else ((x - x1) ** 2 + (y - y1) ** 2) ** 0.5
        if d > best:
            best, index = d, i
    if best <= tol:
        return [points[0], points[-1]]
    return _rdp(points[:index + 1], tol)[:-1] + _rdp(points[index:], tol)


def simplify(geometry, tol):
    """Simplify every ring (kept closed, at least 4 points) for drawing a map."""
    def ring(r):
        out = _rdp([tuple(p) for p in r[:-1]], tol) + [tuple(r[0])]
        return [list(p) for p in out] if len(out) >= 4 else r
    polygons = [[ring(r) for r in poly] for poly in _polygons(geometry)]
    if geometry["type"] == "Polygon":
        return {"type": "Polygon", "coordinates": polygons[0]}
    return {"type": "MultiPolygon", "coordinates": polygons}
