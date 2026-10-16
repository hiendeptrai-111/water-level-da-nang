"""Centre coordinates of the 94 units from OpenStreetMap (© OpenStreetMap contributors, ODbL),
through the Overpass API (3 queries in total; at most 1 request per second, a User-Agent
naming the project). Every raw response is saved in kho_du_lieu/osm/ and reused, so running
the command again does not call the server (--refresh to download again).

For each unit, by confidence:
  boundary     a post-01/07/2025 boundary (admin_level=6 inside the Da Nang city relation)
               whose name matches -> area-weighted centroid of that boundary;
  needs_check  only a point with the same name (place=* node) -> "cần kiểm tra";
  missing      nothing found -> left empty.
Any coordinate outside the Da Nang city boundary is dropped. Nothing is guessed.

Writes backend/data/ward_centroids.csv, ward_boundaries.geojson (polygons, for the CN14
map) and danang_boundary.geojson (city boundary, used for the inside-Da-Nang check).
"""
import csv
import json
import time
import unicodedata
import urllib.parse
import urllib.request

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from catalog import geo
from catalog.models import Ward

CITY_RELATION = 1891418            # "Thành phố Đà Nẵng", admin_level=4
OVERPASS = "https://overpass-api.de/api/interpreter"
PREFIX = {Ward.Kind.WARD: "Phường", Ward.Kind.COMMUNE: "Xã", Ward.Kind.SPECIAL_ZONE: "Đặc khu"}
SOURCE = "OpenStreetMap (© OpenStreetMap contributors, ODbL)"
DATA = settings.BASE_DIR / "data"
DIGITS = 5                          # ~1 m
MAP_TOLERANCE = 0.0002              # ~20 m: map outlines only (centroids use the full boundary)


def nfc(text):
    return unicodedata.normalize("NFC", text or "").strip()


def full_name(ward):
    return f"{PREFIX[ward.kind]} {ward.name}"


def rounded(geometry):
    def r(c):
        return [round(c[0], DIGITS), round(c[1], DIGITS)] if isinstance(c[0], (int, float)) else [r(x) for x in c]
    return {"type": geometry["type"], "coordinates": r(geometry["coordinates"])}


