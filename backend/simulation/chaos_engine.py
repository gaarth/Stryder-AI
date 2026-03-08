"""
STRYDER AI - Chaos Event Engine
=================================
Injects realistic disruptions into the logistics simulation.
Supports manual injection via UI and automated random chaos.

Chaos types:
- Truck breakdowns, road congestion, weather disruptions
- Warehouse overflow, customs delays, strikes
- Carrier failures, fuel shortages, accidents
"""

import random
import uuid
from datetime import datetime
from typing import Optional

from backend.simulation.route_engine import INDIA_HUBS


# All possible chaos event templates
CHAOS_TEMPLATES = {
    "truck_breakdown": {
        "name": "Truck Breakdown",
        "severity": "HIGH",
        "base_delay_hours": 8,
        "affects": "shipment",
        "description": "Vehicle breakdown on {route}. Estimated {delay}h delay.",
    },
    "road_congestion": {
        "name": "Road Congestion",
        "severity": "MEDIUM",
        "base_delay_hours": 4,
        "affects": "route",
        "description": "Heavy traffic congestion on {route}. +{delay}h to ETAs.",
    },
    "weather_disruption": {
        "name": "Severe Weather",
        "severity": "HIGH",
        "base_delay_hours": 12,
        "affects": "region",
        "description": "Severe weather alert in {city}. All operations impacted: +{delay}h.",
    },
    "warehouse_overflow": {
        "name": "Warehouse Overflow",
        "severity": "HIGH",
        "base_delay_hours": 6,
        "affects": "warehouse",
        "description": "Hub {hub} at max capacity. Inbound shipments queued: +{delay}h.",
    },
    "customs_delay": {
        "name": "Customs Delay",
        "severity": "MEDIUM",
        "base_delay_hours": 24,
        "affects": "port",
        "description": "Customs clearance delay at {hub}. Expected {delay}h hold.",
    },
    "driver_unavailable": {
        "name": "Driver Unavailable",
        "severity": "LOW",
        "base_delay_hours": 3,
        "affects": "shipment",
        "description": "Driver unavailable for {shipment}. Reassignment needed: +{delay}h.",
    },
    "carrier_failure": {
        "name": "Carrier System Failure",
        "severity": "CRITICAL",
        "base_delay_hours": 10,
        "affects": "carrier",
        "description": "Carrier {carrier} experiencing system failure. All shipments affected.",
    },
    "fuel_shortage": {
        "name": "Fuel Shortage",
        "severity": "MEDIUM",
        "base_delay_hours": 5,
        "affects": "region",
        "description": "Fuel shortage reported in {city} region. Fleet operations slowed.",
    },
    "port_strike": {
        "name": "Port Workers Strike",
        "severity": "CRITICAL",
        "base_delay_hours": 48,
        "affects": "port",
        "description": "Strike at {hub}. Port operations halted. All cargo delayed.",
    },
    "accident": {
        "name": "Road Accident",
        "severity": "HIGH",
        "base_delay_hours": 6,
        "affects": "route",
        "description": "Accident on {route}. Route blocked. Rerouting needed: +{delay}h.",
    },
}


