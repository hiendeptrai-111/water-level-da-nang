"""Build the drivable road graph (OpenStreetMap, © OpenStreetMap contributors, ODbL) once.

The public Overpass API refuses automated high-volume downloads, so the source is the
Geofabrik extract of Vietnam (download.geofabrik.de/asia/vietnam-latest.osm.pbf), saved in
kho_du_lieu/osm/. osmium-tool cuts the area (bounding box of the Appendix B communes and the
team bases, + ~2 km) and keeps the roads usable by cars and motorbikes (the highway types of
routing.SPEED_KMH, without access=private/no, motor_vehicle=no, motorcar=no). OSMnx then builds
the graph, cut to the exact area, and saves kho_du_lieu/roads/drive_appendix_b.graphml with the
travel time of each edge. Running again reuses the GraphML (--refresh to rebuild).
"""
import json
import shutil
import subprocess
import time
import urllib.request

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from catalog.models import RescueTeam
from rescue import routing
from reservoirs.models import ReservoirWard

BUFFER_DEG = 0.02          # ~2 km
GEOFABRIK = "https://download.geofabrik.de/asia/vietnam-latest.osm.pbf"


def run(*args):
    subprocess.run(args, check=True, capture_output=True, text=True)


class Command(BaseCommand):
    help = "Dựng mạng đường cho xe (OSMnx) quanh các xã Phụ lục B và căn cứ các đội từ file Geofabrik"

    def add_arguments(self, parser):
        parser.add_argument("--refresh", action="store_true", help="dựng lại từ file .pbf")
        parser.add_argument("--pbf", help="file .osm.pbf (mặc định: file vietnam-*.osm.pbf mới nhất trong kho_du_lieu/osm/)")
        parser.add_argument("--download", action="store_true", help="tải file Geofabrik mới nhất nếu chưa có")

    def handle(self, *args, **opts):
        import osmnx as ox
        from shapely.geometry import Point, shape
        from shapely.ops import unary_union

        path = routing.graph_file()
        if path.exists() and not opts["refresh"]:
            self.stdout.write(f"Đã có {path}, không dựng lại.")
            self.report(path, 0.0)
            return
        osm_dir = settings.DATA_STORE_DIR / "osm"
        pbf = opts["pbf"] or next(iter(sorted(osm_dir.glob("vietnam-*.osm.pbf"), reverse=True)), None)
        if pbf is None and opts["download"]:
            pbf = osm_dir / "vietnam-latest.osm.pbf"
            req = urllib.request.Request(GEOFABRIK, headers={"User-Agent": settings.HTTP_USER_AGENT})
            with urllib.request.urlopen(req, timeout=1800) as r, open(pbf, "wb") as f:
                shutil.copyfileobj(r, f)
        if pbf is None:
            raise CommandError(f"Chưa có file .osm.pbf trong {osm_dir}. Tải {GEOFABRIK} hoặc chạy với --download.")
        if shutil.which("osmium") is None:
            raise CommandError("Cần osmium-tool (macOS: brew install osmium-tool).")

        names = {(link.ward.kind, link.ward.name) for link in ReservoirWard.objects.select_related("ward")}
        if not names:
            raise CommandError("Chưa có liên kết Phụ lục B. Chạy load_reservoirs trước.")
        shapes = json.loads((settings.BASE_DIR / "data" / "ward_boundaries.geojson").read_text(encoding="utf-8"))
        parts = [shape(f["geometry"]) for f in shapes["features"]
                 if (f["properties"]["kind"], f["properties"]["name"]) in names]
        bases = [Point(float(t.base_longitude), float(t.base_latitude)) for t in RescueTeam.objects.all()
                 if t.base_latitude is not None and t.base_longitude is not None]
        area = unary_union(parts + [b.buffer(0.01) for b in bases]).buffer(BUFFER_DEG)
        w, s, e, n = area.bounds
        self.stdout.write(f"Nguồn: {pbf.name}. Vùng: {len(parts)} phường/xã Phụ lục B + {len(bases)} căn cứ đội, "
                          f"bbox {w:.3f},{s:.3f} → {e:.3f},{n:.3f}")

        started = time.monotonic()
        work = settings.DATA_STORE_DIR / "roads" / "build"
        work.mkdir(parents=True, exist_ok=True)
        region, roads, drivable, xml = (work / f for f in ("region.osm.pbf", "roads.osm.pbf",
                                                           "drivable.osm.pbf", "drivable.osm"))
        run("osmium", "extract", "-b", f"{w},{s},{e},{n}", "--strategy=complete_ways", "--overwrite",
            "-o", str(region), str(pbf))
        run("osmium", "tags-filter", "--overwrite", "-o", str(roads), str(region),
            "w/highway=" + ",".join(routing.SPEED_KMH))
        run("osmium", "tags-filter", "--overwrite", "-i", "-o", str(drivable), str(roads),
            "w/access=private,no", "w/motor_vehicle=no", "w/motorcar=no")
        run("osmium", "cat", "--overwrite", "-o", str(xml), str(drivable))

        G = ox.graph_from_xml(xml, simplify=True, retain_all=False)
        G = ox.truncate.truncate_graph_polygon(G, area, truncate_by_edge=True)
        G = ox.truncate.largest_component(G, strongly=False)
        routing.add_travel_times(G)
        G.graph["source"] = f"OpenStreetMap via Geofabrik {pbf.name} (ODbL)"
        ox.save_graphml(G, path)
        shutil.rmtree(work, ignore_errors=True)
        routing.set_graph(None)
        self.report(path, time.monotonic() - started)

    def report(self, path, seconds):
        rg = routing.load_graph()
        self.stdout.write(self.style.SUCCESS(
            f"Mạng đường: {rg.G.number_of_nodes():,} nút, {rg.G.number_of_edges():,} cạnh, "
            f"{path.stat().st_size / 1e6:.1f} MB" + (f", dựng trong {seconds:.0f} giây" if seconds else "")))
