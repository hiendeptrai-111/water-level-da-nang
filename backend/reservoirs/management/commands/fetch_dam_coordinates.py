"""Dam coordinates of the 4 reservoirs from OpenStreetMap (© OpenStreetMap contributors, ODbL).

One Overpass query (cached in kho_du_lieu/osm/overpass_dams.json; --refresh to download
again): waterway=dam objects inside the Da Nang city relation named "Đập thủy điện <hồ>".
A reservoir without such a dam gets the approximate coordinates below and is flagged
coord_needs_verification, for an admin to check. Writes data/dam_coordinates.csv.
"""
import csv
import json
import unicodedata
import urllib.parse
import urllib.request

from django.conf import settings
from django.core.management.base import BaseCommand

from catalog import geo
from reservoirs.management.commands.load_reservoirs import RESERVOIRS

OVERPASS = "https://overpass-api.de/api/interpreter"
QUERY = ('[out:json][timeout:120];area(3601891418)->.dn;'
         'nwr(area.dn)["waterway"="dam"]["name"];out center tags;')
SOURCE = "OpenStreetMap (© OpenStreetMap contributors, ODbL)"
# Approximate dam positions given by the project owner, used only when OSM has no dam.
APPROXIMATE = {"av": (15.80028, 107.61667), "sb": (15.72, 107.52), "dm": (15.42, 107.87),
               "st": (15.34, 108.10)}
OUT = settings.BASE_DIR / "data" / "dam_coordinates.csv"


def norm(text):
    t = unicodedata.normalize("NFC", text or "").lower().strip()
    return t.replace("thuỷ", "thủy")


class Command(BaseCommand):
    help = "Lấy tọa độ 4 đập từ OpenStreetMap (Overpass), ghi data/dam_coordinates.csv"

    def add_arguments(self, parser):
        parser.add_argument("--refresh", action="store_true")

    def handle(self, *args, **opts):
        cache = settings.DATA_STORE_DIR / "osm" / "overpass_dams.json"
        if opts["refresh"] or not cache.exists():
            req = urllib.request.Request(OVERPASS, data=urllib.parse.urlencode({"data": QUERY}).encode(),
                                         headers={"User-Agent": settings.HTTP_USER_AGENT})
            with urllib.request.urlopen(req, timeout=180) as r:
                body = r.read().decode("utf-8")
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(body, encoding="utf-8")
        dams = json.loads(cache.read_text(encoding="utf-8"))["elements"]
        rows = []
        for code, _key, name, _mndbt, _order in RESERVOIRS:
            wanted = norm(f"Đập thủy điện {name}")
            found = [d for d in dams if norm(d["tags"].get("name")) == wanted]
            row = {"code": code, "name": name}
            if len(found) == 1:
                d = found[0]
                c = d.get("center") or {"lat": d["lat"], "lon": d["lon"]}
                if geo.in_da_nang(c["lat"], c["lon"]):
                    row.update(latitude=round(c["lat"], 6), longitude=round(c["lon"], 6),
                               source=f"{SOURCE}, {d['type']} {d['id']} «{d['tags']['name']}»",
                               needs_verification=0)
                    rows.append(row)
                    continue
            lat, lon = APPROXIMATE[code]
            reason = "nhiều đối tượng cùng tên" if len(found) > 1 else "không có đối tượng đập cùng tên trên OSM"
            row.update(latitude=lat, longitude=lon, needs_verification=1,
                       source=f"Tọa độ gần đúng do chủ dự án cung cấp ({reason}) – cần xác minh")
            rows.append(row)
        with open(OUT, "w", encoding="utf-8", newline="") as f:
            f.write(f"# Tọa độ đập. Nguồn: {SOURCE} (Overpass), hoặc tọa độ gần đúng cần xác minh\n")
            w = csv.DictWriter(f, fieldnames=["code", "name", "latitude", "longitude", "source",
                                              "needs_verification"])
            w.writeheader()
            w.writerows(rows)
        for r in rows:
            self.stdout.write(f"  {r['name']}: {r['latitude']}, {r['longitude']} – {r['source']}")
        self.stdout.write(self.style.SUCCESS(f"Đã ghi {OUT.name}"))
