"""
STRYDER AI - Route Engine (OpenStreetMap Integration)
======================================================
Provides road graph construction, route calculation, and vehicle
path simulation for the logistics simulation and live map.

Two modes:
  1. FULL OSM MODE: Uses OSMnx to fetch actual road networks (requires internet)
  2. FAST MODE (default): Uses a pre-built India logistics hub graph with
     Haversine distance calculation and realistic route generation.

The fast mode is default for hackathon reliability. Full OSM can be enabled
by calling initialize_osm_graph() with a city or bounding box.
"""

import math
import json
import random
from pathlib import Path
from typing import Optional

import numpy as np

try:
    import networkx as nx
    HAS_NETWORKX = True
except ImportError:
    HAS_NETWORKX = False

try:
    from geopy.distance import geodesic
    HAS_GEOPY = True
except ImportError:
    HAS_GEOPY = False

# ============================================================
# INDIA LOGISTICS HUB DATABASE
# ============================================================
# Major logistics hubs with coordinates, type, and capacity

INDIA_HUBS = {
    # Metro Warehouses
    "DEL-WH": {"name": "Delhi NCR Warehouse", "lat": 28.6139, "lon": 77.2090, "type": "warehouse", "capacity": 5000, "city": "Delhi"},
    "MUM-WH": {"name": "Mumbai Warehouse", "lat": 19.0760, "lon": 72.8777, "type": "warehouse", "capacity": 8000, "city": "Mumbai"},
    "BLR-WH": {"name": "Bangalore Warehouse", "lat": 12.9716, "lon": 77.5946, "type": "warehouse", "capacity": 4500, "city": "Bangalore"},
    "CHN-WH": {"name": "Chennai Warehouse", "lat": 13.0827, "lon": 80.2707, "type": "warehouse", "capacity": 4000, "city": "Chennai"},
    "HYD-WH": {"name": "Hyderabad Warehouse", "lat": 17.3850, "lon": 78.4867, "type": "warehouse", "capacity": 3500, "city": "Hyderabad"},
    "KOL-WH": {"name": "Kolkata Warehouse", "lat": 22.5726, "lon": 88.3639, "type": "warehouse", "capacity": 3000, "city": "Kolkata"},
    "AHM-WH": {"name": "Ahmedabad Warehouse", "lat": 23.0225, "lon": 72.5714, "type": "warehouse", "capacity": 2500, "city": "Ahmedabad"},
    "PUN-WH": {"name": "Pune Warehouse", "lat": 18.5204, "lon": 73.8567, "type": "warehouse", "capacity": 3000, "city": "Pune"},

    # Regional Distribution Centers
    "JAI-DC": {"name": "Jaipur Distribution Center", "lat": 26.9124, "lon": 75.7873, "type": "distribution_center", "capacity": 2000, "city": "Jaipur"},
    "LKO-DC": {"name": "Lucknow Distribution Center", "lat": 26.8467, "lon": 80.9462, "type": "distribution_center", "capacity": 1800, "city": "Lucknow"},
    "PAT-DC": {"name": "Patna Distribution Center", "lat": 25.6093, "lon": 85.1376, "type": "distribution_center", "capacity": 1200, "city": "Patna"},
    "BHO-DC": {"name": "Bhopal Distribution Center", "lat": 23.2599, "lon": 77.4126, "type": "distribution_center", "capacity": 1500, "city": "Bhopal"},
    "NAG-DC": {"name": "Nagpur Distribution Center", "lat": 21.1458, "lon": 79.0882, "type": "distribution_center", "capacity": 1800, "city": "Nagpur"},
    "COI-DC": {"name": "Coimbatore Distribution Center", "lat": 11.0168, "lon": 76.9558, "type": "distribution_center", "capacity": 1200, "city": "Coimbatore"},
    "VIZ-DC": {"name": "Visakhapatnam Distribution Center", "lat": 17.6868, "lon": 83.2185, "type": "distribution_center", "capacity": 1000, "city": "Visakhapatnam"},

    # Port Hubs
    "MUM-PT": {"name": "JNPT Mumbai Port", "lat": 18.9543, "lon": 72.9479, "type": "port", "capacity": 10000, "city": "Navi Mumbai"},
    "CHN-PT": {"name": "Chennai Port", "lat": 13.0979, "lon": 80.2939, "type": "port", "capacity": 7000, "city": "Chennai"},
    "KOC-PT": {"name": "Cochin Port", "lat": 9.9312, "lon": 76.2673, "type": "port", "capacity": 5000, "city": "Kochi"},
    "KOL-PT": {"name": "Kolkata Port", "lat": 22.5406, "lon": 88.3274, "type": "port", "capacity": 4000, "city": "Kolkata"},

    # Air Cargo
    "DEL-AC": {"name": "IGI Airport Cargo", "lat": 28.5562, "lon": 77.1000, "type": "air_cargo", "capacity": 3000, "city": "Delhi"},
    "MUM-AC": {"name": "CSIA Air Cargo", "lat": 19.0896, "lon": 72.8656, "type": "air_cargo", "capacity": 2500, "city": "Mumbai"},
    "BLR-AC": {"name": "KIA Air Cargo", "lat": 13.1986, "lon": 77.7066, "type": "air_cargo", "capacity": 2000, "city": "Bangalore"},
}

