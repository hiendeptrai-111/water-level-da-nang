"""Travel time of rescue teams to an SOS (CN18): OSMnx road graph + NetworkX Dijkstra.

Road network: OpenStreetMap (© OpenStreetMap contributors, ODbL), downloaded once with
OSMnx (network_type="drive", Overpass) for the Appendix B communes and the team bases, saved
as GraphML in kho_du_lieu/roads/ and reused.

Edge weight = length / speed of the road type (SPEED_KMH below: ASSUMPTIONS of the project,
not measured speeds). Approved flood points change the weights of the edges within
flood_point_radius_m of them, without copying the graph:
  - "no_motorbike" (xe máy không qua được): time × flood_slowdown_factor;
  - "no_car" (ô tô không qua được) and "boat_only" (chỉ ca nô): edge removed for road teams;
  - "passable": no change.
Boat teams: straight-line distance / boat speed (simplification, see README limitations).
"""
import math
import threading
from dataclasses import dataclass

import networkx as nx
import numpy as np
from django.conf import settings

# Speed by OSM highway type, km/h — ASSUMPTION of the project (mountain and rural roads of
# the Vu Gia – Thu Bồn basin during floods), not measured.
SPEED_KMH = {
    "motorway": 80, "motorway_link": 40,
    "trunk": 60, "trunk_link": 35,
    "primary": 50, "primary_link": 30,
    "secondary": 40, "secondary_link": 25,
    "tertiary": 35, "tertiary_link": 20,
    "unclassified": 25, "residential": 20, "living_street": 10, "road": 20,
}
DEFAULT_SPEED_KMH = 20
EARTH_R = 6_371_000.0
GRAPH_NAME = "drive_appendix_b.graphml"

_lock = threading.Lock()
_graph = None


def graph_file():
    return settings.DATA_STORE_DIR / "roads" / GRAPH_NAME


def speed_for(highway):
    if isinstance(highway, list):
        return max(SPEED_KMH.get(h, DEFAULT_SPEED_KMH) for h in highway)
    return SPEED_KMH.get(highway, DEFAULT_SPEED_KMH)


def add_travel_times(G):
    """Edge attribute 'tt' = seconds = length (m) / speed (m/s)."""
    for _u, _v, d in G.edges(data=True):
        d["tt"] = float(d["length"]) / (speed_for(d.get("highway")) / 3.6)
    return G


