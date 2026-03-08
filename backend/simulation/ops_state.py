"""
STRYDER AI — Authoritative Operations Simulation State v2
==========================================================
Single source of truth. Agents are CONTROLLERS that modify this state.
Includes: cost model, port/warehouse live state, agent memory,
ETA optimization, structured command execution.
"""
import random, math, threading, time
from datetime import datetime, timedelta
from typing import Optional

# Lazy import to avoid circular deps
def _bg_sync(fn, *args):
    """Fire-and-forget background sync to Supabase."""
    threading.Thread(target=fn, args=args, daemon=True).start()

# ────────────────────────────────────────────────────────
# GEOGRAPHY — Real Indian locations
# ────────────────────────────────────────────────────────
PORTS = [
    {"id": "PRT-MUM", "name": "Mumbai Port",         "lat": 18.94, "lon": 72.84, "type": "port"},
    {"id": "PRT-CHE", "name": "Chennai Port",        "lat": 13.08, "lon": 80.29, "type": "port"},
    {"id": "PRT-VIZ", "name": "Vishakhapatnam Port", "lat": 17.69, "lon": 83.22, "type": "port"},
    {"id": "PRT-KOL", "name": "Kolkata Port",        "lat": 22.55, "lon": 88.35, "type": "port"},
    {"id": "PRT-KOC", "name": "Kochi Port",          "lat":  9.97, "lon": 76.27, "type": "port"},
    {"id": "PRT-KAN", "name": "Kandla Port",         "lat": 23.03, "lon": 70.22, "type": "port"},
    {"id": "PRT-TUT", "name": "Tuticorin Port",      "lat":  8.76, "lon": 78.13, "type": "port"},
    {"id": "PRT-GOA", "name": "Goa Port",            "lat": 15.41, "lon": 73.88, "type": "port"},
]

WAREHOUSES = [
    {"id": "WH-DEL", "name": "Delhi Warehouse",     "lat": 28.61, "lon": 77.23, "type": "warehouse"},
    {"id": "WH-BHO", "name": "Bhopal Warehouse",    "lat": 23.26, "lon": 77.41, "type": "warehouse"},
    {"id": "WH-NAG", "name": "Nagpur Warehouse",     "lat": 21.15, "lon": 79.09, "type": "warehouse"},
    {"id": "WH-AHM", "name": "Ahmedabad Warehouse",  "lat": 23.02, "lon": 72.57, "type": "warehouse"},
    {"id": "WH-JAI", "name": "Jaipur Warehouse",     "lat": 26.91, "lon": 75.79, "type": "warehouse"},
    {"id": "WH-HYD", "name": "Hyderabad Warehouse",  "lat": 17.39, "lon": 78.49, "type": "warehouse"},
    {"id": "WH-BEN", "name": "Bengaluru Warehouse",  "lat": 12.97, "lon": 77.59, "type": "warehouse"},
    {"id": "WH-LUC", "name": "Lucknow Warehouse",   "lat": 26.85, "lon": 80.95, "type": "warehouse"},
]

CITIES = {n["id"]: n for n in PORTS + WAREHOUSES}
ALL_LOCATIONS = PORTS + WAREHOUSES

CARRIERS = [
    {"name": "DHL",          "base_rate": 450, "speed_factor": 1.2},
    {"name": "Maersk",       "base_rate": 320, "speed_factor": 0.9},
    {"name": "BlueDart",     "base_rate": 380, "speed_factor": 1.1},
    {"name": "FedEx",        "base_rate": 500, "speed_factor": 1.3},
    {"name": "DTDC",         "base_rate": 280, "speed_factor": 0.8},
    {"name": "Gati",         "base_rate": 300, "speed_factor": 0.85},
    {"name": "Delhivery",    "base_rate": 340, "speed_factor": 1.0},
    {"name": "Ecom Express", "base_rate": 260, "speed_factor": 0.75},
]
CARRIER_MAP = {c["name"]: c for c in CARRIERS}
CARGO_TYPES = ["Electronics", "FMCG", "Machinery", "Textiles", "Pharma", "Auto Parts", "Chemicals", "Food"]

DISRUPTION_TYPES = [
    {"name": "Port congestion",      "category": "port",      "severity": "HIGH",   "eta_impact_h": 36},
    {"name": "Carrier strike",       "category": "carrier",   "severity": "HIGH",   "eta_impact_h": 48},
    {"name": "Weather delay",        "category": "weather",   "severity": "MEDIUM", "eta_impact_h": 18},
    {"name": "Customs inspection",   "category": "customs",   "severity": "LOW",    "eta_impact_h": 12},
    {"name": "Warehouse overflow",   "category": "warehouse", "severity": "MEDIUM", "eta_impact_h": 24},
    {"name": "Route blockage",       "category": "route",     "severity": "HIGH",   "eta_impact_h": 30},
    {"name": "Vehicle breakdown",    "category": "vehicle",   "severity": "MEDIUM", "eta_impact_h": 16},
    {"name": "Labour shortage",      "category": "labour",    "severity": "LOW",    "eta_impact_h": 10},
]


# ────────────────────────────────────────────────────────
# ROUTE / COST HELPERS
# ────────────────────────────────────────────────────────
def _lerp(a, b, t):
    return a + (b - a) * t

def _geo_dist(a, b):
    """Approximate distance in km between two lat/lon points."""
    return math.sqrt((a["lat"]-b["lat"])**2 + (a["lon"]-b["lon"])**2) * 111

def _route_coords(origin_id, dest_id, steps=12):
    o, d = CITIES[origin_id], CITIES[dest_id]
    coords = []
    for i in range(steps + 1):
        t = i / steps
        lat = _lerp(o["lat"], d["lat"], t) + random.uniform(-0.2, 0.2) * math.sin(t * math.pi)
        lon = _lerp(o["lon"], d["lon"], t) + random.uniform(-0.2, 0.2) * math.sin(t * math.pi)
        coords.append({"lat": round(lat, 4), "lon": round(lon, 4)})
    return coords