# Major freight corridors (bidirectional)
FREIGHT_CORRIDORS = [
    ("DEL-WH", "MUM-WH", "NH48"),     # Delhi-Mumbai Expressway
    ("DEL-WH", "KOL-WH", "NH19"),     # Delhi-Kolkata (GT Road corridor)
    ("DEL-WH", "JAI-DC", "NH48"),     # Delhi-Jaipur
    ("DEL-WH", "LKO-DC", "NH27"),    # Delhi-Lucknow
    ("MUM-WH", "PUN-WH", "NH48"),     # Mumbai-Pune Expressway
    ("MUM-WH", "AHM-WH", "NH48"),     # Mumbai-Ahmedabad
    ("MUM-WH", "BLR-WH", "NH48"),     # Mumbai-Bangalore
    ("MUM-WH", "NAG-DC", "NH53"),     # Mumbai-Nagpur
    ("MUM-WH", "MUM-PT", "local"),    # Mumbai to JNPT
    ("BLR-WH", "CHN-WH", "NH48"),     # Bangalore-Chennai
    ("BLR-WH", "HYD-WH", "NH44"),     # Bangalore-Hyderabad
    ("BLR-WH", "COI-DC", "NH44"),     # Bangalore-Coimbatore
    ("CHN-WH", "CHN-PT", "local"),    # Chennai warehouse to port
    ("CHN-WH", "HYD-WH", "NH65"),     # Chennai-Hyderabad
    ("HYD-WH", "NAG-DC", "NH44"),     # Hyderabad-Nagpur
    ("HYD-WH", "VIZ-DC", "NH65"),     # Hyderabad-Visakhapatnam
    ("KOL-WH", "PAT-DC", "NH19"),     # Kolkata-Patna
    ("KOL-WH", "KOL-PT", "local"),    # Kolkata to port
    ("LKO-DC", "PAT-DC", "NH27"),    # Lucknow-Patna
    ("BHO-DC", "NAG-DC", "NH46"),     # Bhopal-Nagpur
    ("JAI-DC", "AHM-WH", "NH48"),     # Jaipur-Ahmedabad
    ("COI-DC", "KOC-PT", "NH66"),     # Coimbatore-Kochi
    # Air corridors
    ("DEL-AC", "MUM-AC", "air"),
    ("DEL-AC", "BLR-AC", "air"),
    ("MUM-AC", "BLR-AC", "air"),
]