class Command(BaseCommand):
    help = "Lấy tọa độ trung tâm 94 phường/xã từ OpenStreetMap, ghi data/ward_centroids.csv"

    def add_arguments(self, parser):
        parser.add_argument("--refresh", action="store_true", help="tải lại thay vì dùng bản đã lưu")

    # ------------------------------------------------------------ HTTP with cache
    def fetch(self, name, url, data=None):
        cache = settings.DATA_STORE_DIR / "osm" / name
        if cache.exists() and not self.refresh:
            return json.loads(cache.read_text(encoding="utf-8"))
        wait = 1.1 - (time.monotonic() - self.last_call)
        if wait > 0:
            time.sleep(wait)                         # at most 1 request per second
        req = urllib.request.Request(url, data=data,
                                     headers={"User-Agent": settings.HTTP_USER_AGENT})
        with urllib.request.urlopen(req, timeout=180) as r:
            body = json.loads(r.read().decode("utf-8"))
        self.last_call = time.monotonic()
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(body, ensure_ascii=False), encoding="utf-8")
        return body

    def overpass(self, name, query):
        return self.fetch(name, OVERPASS, urllib.parse.urlencode({"data": query}).encode())["elements"]

    # ------------------------------------------------------------ main
    def handle(self, *args, **opts):
        self.refresh, self.last_call = opts["refresh"], 0.0
        wards = list(Ward.objects.order_by("kind", "name"))
        if len(wards) != 94:
            raise CommandError("Chưa nạp đủ 94 phường/xã. Chạy: python manage.py load_wards")

        area = f"area({3600000000 + CITY_RELATION})->.dn;"
        city = self.overpass("overpass_city.json", f"[out:json][timeout:180];rel({CITY_RELATION});out geom;")[0]
        city_geom = rounded(relation_geometry(city))
        (DATA / "danang_boundary.geojson").write_text(json.dumps({
            "type": "FeatureCollection", "attribution": SOURCE,
            "features": [{"type": "Feature", "properties": {"name": city["tags"]["name"],
                                                            "osm_id": f"R{CITY_RELATION}"},
                          "geometry": city_geom}]}, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8")
        geo.city_geometry.cache_clear()

        units = self.overpass("overpass_admin_level6.json", f"[out:json][timeout:300];{area}"
                              'rel(area.dn)["boundary"="administrative"]["admin_level"="6"];out geom;')
        by_name = {}
        for u in units:
            by_name.setdefault(nfc(u["tags"].get("name")), []).append(u)
        places = self.overpass("overpass_places.json", f"[out:json][timeout:180];{area}"
                               'node(area.dn)["place"]["name"];out;')

        rows, features = [], []
        for w in wards:
            row = {"kind": w.kind, "name": w.name, "latitude": "", "longitude": "", "source": "",
                   "confidence": "missing", "osm_id": "", "note": ""}
            found = by_name.get(full_name(w), [])
            geometry = None
            if len(found) == 1:
                try:
                    geometry = relation_geometry(found[0])
                except ValueError as e:
                    row["note"] = f"ranh giới R{found[0]['id']} không ghép được: {e}"
            if geometry:
                rel = found[0]["id"]
                lat, lon = geo.centroid(geometry)
                note = "trọng tâm diện tích của ranh giới"
                if not geo.contains(geometry, lat, lon):     # concave shape: use the label point
                    label = next((m for m in found[0]["members"] if m.get("role") in ("label", "admin_centre")
                                  and m["type"] == "node"), None)
                    if label and geo.contains(geometry, label["lat"], label["lon"]):
                        lat, lon, note = label["lat"], label["lon"], \
                            f"trọng tâm nằm ngoài ranh giới, dùng điểm {label['role']} của relation"
                    else:
                        row["note"] = f"trọng tâm R{rel} nằm ngoài ranh giới và không có điểm nhãn"
                        geometry = None
                if geometry and geo.in_da_nang(lat, lon):
                    row.update(latitude=round(lat, 6), longitude=round(lon, 6), confidence="boundary",
                               source=f"{SOURCE}, relation {rel}", osm_id=f"R{rel}", note=note)
                    features.append({"type": "Feature", "geometry": rounded(geo.simplify(geometry, MAP_TOLERANCE)),
                                      "properties": {"kind": w.kind, "name": w.name, "osm_id": f"R{rel}"}})
                elif geometry:
                    row["note"] = f"tâm ranh giới R{rel} nằm ngoài TP Đà Nẵng: bỏ"
            if row["confidence"] == "missing":
                if len(found) > 1:
                    row["note"] = f"{len(found)} ranh giới OSM cùng tên"
                self.search_point(w, row, places)
            rows.append(row)

        with open(DATA / "ward_centroids.csv", "w", encoding="utf-8", newline="") as f:
            f.write(f"# Tọa độ trung tâm 94 đơn vị. Nguồn: {SOURCE}, lấy ngày {time.strftime('%d/%m/%Y')}\n"
                    "# confidence: boundary = tâm ranh giới mới (admin_level=6) khớp tên; needs_check = chỉ có "
                    "điểm cùng tên, cần kiểm tra; missing = không tìm được (để trống)\n")
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        (DATA / "ward_boundaries.geojson").write_text(json.dumps(
            {"type": "FeatureCollection", "attribution": SOURCE, "features": features},
            ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

        counts = {c: sum(r["confidence"] == c for r in rows) for c in ("boundary", "needs_check", "missing")}
        self.stdout.write(f"Kết quả: {counts}. Đã ghi data/ward_centroids.csv, ward_boundaries.geojson "
                          f"({len(features)} ranh giới), danang_boundary.geojson")
        unused = sorted(n for n, v in by_name.items() if not any(full_name(w) == n for w in wards))
        if unused:
            self.stdout.write(f"Ranh giới OSM không khớp tên đơn vị nào: {unused}")
        for r in rows:
            if r["confidence"] != "boundary":
                self.stdout.write(f"  {r['confidence']:<11} {PREFIX[r['kind']]} {r['name']}: {r['note']}")

    def search_point(self, ward, row, places):
        """Only a point with the same name: kept as 'needs_check' when inside Da Nang."""
        same = [p for p in places if nfc(p["tags"].get("name")) in (ward.name, full_name(ward))]
        for p in same:
            if not geo.in_da_nang(p["lat"], p["lon"]):
                row["note"] = (row["note"] + "; " if row["note"] else "") + \
                    f"điểm cùng tên node {p['id']} nằm ngoài TP Đà Nẵng: bỏ"
                continue
            row.update(latitude=round(p["lat"], 6), longitude=round(p["lon"], 6), confidence="needs_check",
                       source=f"{SOURCE}, node {p['id']} (place={p['tags'].get('place')})",
                       osm_id=f"N{p['id']}",
                       note=(f"{len(same)} điểm cùng tên, lấy điểm đầu; " if len(same) > 1 else "")
                       + "chỉ tìm được điểm cùng tên, chưa có ranh giới mới: cần kiểm tra")
            return
        if not row["note"]:
            row["note"] = "không tìm được trên OpenStreetMap"


def relation_geometry(rel):
    """Overpass 'out geom' relation -> GeoJSON Polygon/MultiPolygon (ways joined into rings)."""
    def rings(role):
        ways = [[(round(p["lon"], 7), round(p["lat"], 7)) for p in m["geometry"]]
                for m in rel["members"] if m["type"] == "way" and m.get("role", "outer") == role
                and m.get("geometry")]
        out = []
        while ways:
            ring = list(ways.pop(0))
            while ring[0] != ring[-1]:
                for i, w in enumerate(ways):
                    if w[0] == ring[-1]:
                        ring += w[1:]
                    elif w[-1] == ring[-1]:
                        ring += w[::-1][1:]
                    else:
                        continue
                    ways.pop(i)
                    break
                else:
                    raise ValueError(f"vòng '{role}' không khép kín")
            out.append([list(p) for p in ring])
        return out

    outers, inners = rings("outer"), rings("inner")
    if not outers:
        raise ValueError("không có vòng ngoài")
    polygons = [[o] for o in outers]
    for hole in inners:
        x, y = hole[0]
        for poly in polygons:
            if geo.contains({"type": "Polygon", "coordinates": [poly[0]]}, y, x):
                poly.append(hole)
                break
    if len(polygons) == 1:
        return {"type": "Polygon", "coordinates": polygons[0]}
    return {"type": "MultiPolygon", "coordinates": polygons}