def _calc_cost(distance_km, carrier_name, cargo_type):
    """Calculate shipment cost based on distance, carrier rate, cargo type."""
    carrier = CARRIER_MAP.get(carrier_name, CARRIERS[0])
    base = distance_km * carrier["base_rate"] / 100
    # Cargo multiplier (pharma/electronics cost more)
    cargo_mult = {"Electronics": 1.4, "Pharma": 1.5, "Machinery": 1.3, "Chemicals": 1.2}.get(cargo_type, 1.0)
    return round(base * cargo_mult, 0)

def _calc_eta(distance_km, carrier_name):
    carrier = CARRIER_MAP.get(carrier_name, CARRIERS[0])
    # ~50km/h average, adjusted by carrier speed factor
    hours = distance_km / (50 * carrier["speed_factor"])
    return max(2, round(hours))


# ────────────────────────────────────────────────────────
# PORT / WAREHOUSE LIVE STATE
# ────────────────────────────────────────────────────────
def _init_port_state(port):
    return {
        **port,
        "congestion_level": random.choice(["LOW", "MODERATE", "LOW", "LOW"]),
        "congestion_pct": random.randint(15, 45),
        "throughput": random.randint(80, 250),
        "incoming_count": 0,
    }

def _init_wh_state(wh):
    cap = random.randint(200, 500)
    util = random.randint(40, 80)
    return {
        **wh,
        "capacity": cap,
        "utilization_pct": util,
        "incoming_count": 0,
    }