def haversine_m(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 2 * EARTH_R * math.asin(math.sqrt(a))


# ---------------------------------------------------------------- graph loading
class RoadGraph:
    """The graph plus numpy arrays for nearest-node and edge-near-point lookups."""

    def __init__(self, G):
        self.G = G
        self.R = G.reverse(copy=False)
        self.nodes = list(G.nodes)
        self.lat = np.array([G.nodes[n]["y"] for n in self.nodes], dtype=float)
        self.lon = np.array([G.nodes[n]["x"] for n in self.nodes], dtype=float)
        self.index = {n: i for i, n in enumerate(self.nodes)}
        self.edges = [(u, v, k) for u, v, k in G.edges(keys=True)]
        ia = np.array([self.index[u] for u, _, _ in self.edges])
        ib = np.array([self.index[v] for _, v, _ in self.edges])
        self.e_lat1, self.e_lon1 = self.lat[ia], self.lon[ia]
        self.e_lat2, self.e_lon2 = self.lat[ib], self.lon[ib]

    def nearest_node(self, lat, lon):
        """Nearest node and its straight distance (m) (equirectangular, fine at this scale)."""
        k = math.cos(math.radians(lat))
        d2 = ((self.lat - lat) ** 2 + ((self.lon - lon) * k) ** 2)
        i = int(np.argmin(d2))
        return self.nodes[i], haversine_m(lat, lon, self.lat[i], self.lon[i])

    def edges_near(self, lat, lon, radius_m):
        """Edges whose straight segment passes within radius_m of the point."""
        k = math.cos(math.radians(lat))
        m = 111_320.0                                    # metres per degree of latitude
        ax, ay = (self.e_lon1 - lon) * k * m, (self.e_lat1 - lat) * m
        bx, by = (self.e_lon2 - lon) * k * m, (self.e_lat2 - lat) * m
        dx, dy = bx - ax, by - ay
        L2 = dx * dx + dy * dy
        t = np.clip(np.where(L2 > 0, -(ax * dx + ay * dy) / np.where(L2 > 0, L2, 1), 0), 0, 1)
        px, py = ax + t * dx, ay + t * dy
        hit = np.nonzero(px * px + py * py <= radius_m * radius_m)[0]
        return {self.edges[i] for i in hit}


def load_graph():
    """The road graph (loaded once per process). Raises FileNotFoundError when missing."""
    global _graph
    with _lock:
        if _graph is None:
            import osmnx as ox
            path = graph_file()
            if not path.exists():
                raise FileNotFoundError(f"Chưa có mạng đường {path}. Chạy: python manage.py fetch_road_network")
            G = ox.load_graphml(path, edge_dtypes={"tt": float, "length": float})
            _graph = RoadGraph(G)
        return _graph


def set_graph(G):
    """Use an in-memory graph (tests: small hand-built graphs)."""
    global _graph
    with _lock:
        _graph = RoadGraph(add_travel_times(G)) if G is not None else None


# ---------------------------------------------------------------- flood points -> weights
@dataclass
class Flood:
    lat: float
    lon: float
    level: str             # passable / no_motorbike / no_car / boat_only


def flood_effects(rg, floods, radius_m, slowdown):
    """{edge key: factor or None (blocked)} for the approved flood points."""
    effects = {}
    for f in floods:
        if f.level == "passable":
            continue
        for e in rg.edges_near(f.lat, f.lon, radius_m):
            if f.level in ("no_car", "boat_only"):
                effects[e] = None
            elif effects.get(e, 1.0) is not None:
                effects[e] = max(effects.get(e, 1.0), slowdown)
    return effects


def weight_fn(effects, reverse):
    """Dijkstra weight on the (reversed) MultiDiGraph: min over parallel edges, None = blocked."""
    def w(u, v, data):
        best = None
        for k, d in data.items():
            key = (v, u, k) if reverse else (u, v, k)
            factor = effects.get(key, 1.0)
            if factor is None:
                continue
            t = d["tt"] * factor
            best = t if best is None or t < best else best
        return best
    return w


# ---------------------------------------------------------------- travel times
ACCESS_SPEED_KMH = 15          # walking/riding from the exact point to the nearest road node


@dataclass
class Route:
    team_id: int
    mode: str                  # "road" / "boat" / "none"
    seconds: float | None
    path: list | None          # [[lat, lon], ...] (road) or [[from], [to]] (boat)
    note: str = ""


def road_times(rg, target, starts, effects):
    """One Dijkstra from the SOS on the reversed graph: travel time from every start.
    target = (lat, lon); starts = {team_id: (lat, lon)}. Returns {team_id: (seconds, path)}."""
    t_node, t_off = rg.nearest_node(*target)
    dist, paths = nx.single_source_dijkstra(rg.R, t_node, weight=weight_fn(effects, reverse=True))
    out = {}
    for team_id, (lat, lon) in starts.items():
        s_node, s_off = rg.nearest_node(lat, lon)
        if s_node not in dist:
            out[team_id] = (None, None)
            continue
        access = (s_off + t_off) / (ACCESS_SPEED_KMH / 3.6)
        nodes = list(reversed(paths[s_node]))
        out[team_id] = (dist[s_node] + access,
                        [[rg.G.nodes[n]["y"], rg.G.nodes[n]["x"]] for n in nodes])
    return out


def boat_time(start, target, speed_kmh):
    d = haversine_m(*start, *target)
    return d / (speed_kmh / 3.6)
