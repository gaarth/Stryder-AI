"""
STRYDER AI - Shipment Engine
==============================
Manages shipment lifecycle operations:
- Create, update, and track shipments
- Assign carriers and routes
- Calculate ETAs using route engine + ML models
- Handle SLA monitoring
"""

import uuid
import random
from datetime import datetime, timedelta
from typing import Optional

from backend.simulation.route_engine import get_route_engine, INDIA_HUBS


class ShipmentEngine:
    """Manages shipment operations within the simulation."""

    def __init__(self, world_state):
        self.world = world_state
        self.route_engine = get_route_engine()

    def create_shipment(self, origin_hub: str, destination_hub: str,
                        cargo_type: str = "General", weight_kg: float = 1000,
                        sla_tier: str = "STANDARD", customer_id: str = None) -> dict:
        """Create a new shipment and assign to the simulation."""
        route = self.route_engine.calculate_route(origin_hub, destination_hub)
        if "error" in route:
            return {"error": route["error"]}

        # Pick a carrier from world state
        carriers = self.world.carriers
        available = [c for c in carriers if c.get("reliability_score", 0) > 0.6]
        carrier = random.choice(available) if available else carriers[0] if carriers else None

        sla_days = {"PREMIUM": 2, "EXPRESS": 4, "STANDARD": 7, "ECONOMY": 14}.get(sla_tier, 7)

        shipment = {
            "shipment_id": f"S{random.randint(5000, 9999)}",
            "customer_id": customer_id or f"CU{random.randint(1, 100):04d}",
            "carrier_id": carrier["carrier_id"] if carrier else "CR001",
            "carrier_name": carrier["name"] if carrier else "Default Carrier",
            "origin_hub": origin_hub,
            "origin_city": INDIA_HUBS.get(origin_hub, {}).get("city", origin_hub),
            "destination_hub": destination_hub,
            "destination_city": INDIA_HUBS.get(destination_hub, {}).get("city", destination_hub),
            "cargo_type": cargo_type,
            "weight_kg": weight_kg,
            "shipment_value": round(random.uniform(10000, 500000), 2),
            "sla_tier": sla_tier,
            "sla_max_days": sla_days,
            "creation_date": self.world.sim_time.isoformat(),
            "pickup_date": (self.world.sim_time + timedelta(hours=random.randint(2, 12))).isoformat(),
            "expected_delivery": (self.world.sim_time + timedelta(hours=route["total_travel_hours"])).isoformat(),
            "actual_delivery": None,
            "route_distance_km": route["total_distance_km"],
            "expected_hours": route["total_travel_hours"],
            "actual_hours": None,
            "route_stops": route["num_stops"],
            "route_path": ",".join(route["path"]),
            "status": "PENDING",
            "progress_pct": 0,
            "has_disruption": False,
            "disruption_type": None,
            "disruption_delay_hours": 0,
            "sla_breached": False,
            "delay_days": 0,
            "priority": {"PREMIUM": 1, "EXPRESS": 2, "STANDARD": 3, "ECONOMY": 4}.get(sla_tier, 3),
        }

        # Add to world state
        self.world.shipments.append(shipment)
        self.world._shipment_index[shipment["shipment_id"]] = len(self.world.shipments) - 1

        # Add creation event
        self.world.add_event({
            "shipment_id": shipment["shipment_id"],
            "event_type": "CREATED",
            "timestamp": datetime.now().isoformat(),
            "hub_id": origin_hub,
            "description": f"Shipment created: {origin_hub} -> {destination_hub}",
        })

        return shipment

    def update_status(self, shipment_id: str, new_status: str, note: str = ""):
        """Update shipment status and log event."""
        ship = self.world.get_shipment(shipment_id)
        if not ship:
            return {"error": f"Shipment not found: {shipment_id}"}

        old_status = ship.get("status")
        self.world.update_shipment(shipment_id, {"status": new_status})

        self.world.add_event({
            "shipment_id": shipment_id,
            "event_type": f"STATUS_CHANGE",
            "timestamp": datetime.now().isoformat(),
            "hub_id": ship.get("origin_hub"),
            "description": f"Status: {old_status} -> {new_status}. {note}",
        })

        return {"success": True, "old_status": old_status, "new_status": new_status}

    def reroute_shipment(self, shipment_id: str, new_destination: str) -> dict:
        """Reroute a shipment to a new destination hub."""
        ship = self.world.get_shipment(shipment_id)
        if not ship:
            return {"error": f"Shipment not found: {shipment_id}"}

        current_hub = ship.get("origin_hub")
        route = self.route_engine.calculate_route(current_hub, new_destination)
        if "error" in route:
            return route

        self.world.update_shipment(shipment_id, {
            "destination_hub": new_destination,
            "destination_city": INDIA_HUBS.get(new_destination, {}).get("city", new_destination),
            "route_distance_km": route["total_distance_km"],
            "expected_hours": route["total_travel_hours"],
            "route_path": ",".join(route["path"]),
            "route_stops": route["num_stops"],
        })

        self.world.add_event({
            "shipment_id": shipment_id,
            "event_type": "REROUTED",
            "timestamp": datetime.now().isoformat(),
            "hub_id": current_hub,
            "description": f"Rerouted to {new_destination} ({route['total_distance_km']} km)",
        })

        return {"success": True, "new_route": route}

    def reassign_carrier(self, shipment_id: str, new_carrier_id: str) -> dict:
        """Reassign a shipment to a different carrier."""
        ship = self.world.get_shipment(shipment_id)
        carrier = self.world.get_carrier(new_carrier_id)
        if not ship:
            return {"error": f"Shipment not found: {shipment_id}"}
        if not carrier:
            return {"error": f"Carrier not found: {new_carrier_id}"}

        old_carrier = ship.get("carrier_name")
        self.world.update_shipment(shipment_id, {
            "carrier_id": new_carrier_id,
            "carrier_name": carrier.get("name", new_carrier_id),
        })

        self.world.add_event({
            "shipment_id": shipment_id,
            "event_type": "CARRIER_CHANGED",
            "timestamp": datetime.now().isoformat(),
            "hub_id": ship.get("origin_hub"),
            "description": f"Carrier changed: {old_carrier} -> {carrier.get('name')}",
        })

        return {"success": True, "old_carrier": old_carrier, "new_carrier": carrier.get("name")}

    def get_active_shipments(self) -> list:
        """Get all active (non-delivered) shipments."""
        return [s for s in self.world.shipments
                if s.get("status") in ("PENDING", "IN_TRANSIT")]

    def get_shipment_timeline(self, shipment_id: str) -> list:
        """Get all events for a specific shipment."""
        return [e for e in self.world.events
                if e.get("shipment_id") == shipment_id]