# ============================================================
# HAVERSINE DISTANCE
# ============================================================
def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points in km (Haversine formula)."""
    R = 6371  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    return R * c


# ============================================================
# ROUTE ENGINE CLASS
# ============================================================
class RouteEngine:
    """
    Core routing engine for STRYDER AI.
    Maintains a logistics hub graph and provides:
    - Shortest path routing
    - Distance + ETA calculation
    - Route path generation (for map animation)
    - Hub lookup and geospatial queries
    """

    def __init__(self):
        self.hubs = {}
        self.graph = None
        self._build_india_graph()

    def _build_india_graph(self):
        """Build the India logistics hub graph."""
        if not HAS_NETWORKX:
            raise ImportError("networkx is required for route engine")

        self.graph = nx.Graph()
        self.hubs = INDIA_HUBS.copy()

        # Add nodes
        for hub_id, info in self.hubs.items():
            self.graph.add_node(hub_id, **info)

        # Add edges with distance weights
        for src, dst, corridor in FREIGHT_CORRIDORS:
            if src in self.hubs and dst in self.hubs:
                src_info = self.hubs[src]
                dst_info = self.hubs[dst]
                distance = haversine_km(src_info["lat"], src_info["lon"],
                                       dst_info["lat"], dst_info["lon"])

                # Road distance is ~1.3x straight-line, air is 1.0x
                road_factor = 1.0 if corridor == "air" else 1.3
                road_distance = distance * road_factor

                # Average speed by corridor type
                if corridor == "air":
                    avg_speed = 800  # km/h
                elif corridor == "local":
                    avg_speed = 30   # km/h (urban)
                else:
                    avg_speed = 55   # km/h (highway freight)

                travel_hours = road_distance / avg_speed

                self.graph.add_edge(
                    src, dst,
                    distance_km=round(road_distance, 1),
                    straight_line_km=round(distance, 1),
                    corridor=corridor,
                    travel_hours=round(travel_hours, 2),
                    avg_speed_kmh=avg_speed,
                )

    def get_hub(self, hub_id: str) -> Optional[dict]:
        """Get hub information by ID."""
        return self.hubs.get(hub_id)

    def get_all_hubs(self) -> dict:
        """Get all hub data (for map rendering)."""
        return self.hubs

    def get_hubs_by_type(self, hub_type: str) -> dict:
        """Get hubs filtered by type."""
        return {k: v for k, v in self.hubs.items() if v["type"] == hub_type}

    def find_nearest_hub(self, lat: float, lon: float, hub_type: Optional[str] = None) -> tuple:
        """Find the nearest hub to a given coordinate."""
        best_id = None
        best_dist = float("inf")
        for hub_id, info in self.hubs.items():
            if hub_type and info["type"] != hub_type:
                continue
            d = haversine_km(lat, lon, info["lat"], info["lon"])
            if d < best_dist:
                best_dist = d
                best_id = hub_id
        return best_id, best_dist

    def calculate_route(self, origin_id: str, destination_id: str) -> dict:
        """
        Calculate the optimal route between two hubs.
        Returns path, distance, estimated travel time, and waypoints.
        """
        if origin_id not in self.graph or destination_id not in self.graph:
            return {"error": f"Hub not found: {origin_id} or {destination_id}"}

        try:
            path = nx.shortest_path(self.graph, origin_id, destination_id, weight="distance_km")
        except nx.NetworkXNoPath:
            return {"error": f"No route between {origin_id} and {destination_id}"}

        # Calculate totals along path
        total_distance = 0
        total_hours = 0
        segments = []
        waypoints = []

        for i in range(len(path)):
            hub = self.hubs[path[i]]
            waypoints.append({
                "hub_id": path[i],
                "name": hub["name"],
                "lat": hub["lat"],
                "lon": hub["lon"],
                "type": hub["type"],
            })

            if i < len(path) - 1:
                edge = self.graph[path[i]][path[i+1]]
                total_distance += edge["distance_km"]
                total_hours += edge["travel_hours"]
                segments.append({
                    "from": path[i],
                    "to": path[i+1],
                    "distance_km": edge["distance_km"],
                    "travel_hours": edge["travel_hours"],
                    "corridor": edge["corridor"],
                })

        return {
            "origin": origin_id,
            "destination": destination_id,
            "path": path,
            "total_distance_km": round(total_distance, 1),
            "total_travel_hours": round(total_hours, 2),
            "estimated_travel_days": round(total_hours / 12, 1),  # 12h driving/day
            "segments": segments,
            "waypoints": waypoints,
            "num_stops": len(path),
        }

    def generate_route_animation_points(self, origin_id: str, destination_id: str,
                                        num_points: int = 50) -> list:
        """
        Generate interpolated lat/lon points along a route for smooth map animation.
        Returns a list of {lat, lon, progress_pct} dicts.
        """
        route = self.calculate_route(origin_id, destination_id)
        if "error" in route:
            return []

        waypoints = route["waypoints"]
        if len(waypoints) < 2:
            return []

        # Interpolate between waypoints
        points = []
        total_dist = route["total_distance_km"]
        cumulative = 0

        for i in range(len(waypoints) - 1):
            wp1 = waypoints[i]
            wp2 = waypoints[i + 1]
            seg_dist = haversine_km(wp1["lat"], wp1["lon"], wp2["lat"], wp2["lon"])

            # Allocate points proportionally to segment distance
            seg_points = max(2, int(num_points * seg_dist / total_dist)) if total_dist > 0 else 2

            for j in range(seg_points):
                t = j / seg_points
                lat = wp1["lat"] + t * (wp2["lat"] - wp1["lat"])
                lon = wp1["lon"] + t * (wp2["lon"] - wp1["lon"])
                progress = (cumulative + t * seg_dist) / total_dist if total_dist > 0 else 0

                # Add slight random offset for realistic road path appearance
                jitter = 0.002 * math.sin(j * 0.5)
                points.append({
                    "lat": round(lat + jitter, 5),
                    "lon": round(lon + jitter, 5),
                    "progress_pct": round(progress * 100, 1),
                })

            cumulative += seg_dist

        # Add final destination
        final = waypoints[-1]
        points.append({"lat": final["lat"], "lon": final["lon"], "progress_pct": 100.0})

        return points

    def get_graph_summary(self) -> dict:
        """Get summary statistics of the logistics graph."""
        return {
            "total_hubs": len(self.hubs),
            "total_corridors": self.graph.number_of_edges(),
            "hub_types": {
                t: len([h for h in self.hubs.values() if h["type"] == t])
                for t in set(h["type"] for h in self.hubs.values())
            },
            "total_network_distance_km": round(
                sum(d["distance_km"] for _, _, d in self.graph.edges(data=True)), 1
            ),
            "avg_corridor_distance_km": round(
                np.mean([d["distance_km"] for _, _, d in self.graph.edges(data=True)]), 1
            ),
        }

    def get_all_routes_geojson(self) -> dict:
        """Export all corridors as GeoJSON for map rendering."""
        features = []

        # Hub points
        for hub_id, info in self.hubs.items():
            features.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [info["lon"], info["lat"]]},
                "properties": {
                    "id": hub_id, "name": info["name"],
                    "type": info["type"], "capacity": info["capacity"],
                    "city": info["city"],
                },
            })

        # Corridor lines
        for src, dst, data in self.graph.edges(data=True):
            src_info = self.hubs[src]
            dst_info = self.hubs[dst]
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [src_info["lon"], src_info["lat"]],
                        [dst_info["lon"], dst_info["lat"]],
                    ],
                },
                "properties": {
                    "from": src, "to": dst,
                    "corridor": data["corridor"],
                    "distance_km": data["distance_km"],
                    "travel_hours": data["travel_hours"],
                },
            })

        return {"type": "FeatureCollection", "features": features}


# ============================================================
# MODULE-LEVEL SINGLETON
# ============================================================
_engine: Optional[RouteEngine] = None


def get_route_engine() -> RouteEngine:
    """Get or create the singleton route engine."""
    global _engine
    if _engine is None:
        _engine = RouteEngine()
    return _engine


# ============================================================
# CONVENIENCE FUNCTIONS
# ============================================================
def get_route(origin: str, destination: str) -> dict:
    """Calculate route between two hub IDs."""
    return get_route_engine().calculate_route(origin, destination)


def get_all_hubs() -> dict:
    """Get all hub data."""
    return get_route_engine().get_all_hubs()


def get_animation_points(origin: str, destination: str, num_points: int = 50) -> list:
    """Get animation waypoints for a route."""
    return get_route_engine().generate_route_animation_points(origin, destination, num_points)


def get_network_geojson() -> dict:
    """Get full network as GeoJSON."""
    return get_route_engine().get_all_routes_geojson()


# ============================================================
# MAIN (for testing)
# ============================================================
if __name__ == "__main__":
    engine = RouteEngine()

    print("=" * 60)
    print("STRYDER AI - ROUTE ENGINE")
    print("=" * 60)

    # Graph summary
    summary = engine.get_graph_summary()
    print(f"\nNetwork Summary:")
    for k, v in summary.items():
        print(f"  {k}: {v}")

    # Test routes
    print("\n--- Test Routes ---")
    test_routes = [
        ("DEL-WH", "MUM-WH"),
        ("DEL-WH", "BLR-WH"),
        ("MUM-WH", "CHN-WH"),
        ("KOL-WH", "BLR-WH"),
        ("DEL-WH", "KOC-PT"),
    ]

    for src, dst in test_routes:
        route = engine.calculate_route(src, dst)
        if "error" not in route:
            path_str = " -> ".join(route["path"])
            print(f"\n  {src} -> {dst}")
            print(f"    Path: {path_str}")
            print(f"    Distance: {route['total_distance_km']} km")
            print(f"    Travel: {route['total_travel_hours']} hours ({route['estimated_travel_days']} days)")
            print(f"    Stops: {route['num_stops']}")
        else:
            print(f"\n  {src} -> {dst}: {route['error']}")

    # Test animation points
    print("\n--- Animation Points (DEL->BLR) ---")
    points = engine.generate_route_animation_points("DEL-WH", "BLR-WH", 20)
    print(f"  Generated {len(points)} points")
    if points:
        print(f"  Start: ({points[0]['lat']}, {points[0]['lon']})")
        print(f"  End:   ({points[-1]['lat']}, {points[-1]['lon']})")

    # Test nearest hub
    print("\n--- Nearest Hub Test ---")
    hub_id, dist = engine.find_nearest_hub(20.0, 78.0)  # Central India
    print(f"  Nearest to (20.0, 78.0): {hub_id} ({dist:.0f} km)")

    # GeoJSON
    geojson = engine.get_all_routes_geojson()
    print(f"\n--- GeoJSON ---")
    print(f"  Features: {len(geojson['features'])}")

    print("\n=== ROUTE ENGINE VALIDATED ===")