# ────────────────────────────────────────────────────────
# SIMULATION STATE (singleton)
# ────────────────────────────────────────────────────────
class OpsState:
    def __init__(self):
        self._lock = threading.RLock()
        self.version = 0
        self.time_tick = 0
        self.sim_time = datetime(2026, 3, 8, 6, 0, 0)
        self.auto_mode = True
        self.shipments: list[dict] = []
        self.port_states: list[dict] = []
        self.wh_states: list[dict] = []
        self.disruptions: list[dict] = []
        self.metrics_log: list[dict] = []
        self.agent_log: list[dict] = []
        self.event_log: list[dict] = []
        self.cascade_alerts: list[dict] = []

        # ── SIMULATION CONTROL ──
        self.sim_paused = False
        self.sim_speed = 1.0          # 0.25, 0.5, 1, 2, 5
        self.movement_scale = 1.0     # 0, 0.25, 0.5, 1.0
        self.sim_frozen = False       # freeze all state

        # ── LEARNING LOGS (chronological) ──
        self.learning_logs: list[dict] = []

        # ── SCENARIO HISTORY ──
        self.scenario_history: list[dict] = []

        # Agent memory
        self.agent_memory = {
            "global_strategy": "balanced",
            "shipment_priorities": {},
            "optimization_history": [],
            "user_preferences": [],
            "agent_learnings": {
                "sentinel_detections": 0,
                "strategist_optimizations": 0,
                "actuary_evaluations": 0,
                "executor_executions": 0,
                "cascade_predictions": 0,
                "total_cost_saved": 0,
                "total_hours_saved": 0,
            },
        }

        # Agent performance metrics
        self.agent_stats = {
            "Sentinel":   {"detections": 0, "accuracy": 94.2, "last_run": None},
            "Strategist": {"optimizations": 0, "success_rate": 87.5, "last_run": None},
            "Actuary":    {"evaluations": 0, "prediction_error": 3.8, "last_run": None},
            "Executor":   {"executions": 0, "latency_ms": 45, "last_run": None},
            "Cascade":    {"predictions": 0, "accuracy": 78.3, "last_run": None},
        }

        self._build_ports_warehouses()
        self._build_shipments()

    def _bump(self):
        self.version += 1
        # Sync to Supabase every 5 ticks (non-blocking)
        if self.time_tick > 0 and self.time_tick % 5 == 0:
            self._sync_to_supabase()

    def _sync_to_supabase(self):
        """Background sync of core state to Supabase."""
        try:
            from backend.services.supabase_sync import sync_shipments, sync_ports, sync_warehouses
            shipments_copy = [dict(s) for s in self.shipments]
            ports_copy = [dict(p) for p in self.port_states]
            wh_copy = [dict(w) for w in self.wh_states]
            # Remove non-serializable fields from shipments
            for s in shipments_copy:
                s.pop("route", None)
                s.pop("fix_history", None)
            _bg_sync(sync_shipments, shipments_copy)
            _bg_sync(sync_ports, ports_copy)
            _bg_sync(sync_warehouses, wh_copy)
        except Exception:
            pass

    # ──── BUILD ────
    def _build_ports_warehouses(self):
        self.port_states = [_init_port_state(p) for p in PORTS]
        self.wh_states = [_init_wh_state(w) for w in WAREHOUSES]

    def _build_shipments(self):
        all_nodes = list(CITIES.keys())
        total_count = 120  # enough density for every port/warehouse

        # Phase 1: Guarantee every node appears as both origin & destination
        # This ensures every port/warehouse has incoming shipments
        guaranteed_pairs = []
        for node in all_nodes:
            others = [n for n in all_nodes if n != node]
            guaranteed_pairs.append((node, random.choice(others)))           # node as origin
            guaranteed_pairs.append((random.choice(others), node))           # node as destination
        random.shuffle(guaranteed_pairs)

        ship_id = 1
        for origin_id, dest_id in guaranteed_pairs[:total_count]:
            self._add_shipment(ship_id, origin_id, dest_id)
            ship_id += 1

        # Phase 2: Fill remaining slots randomly
        while ship_id <= total_count:
            origin_id = random.choice(all_nodes)
            dest_id = random.choice([n for n in all_nodes if n != origin_id])
            self._add_shipment(ship_id, origin_id, dest_id)
            ship_id += 1

    def _add_shipment(self, ship_id, origin_id, dest_id):
        route = _route_coords(origin_id, dest_id)
        max_start = max(0, len(route) - 3)  # leave at least 2 steps to go
        progress = random.randint(0, min(max_start, int(len(route) * 0.6)))
        carrier = random.choice(CARRIERS)
        cargo = random.choice(CARGO_TYPES)
        dist = _geo_dist(CITIES[origin_id], CITIES[dest_id])
        cost = _calc_cost(dist, carrier["name"], cargo)
        eta = _calc_eta(dist, carrier["name"])
        elapsed = int(eta * progress / max(1, len(route)))
        remaining = max(2, eta - elapsed)
        penalty = round(random.uniform(200, 800))

        self.shipments.append({
            "id": ship_id,
            "origin": CITIES[origin_id]["name"].replace(" Port", "").replace(" Warehouse", ""),
            "origin_id": origin_id,
            "destination": CITIES[dest_id]["name"].replace(" Port", "").replace(" Warehouse", ""),
            "destination_id": dest_id,
            "carrier": carrier["name"],
            "cargo": cargo,
            "status": "IN_TRANSIT" if progress < len(route) - 1 else "DELIVERED",
            "eta_hours": remaining,
            "base_cost": cost,
            "current_cost": cost,
            "delay_penalty_per_hour": penalty,
            "risk": "Low",
            "route": route,
            "progress": progress,
            "lat": route[progress]["lat"],
            "lon": route[progress]["lon"],
            "disrupted": False,
            "disruption_id": None,
            "fix_history": [],
            "has_update": False,
            "priority": None,
        })

    def reset(self):
        with self._lock:
            self.time_tick = 0
            self.sim_time = datetime(2026, 3, 8, 6, 0, 0)
            self.shipments = []
            self.disruptions = []
            self.metrics_log = []
            self.agent_log = []
            self.event_log = []
            self.cascade_alerts = []
            self.learning_logs = []
            self.scenario_history = []
            self.sim_paused = False
            self.sim_frozen = False
            self.agent_memory["shipment_priorities"] = {}
            self.agent_memory["optimization_history"] = []
            self._build_ports_warehouses()
        self._build_shipments()
        self._bump()
        # Clear Supabase data on reset
        try:
            from backend.services.supabase_sync import clear_simulation_data, sync_shipments, sync_ports, sync_warehouses
            _bg_sync(clear_simulation_data)
        except Exception:
            pass

    # ──── TICK (respects sim controls) ────
    def tick(self, minutes: int = 30):
        with self._lock:
            if self.sim_frozen:
                return
            self.time_tick += 1
            self.sim_time += timedelta(minutes=minutes)
            ts = self.sim_time.strftime("%H:%M")

            for s in self.shipments:
                if s["status"] in ("DELIVERED", "PENDING"):
                    continue
                # Advance position (scaled by movement_scale)
                if self.movement_scale > 0 and s["progress"] < len(s["route"]) - 1:
                    if random.random() < self.movement_scale:
                        s["progress"] += 1
                        s["lat"] = s["route"][s["progress"]]["lat"]
                        s["lon"] = s["route"][s["progress"]]["lon"]
                    s["eta_hours"] = max(0, s["eta_hours"] - random.randint(1, 3))
                elif self.movement_scale == 0:
                    s["eta_hours"] = max(0, s["eta_hours"] - 1)
                # Accrue delay penalties
                if s["status"] == "DELAYED":
                    s["current_cost"] += s["delay_penalty_per_hour"] * 0.5
                # Arrival
                if s["progress"] >= len(s["route"]) - 1:
                    s["status"] = "DELIVERED"
                    s["eta_hours"] = 0
                elif s["eta_hours"] <= 0:
                    s["status"] = "DELIVERED"

            self._update_infrastructure()
            self.metrics_log.append({"ts": ts, "msg": f"Tick {self.time_tick}: +{minutes}m", "type": "info"})
            self._bump()

    def _update_infrastructure(self):
        """Recalculate port congestion and warehouse utilization based on shipments."""
        for p in self.port_states:
            nearby = sum(1 for s in self.shipments if s["status"] == "IN_TRANSIT"
                         and (abs(s["lat"] - p["lat"]) + abs(s["lon"] - p["lon"]) < 3
                              or s.get("destination_id") == p["id"]
                              or s.get("origin_id") == p["id"]))
            p["incoming_count"] = max(1, nearby)  # minimum 1 (guaranteed by node coverage)
            p["congestion_pct"] = min(95, 20 + nearby * 5 + random.randint(-3, 3))
            p["congestion_level"] = "HIGH" if p["congestion_pct"] > 70 else "MODERATE" if p["congestion_pct"] > 40 else "LOW"

        for w in self.wh_states:
            nearby = sum(1 for s in self.shipments if s["status"] == "IN_TRANSIT"
                         and (abs(s["lat"] - w["lat"]) + abs(s["lon"] - w["lon"]) < 3
                              or s.get("destination_id") == w["id"]
                              or s.get("origin_id") == w["id"]))
            w["incoming_count"] = max(1, nearby)
            w["utilization_pct"] = min(98, 50 + nearby * 4 + random.randint(-5, 5))

    # ──── SENTINEL SCAN ────
    def sentinel_scan(self) -> list:
        """Sentinel background scan: detect anomalies from state."""
        with self._lock:
            ts = self.sim_time.strftime("%H:%M")
            alerts = []
            # Check for high congestion ports
            for p in self.port_states:
                if p["congestion_pct"] > 70:
                    alerts.append(f"High congestion at {p['name']}: {p['congestion_pct']}%")
            # Check for near-capacity warehouses
            for w in self.wh_states:
                if w["utilization_pct"] > 85:
                    alerts.append(f"Near capacity at {w['name']}: {w['utilization_pct']}%")
            # Check delayed shipments
            delayed = [s for s in self.shipments if s["status"] == "DELAYED"]
            if delayed:
                alerts.append(f"{len(delayed)} shipments currently delayed")

            self.agent_stats["Sentinel"]["detections"] += len(alerts)
            self.agent_stats["Sentinel"]["last_run"] = self.sim_time.isoformat()
            if alerts:
                self.metrics_log.append({"ts": ts, "msg": f"Sentinel scan: {len(alerts)} alerts", "type": "agent"})
            return alerts

    # ──── CASCADE PREDICTIONS ────
    def cascade_predict(self) -> list:
        """Cascade agent predicts upcoming failures."""
        with self._lock:
            ts = self.sim_time.strftime("%H:%M")
            self.cascade_alerts = []

            for p in self.port_states:
                if p["congestion_pct"] > 55:
                    confidence = min(95, p["congestion_pct"] + random.randint(-10, 10))
                    impact = sum(1 for s in self.shipments if s["status"] == "IN_TRANSIT"
                                 and abs(s["lat"] - p["lat"]) + abs(s["lon"] - p["lon"]) < 5)
                    if impact > 0:
                        self.cascade_alerts.append({
                            "id": len(self.cascade_alerts) + 1,
                            "type": "congestion_risk",
                            "location": p["name"],
                            "location_id": p["id"],
                            "confidence": confidence,
                            "impact_count": impact,
                            "suggestion": f"Pre-emptively reroute {min(5, impact)} shipments",
                            "severity": "HIGH" if confidence > 75 else "MEDIUM",
                        })

            for w in self.wh_states:
                if w["utilization_pct"] > 80:
                    confidence = min(92, w["utilization_pct"] + random.randint(-8, 8))
                    self.cascade_alerts.append({
                        "id": len(self.cascade_alerts) + 1,
                        "type": "overflow_risk",
                        "location": w["name"],
                        "location_id": w["id"],
                        "confidence": confidence,
                        "impact_count": w["incoming_count"],
                        "suggestion": f"Divert incoming to alternate warehouse",
                        "severity": "MEDIUM",
                    })

            self.agent_stats["Cascade"]["predictions"] += len(self.cascade_alerts)
            self.agent_stats["Cascade"]["last_run"] = self.sim_time.isoformat()
            return self.cascade_alerts

    # ──── DISRUPTIONS ────
    def inject_disruption(self) -> dict:
        with self._lock:
            template = random.choice(DISRUPTION_TYPES)
            location = random.choice(ALL_LOCATIONS)
            ts = self.sim_time.strftime("%H:%M")

            affected = [s for s in self.shipments if s["status"] == "IN_TRANSIT" and (
                s["origin_id"] == location["id"] or s["destination_id"] == location["id"]
                or abs(s["lat"] - location["lat"]) + abs(s["lon"] - location["lon"]) < 10
            )]
            # Guarantee minimum affected
            transit = [s for s in self.shipments if s["status"] == "IN_TRANSIT" and s not in affected]
            min_affected = min(8, len(transit) + len(affected))
            while len(affected) < min_affected and transit:
                pick = random.choice(transit)
                transit.remove(pick)
                affected.append(pick)

            disruption = {
                "id": len(self.disruptions) + 1,
                "name": template["name"],
                "severity": template["severity"],
                "location": location["name"],
                "location_id": location["id"],
                "eta_impact_h": template["eta_impact_h"],
                "affected_count": len(affected),
                "affected_ids": [s["id"] for s in affected],
                "timestamp": self.sim_time.isoformat(),
                "resolved": False,
            }
            self.disruptions.append(disruption)

            for s in affected:
                s["status"] = "DELAYED"
                s["eta_hours"] += template["eta_impact_h"]
                s["current_cost"] += s["delay_penalty_per_hour"] * template["eta_impact_h"]
                s["risk"] = "High" if template["severity"] == "HIGH" else "Medium"
                s["disrupted"] = True
                s["disruption_id"] = disruption["id"]

            # Update port congestion if port-related
            if location["type"] == "port":
                for p in self.port_states:
                    if p["id"] == location["id"]:
                        p["congestion_pct"] = min(95, p["congestion_pct"] + 25)
                        p["congestion_level"] = "HIGH"

            self.metrics_log.append({"ts": ts, "msg": f"{template['name']} at {location['name']}", "type": "disruption"})
            self.metrics_log.append({"ts": ts, "msg": f"{len(affected)} shipments delayed, ETA +{template['eta_impact_h']}h", "type": "warning"})
            self._bump()
            # Sync disruption to Supabase
            try:
                from backend.services.supabase_sync import log_disruption, log_metric
                _bg_sync(log_disruption, disruption)
                _bg_sync(log_metric, template['name'], len(affected), f"{template['name']} at {location['name']}", "disruption", ts)
            except Exception:
                pass
            return disruption

    # ──── AGENT REASONING (enhanced with cost awareness) ────
    def run_agents(self, disruption: Optional[dict] = None) -> list:
        with self._lock:
            ts = self.sim_time.strftime("%H:%M")
            steps = []
            strategy = self.agent_memory["global_strategy"]

            if not disruption:
                unresolved = [d for d in self.disruptions if not d["resolved"]]
                disruption = unresolved[-1] if unresolved else None

            if not disruption:
                steps.append({"agent": "Sentinel", "bullets": ["No active disruptions", "All systems nominal"]})
                return steps

            loc = disruption["location"]
            name = disruption["name"]
            count = disruption["affected_count"]
            ids = disruption["affected_ids"]
            eta_h = disruption["eta_impact_h"]

            # Sentinel
            total_penalty = sum(s["delay_penalty_per_hour"] * eta_h for s in self.shipments if s["id"] in ids)
            sentinel_out = [
                f"Detected {name} at {loc}",
                f"{count} shipments impacted",
                f"Severity: {disruption['severity']}",
                f"Total penalty exposure: ₹{total_penalty:,.0f}",
            ]
            steps.append({"agent": "Sentinel", "bullets": sentinel_out})
            self.agent_stats["Sentinel"]["detections"] += 1
            self.agent_stats["Sentinel"]["last_run"] = self.sim_time.isoformat()
            self.metrics_log.append({"ts": ts, "msg": f"Sentinel: {name} at {loc}", "type": "agent"})

            # Strategist
            alt_loc = random.choice([p["name"] for p in ALL_LOCATIONS if p["name"] != loc])
            reroute_count = min(count, random.randint(3, max(4, count)))
            delay_reduction = random.randint(max(4, eta_h // 3), min(eta_h, 24))
            extra_cost = round(random.uniform(2000, 8000))

            # Strategy influences decision
            if strategy == "cost":
                reroute_count = max(2, reroute_count - 2)  # fewer reroutes = lower cost
                strategist_out = [
                    f"Cost-optimized: reroute {reroute_count} shipments via {alt_loc}",
                    f"Delay reduction: {delay_reduction}h",
                    f"Additional cost: ₹{extra_cost:,.0f}",
                    f"Strategy: minimizing cost (user preference)",
                ]
            elif strategy == "speed":
                reroute_count = min(count, reroute_count + 2)  # more reroutes = faster
                extra_cost = round(extra_cost * 1.5)
                strategist_out = [
                    f"Speed-optimized: reroute {reroute_count} shipments via {alt_loc}",
                    f"Delay reduction: {delay_reduction}h",
                    f"Additional cost: ₹{extra_cost:,.0f}",
                    f"Strategy: fastest delivery (user preference)",
                ]
            else:
                strategist_out = [
                    f"Balanced: reroute {reroute_count} shipments via {alt_loc}",
                    f"Delay reduction: {delay_reduction}h",
                    f"Additional cost: ₹{extra_cost:,.0f}",
                ]
            steps.append({"agent": "Strategist", "bullets": strategist_out})
            self.agent_stats["Strategist"]["optimizations"] += 1
            self.agent_stats["Strategist"]["last_run"] = self.sim_time.isoformat()
            self.metrics_log.append({"ts": ts, "msg": f"Strategist: reroute via {alt_loc}", "type": "agent"})

            # Actuary
            penalty_saved = round(total_penalty * delay_reduction / eta_h)
            net_impact = extra_cost - penalty_saved
            actuary_out = [
                f"Delay reduction: {delay_reduction} hours",
                f"Reroute cost: ₹{extra_cost:,.0f}",
                f"Penalty savings: ₹{penalty_saved:,.0f}",
                f"Net impact: {'₹' + f'{abs(net_impact):,.0f}' + (' saved' if net_impact < 0 else ' additional')}",
                f"SLA breach probability: {random.randint(5, 25)}%",
            ]
            steps.append({"agent": "Actuary", "bullets": actuary_out})
            self.agent_stats["Actuary"]["evaluations"] += 1
            self.agent_stats["Actuary"]["last_run"] = self.sim_time.isoformat()
            self.metrics_log.append({"ts": ts, "msg": f"Actuary: net {'saving' if net_impact < 0 else 'cost'} ₹{abs(net_impact):,.0f}", "type": "agent"})

            # Executor — apply fix
            new_carrier = random.choice(CARRIERS)
            rerouted_ids = random.sample(ids, min(len(ids), reroute_count))
            fix_details = []
            for sid in rerouted_ids:
                ship = next((s for s in self.shipments if s["id"] == sid), None)
                if ship:
                    old_carrier = ship["carrier"]
                    old_eta = ship["eta_hours"]
                    old_cost = ship["current_cost"]
                    ship["status"] = "IN_TRANSIT"
                    ship["eta_hours"] = max(1, ship["eta_hours"] - delay_reduction)
                    ship["carrier"] = new_carrier["name"]
                    ship["current_cost"] += extra_cost / reroute_count
                    ship["risk"] = "Low"
                    ship["disrupted"] = False
                    ship["has_update"] = True
                    fix = {
                        "disruption_id": disruption["id"],
                        "event": name,
                        "fix": f"Rerouted via {alt_loc}",
                        "old_carrier": old_carrier,
                        "new_carrier": new_carrier["name"],
                        "old_eta": old_eta,
                        "new_eta": ship["eta_hours"],
                        "old_cost": round(old_cost),
                        "new_cost": round(ship["current_cost"]),
                        "timestamp": self.sim_time.isoformat(),
                    }
                    ship["fix_history"].append(fix)
                    fix_details.append({"id": sid, **fix})

            executor_out = [
                f"Rerouted {len(rerouted_ids)} shipments: {','.join(str(x) for x in rerouted_ids)}",
                f"New route via {alt_loc}",
                f"Carrier → {new_carrier['name']}",
                f"ETA reduced by ~{delay_reduction}h",
            ]
            steps.append({"agent": "Executor", "bullets": executor_out, "rerouted_ids": rerouted_ids, "fix_details": fix_details})
            self.agent_stats["Executor"]["executions"] += 1
            self.agent_stats["Executor"]["last_run"] = self.sim_time.isoformat()
            self.metrics_log.append({"ts": ts, "msg": f"Executor: rerouted {len(rerouted_ids)} shipments", "type": "agent"})

            # Cascade
            cascade_risk = random.choice(["LOW", "MEDIUM", "LOW", "LOW"])
            cascade_out = [
                f"Secondary congestion risk at {alt_loc}: {cascade_risk}",
                "No downstream SLA breaches predicted" if cascade_risk == "LOW" else f"Monitor {alt_loc} for capacity",
            ]
            steps.append({"agent": "Cascade", "bullets": cascade_out})
            self.agent_stats["Cascade"]["predictions"] += 1
            self.agent_stats["Cascade"]["last_run"] = self.sim_time.isoformat()

            # Resolve
            disruption["resolved"] = True

            # Update learnings
            self.agent_memory["agent_learnings"]["total_hours_saved"] += delay_reduction * len(rerouted_ids)
            self.agent_memory["agent_learnings"]["total_cost_saved"] += max(0, -net_impact)
            self.agent_memory["agent_learnings"]["executor_executions"] += 1

            # Event log
            self.event_log.append({
                "id": len(self.event_log) + 1,
                "disruption_id": disruption["id"],
                "timestamp": self.sim_time.isoformat(),
                "title": f"{name} at {loc}",
                "severity": disruption["severity"],
                "affected_count": count,
                "rerouted_count": len(rerouted_ids),
                "rerouted_ids": rerouted_ids,
                "resolved": True,
                "summary": f"{name} — {count} affected, {len(rerouted_ids)} rerouted via {alt_loc}",
                "cost_impact": f"₹{extra_cost:,.0f} additional, ₹{penalty_saved:,.0f} saved",
                "steps": steps,
                "fix_details": fix_details,
            })

            self.agent_log.append({
                "tick": self.time_tick,
                "timestamp": self.sim_time.isoformat(),
                "disruption_id": disruption["id"],
                "steps": steps,
            })
            self._bump()
            return steps

    # ──── ETA OPTIMIZATION ENGINE ────
    def optimize_eta(self, shipment_id: int) -> dict:
        """Generate optimization options for a shipment — works even without disruptions."""
        with self._lock:
            ship = next((s for s in self.shipments if s["id"] == shipment_id), None)
            if not ship:
                return {"error": f"Shipment #{shipment_id} not found"}
            if ship["status"] == "DELIVERED":
                return {"error": f"Shipment #{shipment_id} already delivered"}

            current_eta = ship["eta_hours"]
            current_cost = ship["current_cost"]
            current_carrier = ship["carrier"]
            origin = ship["origin"]
            dest = ship["destination"]

            options = []
            # Option 1: reroute via intermediate hub
            via = random.choice([l["name"].replace(" Port", "").replace(" Warehouse", "")
                                 for l in ALL_LOCATIONS if l["name"] not in (origin, dest)])
            opt1_eta = max(1, current_eta - random.randint(4, 12))
            opt1_cost_add = round(random.uniform(2000, 6000))
            options.append({
                "index": 1,
                "description": f"Route via {via}",
                "eta": opt1_eta,
                "eta_saved": current_eta - opt1_eta,
                "cost_increase": opt1_cost_add,
                "new_cost": round(current_cost + opt1_cost_add),
                "carrier": current_carrier,
            })

            # Option 2: express carrier switch
            fast_carrier = max(CARRIERS, key=lambda c: c["speed_factor"])
            opt2_eta = max(1, current_eta - random.randint(8, 18))
            opt2_cost_add = round(random.uniform(5000, 12000))
            options.append({
                "index": 2,
                "description": f"Express carrier: {fast_carrier['name']}",
                "eta": opt2_eta,
                "eta_saved": current_eta - opt2_eta,
                "cost_increase": opt2_cost_add,
                "new_cost": round(current_cost + opt2_cost_add),
                "carrier": fast_carrier["name"],
            })

            # Option 3: priority lane (if not already cheapest option)
            opt3_eta = max(1, current_eta - random.randint(2, 6))
            opt3_cost_add = round(random.uniform(1000, 3000))
            options.append({
                "index": 3,
                "description": "Priority lane upgrade",
                "eta": opt3_eta,
                "eta_saved": current_eta - opt3_eta,
                "cost_increase": opt3_cost_add,
                "new_cost": round(current_cost + opt3_cost_add),
                "carrier": current_carrier,
            })

            result = {
                "shipment_id": shipment_id,
                "origin": origin,
                "destination": dest,
                "current_eta": current_eta,
                "current_cost": round(current_cost),
                "current_carrier": current_carrier,
                "options": options,
            }

            self.agent_stats["Strategist"]["optimizations"] += 1
            self.agent_stats["Strategist"]["last_run"] = self.sim_time.isoformat()
            return result

    def apply_option(self, shipment_id: int, option_index: int) -> dict:
        """Apply an optimization option to a shipment."""
        with self._lock:
            ship = next((s for s in self.shipments if s["id"] == shipment_id), None)
            if not ship:
                return {"error": f"Shipment #{shipment_id} not found"}

            # Regenerate options (deterministic enough for demo)
            # In production you'd cache the options
            opts = self.optimize_eta(shipment_id)
            if "error" in opts:
                return opts
            opt = next((o for o in opts["options"] if o["index"] == option_index), None)
            if not opt:
                return {"error": f"Option {option_index} not found"}

            ts = self.sim_time.strftime("%H:%M")
            old_eta = ship["eta_hours"]
            old_cost = ship["current_cost"]
            old_carrier = ship["carrier"]

            ship["eta_hours"] = opt["eta"]
            ship["current_cost"] = opt["new_cost"]
            ship["carrier"] = opt["carrier"]
            ship["has_update"] = True
            ship["fix_history"].append({
                "event": "ETA Optimization",
                "fix": opt["description"],
                "old_carrier": old_carrier,
                "new_carrier": opt["carrier"],
                "old_eta": old_eta,
                "new_eta": opt["eta"],
                "old_cost": round(old_cost),
                "new_cost": opt["new_cost"],
                "timestamp": self.sim_time.isoformat(),
            })

            self.agent_memory["optimization_history"].append({
                "shipment_id": shipment_id,
                "option": opt["description"],
                "eta_saved": old_eta - opt["eta"],
                "cost_added": opt["cost_increase"],
                "timestamp": self.sim_time.isoformat(),
            })

            self.agent_memory["agent_learnings"]["total_hours_saved"] += old_eta - opt["eta"]
            self.agent_memory["agent_learnings"]["strategist_optimizations"] += 1

            self.metrics_log.append({"ts": ts, "msg": f"ETA optimized: #{shipment_id} → {opt['eta']}h ({opt['description']})", "type": "agent"})
            self.agent_stats["Executor"]["executions"] += 1
            self.agent_stats["Executor"]["last_run"] = self.sim_time.isoformat()
            self._bump()

            return {
                "ok": True,
                "shipment_id": shipment_id,
                "applied": opt["description"],
                "old_eta": old_eta,
                "new_eta": opt["eta"],
                "old_cost": round(old_cost),
                "new_cost": opt["new_cost"],
            }

    # ──── COMMAND EXECUTION ────
    def execute_command(self, cmd_type: str, params: dict) -> dict:
        """Structured command execution — prevents hallucinated actions."""
        with self._lock:
            ts = self.sim_time.strftime("%H:%M")

            if cmd_type == "SWITCH_CARRIER":
                sid = params.get("shipment_id")
                new_carrier = params.get("carrier")
                ship = next((s for s in self.shipments if s["id"] == sid), None)
                if not ship:
                    return {"error": f"Shipment #{sid} not found"}
                old = ship["carrier"]
                ship["carrier"] = new_carrier
                ship["has_update"] = True
                self.metrics_log.append({"ts": ts, "msg": f"Carrier switch: #{sid} {old} → {new_carrier}", "type": "agent"})
                self._bump()
                return {"ok": True, "old_carrier": old, "new_carrier": new_carrier}

            elif cmd_type == "SET_PRIORITY":
                sid = params.get("shipment_id")
                priority = params.get("priority")  # "cost" | "speed"
                self.agent_memory["shipment_priorities"][sid] = priority
                self.metrics_log.append({"ts": ts, "msg": f"Priority set: #{sid} → {priority}", "type": "agent"})
                return {"ok": True, "shipment_id": sid, "priority": priority}

            elif cmd_type == "SET_STRATEGY":
                strategy = params.get("strategy")
                if strategy not in ("cost", "speed", "balanced"):
                    return {"error": "Strategy must be cost, speed, or balanced"}
                self.agent_memory["global_strategy"] = strategy
                self.metrics_log.append({"ts": ts, "msg": f"Global strategy → {strategy}", "type": "agent"})
                return {"ok": True, "strategy": strategy}

            return {"error": f"Unknown command: {cmd_type}"}

    # ──── LEARNING LOG ────
    def add_learning(self, agent: str, message: str):
        with self._lock:
            ts = self.sim_time.strftime("%H:%M")
            self.learning_logs.append({
                "id": len(self.learning_logs) + 1,
                "timestamp": self.sim_time.isoformat(),
                "ts": ts,
                "agent": agent,
                "message": message,
            })
            # Sync to Supabase
            try:
                from backend.services.supabase_sync import log_learning
                _bg_sync(log_learning, agent, message, ts)
            except Exception:
                pass

    # ──── SCENARIO INJECTION ────
    def inject_scenario(self, scenario_type: str) -> dict:
        """Inject a specific predefined scenario. Deterministic effects."""
        SCENARIOS = {
            "PORT_CONGESTION": {
                "name": "Port congestion",
                "locations": ["PRT-CHE", "PRT-MUM", "PRT-VIZ"],
                "severity": "HIGH",
                "eta_impact_h": 36,
                "description": "Port operations slowed due to congestion backlog",
            },
            "CARRIER_STRIKE": {
                "name": "Carrier strike",
                "locations": ["PRT-MUM", "PRT-KOL"],
                "severity": "HIGH",
                "eta_impact_h": 48,
                "description": "Carrier workforce strike halting shipment processing",
            },
            "WEATHER_DISRUPTION": {
                "name": "Weather delay",
                "locations": ["PRT-KOC", "PRT-GOA", "PRT-TUT"],
                "severity": "MEDIUM",
                "eta_impact_h": 18,
                "description": "Cyclonic weather causing route disruptions",
            },
            "WAREHOUSE_OVERFLOW": {
                "name": "Warehouse overflow",
                "locations": ["WH-DEL", "WH-BEN", "WH-HYD"],
                "severity": "MEDIUM",
                "eta_impact_h": 24,
                "description": "Warehouse capacity exceeded, incoming shipments queued",
            },
            "CUSTOMS_DELAY": {
                "name": "Customs inspection delay",
                "locations": ["PRT-CHE", "PRT-KAN", "PRT-MUM"],
                "severity": "LOW",
                "eta_impact_h": 12,
                "description": "Enhanced customs inspection causing delays",
            },
            "ROUTE_BLOCKAGE": {
                "name": "Route blockage",
                "locations": ["WH-NAG", "WH-BHO", "WH-JAI"],
                "severity": "HIGH",
                "eta_impact_h": 30,
                "description": "Major route blocked due to infrastructure failure",
            },
        }

        template = SCENARIOS.get(scenario_type)
        if not template:
            return {"error": f"Unknown scenario: {scenario_type}. Available: {list(SCENARIOS.keys())}"}

        with self._lock:
            ts = self.sim_time.strftime("%H:%M")
            loc_id = random.choice(template["locations"])
            location = CITIES[loc_id]

            affected = [s for s in self.shipments if s["status"] == "IN_TRANSIT" and (
                s["origin_id"] == loc_id or s["destination_id"] == loc_id
                or abs(s["lat"] - location["lat"]) + abs(s["lon"] - location["lon"]) < 10
            )]
            # Guarantee minimum affected: if geo-check found too few, add random in-transit
            transit = [s for s in self.shipments if s["status"] == "IN_TRANSIT" and s not in affected]
            min_affected = min(8, len(transit) + len(affected))
            while len(affected) < min_affected and transit:
                pick = random.choice(transit)
                transit.remove(pick)
                affected.append(pick)

            disruption = {
                "id": len(self.disruptions) + 1,
                "name": template["name"],
                "severity": template["severity"],
                "location": location["name"],
                "location_id": loc_id,
                "eta_impact_h": template["eta_impact_h"],
                "affected_count": len(affected),
                "affected_ids": [s["id"] for s in affected],
                "timestamp": self.sim_time.isoformat(),
                "resolved": False,
                "scenario_type": scenario_type,
            }
            self.disruptions.append(disruption)

            for s in affected:
                s["status"] = "DELAYED"
                s["eta_hours"] += template["eta_impact_h"]
                s["current_cost"] += s["delay_penalty_per_hour"] * template["eta_impact_h"]
                s["risk"] = "High" if template["severity"] == "HIGH" else "Medium"
                s["disrupted"] = True
                s["disruption_id"] = disruption["id"]

            if location["type"] == "port":
                for p in self.port_states:
                    if p["id"] == loc_id:
                        p["congestion_pct"] = min(95, p["congestion_pct"] + 30)
                        p["congestion_level"] = "HIGH"

            self.scenario_history.append({
                "id": len(self.scenario_history) + 1,
                "type": scenario_type,
                "disruption_id": disruption["id"],
                "timestamp": self.sim_time.isoformat(),
                "location": location["name"],
                "affected_count": len(affected),
                "description": template["description"],
            })

            self.metrics_log.append({"ts": ts, "msg": f"Scenario: {template['name']} at {location['name']}", "type": "disruption"})
            self.add_learning("Sentinel", f"Detected {template['name']} at {location['name']} — {len(affected)} shipments impacted")
            self._bump()
            # Sync scenario to Supabase
            try:
                from backend.services.supabase_sync import log_disruption, log_scenario
                _bg_sync(log_disruption, {**disruption, "scenario_type": scenario_type})
                _bg_sync(log_scenario, {
                    "type": scenario_type,
                    "location": location["name"],
                    "affected_count": len(affected),
                    "description": template["description"],
                })
            except Exception:
                pass
            return disruption

    # ──── SNAPSHOTS ────
    def get_snapshot(self) -> dict:
        with self._lock:
            return {
                "version": self.version,
                "time_tick": self.time_tick,
                "sim_time": self.sim_time.isoformat(),
                "auto_mode": self.auto_mode,
                "global_strategy": self.agent_memory["global_strategy"],
                # Sim controls
                "sim_paused": self.sim_paused,
                "sim_speed": self.sim_speed,
                "movement_scale": self.movement_scale,
                "sim_frozen": self.sim_frozen,
                # Data
                "shipments": [_ship_summary(s) for s in self.shipments],
                "ports": self.port_states,
                "warehouses": self.wh_states,
                "disruptions": list(self.disruptions),
                "metrics_log": list(self.metrics_log[-60:]),
                "agent_log": list(self.agent_log[-10:]),
                "event_log": list(self.event_log[-20:]),
                "cascade_alerts": list(self.cascade_alerts),
                "agent_stats": self.agent_stats,
                "learning_logs": list(self.learning_logs[-30:]),
                "scenario_history": list(self.scenario_history),
                "agent_memory_summary": {
                    "strategy": self.agent_memory["global_strategy"],
                    "total_hours_saved": self.agent_memory["agent_learnings"]["total_hours_saved"],
                    "total_cost_saved": self.agent_memory["agent_learnings"]["total_cost_saved"],
                    "optimizations": len(self.agent_memory["optimization_history"]),
                },
                "stats": {
                    "total": len(self.shipments),
                    "in_transit": sum(1 for s in self.shipments if s["status"] == "IN_TRANSIT"),
                    "delivered": sum(1 for s in self.shipments if s["status"] == "DELIVERED"),
                    "delayed": sum(1 for s in self.shipments if s["status"] == "DELAYED"),
                    "at_risk": sum(1 for s in self.shipments if s["status"] == "AT_RISK"),
                    "active_disruptions": sum(1 for d in self.disruptions if not d["resolved"]),
                },
            }


def _ship_summary(s: dict) -> dict:
    return {
        "id": s["id"],
        "origin": s["origin"],
        "destination": s["destination"],
        "carrier": s["carrier"],
        "cargo": s["cargo"],
        "status": s["status"],
        "eta_hours": s["eta_hours"],
        "base_cost": s["base_cost"],
        "current_cost": round(s["current_cost"]),
        "delay_penalty_per_hour": s["delay_penalty_per_hour"],
        "risk": s["risk"],
        "lat": s["lat"],
        "lon": s["lon"],
        "disrupted": s["disrupted"],
        "has_update": s.get("has_update", False),
        "fix_history": s.get("fix_history", []),
        "priority": s.get("priority"),
    }


# Singleton
_state: Optional[OpsState] = None
def get_ops_state() -> OpsState:
    global _state
    if _state is None:
        _state = OpsState()
    return _state