class ChaosEngine:
    """Injects chaos events into the simulation."""

    def __init__(self, world_state):
        self.world = world_state
        self.event_history: list[dict] = []
        self.auto_chaos = False
        self.auto_interval_ticks = 10  # Inject chaos every N ticks
        self.ticks_since_chaos = 0

    def inject_chaos(self, chaos_type: str, target_id: Optional[str] = None,
                     severity_override: Optional[str] = None) -> dict:
        """
        Inject a specific chaos event into the simulation.
        Returns the created chaos event with all effects.
        """
        template = CHAOS_TEMPLATES.get(chaos_type)
        if not template:
            return {"error": f"Unknown chaos type: {chaos_type}. Options: {list(CHAOS_TEMPLATES.keys())}"}

        # Determine delay with randomness
        base_delay = template["base_delay_hours"]
        actual_delay = round(base_delay * random.uniform(0.5, 1.5), 1)

        # Pick target if not specified
        target = self._resolve_target(template["affects"], target_id)

        # Build event
        event = {
            "chaos_id": f"CX{random.randint(1000, 9999)}",
            "type": chaos_type,
            "name": template["name"],
            "severity": severity_override or template["severity"],
            "delay_hours": actual_delay,
            "affects": template["affects"],
            "target": target,
            "timestamp": self.world.sim_time.isoformat(),
            "created_at": datetime.now().isoformat(),
            "status": "ACTIVE",
            "resolved": False,
            "description": template["description"].format(
                route=target.get("route", "N/A"),
                delay=actual_delay,
                city=target.get("city", "Unknown"),
                hub=target.get("hub_id", "N/A"),
                shipment=target.get("shipment_id", "N/A"),
                carrier=target.get("carrier_name", "N/A"),
            ),
        }

        # Apply effects to world state
        effects = self._apply_effects(event)
        event["effects"] = effects

        # Store
        self.world.add_chaos_event(event)
        self.event_history.append(event)

        return event

    def inject_random_chaos(self) -> dict:
        """Inject a random chaos event."""
        chaos_type = random.choice(list(CHAOS_TEMPLATES.keys()))
        return self.inject_chaos(chaos_type)

    def resolve_chaos(self, chaos_id: str) -> dict:
        """Mark a chaos event as resolved."""
        for event in self.world.chaos_events:
            if event.get("chaos_id") == chaos_id:
                event["resolved"] = True
                event["status"] = "RESOLVED"
                event["resolved_at"] = datetime.now().isoformat()
                return {"success": True, "chaos_id": chaos_id}
        return {"error": f"Chaos event not found: {chaos_id}"}

    def tick(self):
        """Auto-chaos injection on simulation tick."""
        if self.auto_chaos:
            self.ticks_since_chaos += 1
            if self.ticks_since_chaos >= self.auto_interval_ticks:
                self.inject_random_chaos()
                self.ticks_since_chaos = 0

    def _resolve_target(self, affects: str, target_id: Optional[str]) -> dict:
        """Resolve the target entity for a chaos event."""
        if affects == "shipment":
            if target_id:
                ship = self.world.get_shipment(target_id)
                if ship:
                    return {"shipment_id": target_id, "route": ship.get("route_path", ""),
                            "carrier_name": ship.get("carrier_name", "")}
            # Pick random in-transit shipment, or any shipment as fallback
            active = [s for s in self.world.shipments if s.get("status") == "IN_TRANSIT"]
            if not active:
                active = self.world.shipments  # fallback to any shipment
            if active:
                s = random.choice(active)
                return {"shipment_id": s["shipment_id"], "route": s.get("route_path", ""),
                        "carrier_name": s.get("carrier_name", "")}

        elif affects == "warehouse" or affects == "port":
            if target_id:
                wh = self.world.get_warehouse(target_id)
                if wh:
                    return {"hub_id": target_id, "city": wh.get("city", "")}
            hubs = [w for w in self.world.warehouses]
            if affects == "port":
                hubs = [w for w in hubs if "PT" in w.get("warehouse_id", "")]
            if hubs:
                h = random.choice(hubs)
                return {"hub_id": h["warehouse_id"], "city": h.get("city", "")}

        elif affects == "carrier":
            if target_id:
                c = self.world.get_carrier(target_id)
                if c:
                    return {"carrier_id": target_id, "carrier_name": c.get("name", "")}
            if self.world.carriers:
                c = random.choice(self.world.carriers)
                return {"carrier_id": c["carrier_id"], "carrier_name": c.get("name", "")}

        elif affects == "route" or affects == "region":
            cities = list(set(h.get("city", "") for h in INDIA_HUBS.values()))
            city = random.choice(cities) if cities else "Unknown"
            return {"city": city, "route": f"NH-{random.randint(1, 100)}"}

        return {"target_id": target_id or "unknown"}

    def _apply_effects(self, event: dict) -> dict:
        """Apply chaos event effects to world state."""
        effects = {"shipments_affected": 0, "details": []}
        delay = event["delay_hours"]
        target = event["target"]
        affects = event["affects"]

        if affects == "shipment":
            sid = target.get("shipment_id")
            if sid:
                self.world.update_shipment(sid, {
                    "has_disruption": True,
                    "disruption_type": event["type"],
                    "disruption_delay_hours": delay,
                })
                effects["shipments_affected"] = 1
                effects["details"].append(f"Shipment {sid} delayed by {delay}h")

        elif affects == "carrier":
            cid = target.get("carrier_id")
            if cid:
                # Degrade carrier reliability
                carrier = self.world.get_carrier(cid)
                if carrier:
                    new_rel = max(0.1, carrier.get("reliability_score", 0.8) - 0.15)
                    self.world.update_carrier(cid, {"reliability_score": round(new_rel, 4)})
                # Affect all shipments by this carrier
                for s in self.world.shipments:
                    if s.get("carrier_id") == cid and s.get("status") == "IN_TRANSIT":
                        self.world.update_shipment(s["shipment_id"], {
                            "has_disruption": True,
                            "disruption_type": event["type"],
                            "disruption_delay_hours": delay,
                        })
                        effects["shipments_affected"] += 1

        elif affects == "warehouse" or affects == "port":
            hub_id = target.get("hub_id")
            if hub_id:
                wh = self.world.get_warehouse(hub_id)
                if wh:
                    self.world.update_warehouse(hub_id, {
                        "congestion_level": "HIGH",
                        "utilization_pct": min(100, wh.get("utilization_pct", 80) + 15),
                        "queue_length": wh.get("queue_length", 0) + 10,
                    })
                # Affect shipments going through this hub
                for s in self.world.shipments:
                    if s.get("status") == "IN_TRANSIT" and hub_id in str(s.get("route_path", "")):
                        self.world.update_shipment(s["shipment_id"], {
                            "has_disruption": True,
                            "disruption_type": event["type"],
                            "disruption_delay_hours": delay,
                        })
                        effects["shipments_affected"] += 1

        elif affects in ("route", "region"):
            city = target.get("city", "")
            for s in self.world.shipments:
                if s.get("status") == "IN_TRANSIT":
                    if city in str(s.get("origin_city", "")) or city in str(s.get("destination_city", "")):
                        self.world.update_shipment(s["shipment_id"], {
                            "has_disruption": True,
                            "disruption_type": event["type"],
                            "disruption_delay_hours": delay,
                        })
                        effects["shipments_affected"] += 1

        return effects

    def get_active_chaos(self) -> list:
        """Get all active (unresolved) chaos events."""
        return [e for e in self.world.chaos_events if not e.get("resolved")]

    def get_chaos_types(self) -> dict:
        """Get all available chaos types for the UI."""
        return {k: {"name": v["name"], "severity": v["severity"],
                     "affects": v["affects"], "base_delay": v["base_delay_hours"]}
                for k, v in CHAOS_TEMPLATES.items()}
