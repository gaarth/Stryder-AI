"""
STRYDER AI - Simulation Router
=================================
Endpoints for simulation control, world state, and chaos injection.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from backend.simulation.world_state import get_world_state
from backend.simulation.shipment_engine import ShipmentEngine
from backend.simulation.chaos_engine import ChaosEngine

router = APIRouter(prefix="/api/simulation", tags=["Simulation"])


# ============================================================
# REQUEST MODELS
# ============================================================
class CreateShipmentRequest(BaseModel):
    origin_hub: str
    destination_hub: str
    cargo_type: str = "General"
    weight_kg: float = 1000
    sla_tier: str = "STANDARD"
    customer_id: Optional[str] = None


class ChaosInjectRequest(BaseModel):
    chaos_type: str
    target_id: Optional[str] = None
    severity_override: Optional[str] = None


class SimControlRequest(BaseModel):
    action: str  # "start", "stop", "tick", "set_speed"
    value: Optional[float] = None


# ============================================================
# WORLD STATE
# ============================================================
@router.get("/state")
async def get_state():
    """Get current world state snapshot."""
    world = get_world_state()
    return world.get_snapshot()


@router.get("/stats")
async def get_stats():
    """Get simulation statistics."""
    world = get_world_state()
    return world.get_stats()


# ============================================================
# SHIPMENTS
# ============================================================
@router.get("/shipments")
async def list_shipments(status: Optional[str] = None, limit: int = 50):
    """List shipments, optionally filtered by status."""
    world = get_world_state()
    if status:
        ships = world.get_shipments_by_status(status)
    else:
        ships = world.shipments
    return {"shipments": ships[:limit], "total": len(ships)}


@router.get("/shipments/{shipment_id}")
async def get_shipment(shipment_id: str):
    """Get a specific shipment."""
    world = get_world_state()
    ship = world.get_shipment(shipment_id)
    if not ship:
        raise HTTPException(404, f"Shipment not found: {shipment_id}")
    return ship


@router.post("/shipments/create")
async def create_shipment(req: CreateShipmentRequest):
    """Create a new shipment."""
    world = get_world_state()
    engine = ShipmentEngine(world)
    result = engine.create_shipment(
        req.origin_hub, req.destination_hub, req.cargo_type,
        req.weight_kg, req.sla_tier, req.customer_id
    )
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


@router.post("/shipments/{shipment_id}/reroute")
async def reroute_shipment(shipment_id: str, new_destination: str):
    """Reroute a shipment to a new destination."""
    world = get_world_state()
    engine = ShipmentEngine(world)
    result = engine.reroute_shipment(shipment_id, new_destination)
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


@router.get("/shipments/{shipment_id}/timeline")
async def shipment_timeline(shipment_id: str):
    """Get event timeline for a shipment."""
    world = get_world_state()
    engine = ShipmentEngine(world)
    events = engine.get_shipment_timeline(shipment_id)
    return {"shipment_id": shipment_id, "events": events}


# ============================================================
# CHAOS ENGINE
# ============================================================
@router.get("/chaos/types")
async def get_chaos_types():
    """Get all available chaos event types."""
    world = get_world_state()
    chaos = ChaosEngine(world)
    return chaos.get_chaos_types()


@router.post("/chaos/inject")
async def inject_chaos(req: ChaosInjectRequest):
    """Inject a chaos event into the simulation."""
    world = get_world_state()
    chaos = ChaosEngine(world)
    result = chaos.inject_chaos(req.chaos_type, req.target_id, req.severity_override)
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


@router.post("/chaos/random")
async def inject_random_chaos():
    """Inject a random chaos event."""
    world = get_world_state()
    chaos = ChaosEngine(world)
    return chaos.inject_random_chaos()


@router.get("/chaos/active")
async def get_active_chaos():
    """Get all active chaos events."""
    world = get_world_state()
    chaos = ChaosEngine(world)
    return {"events": chaos.get_active_chaos()}


@router.post("/chaos/{chaos_id}/resolve")
async def resolve_chaos(chaos_id: str):
    """Resolve a chaos event."""
    world = get_world_state()
    chaos = ChaosEngine(world)
    result = chaos.resolve_chaos(chaos_id)
    if "error" in result:
        raise HTTPException(404, result["error"])
    return result


# ============================================================
# SIM CONTROL
# ============================================================
@router.post("/control")
async def sim_control(req: SimControlRequest):
    """Control simulation: start, stop, tick, set_speed."""
    world = get_world_state()
    if req.action == "tick":
        minutes = req.value or 15
        world.tick(delta_minutes=minutes)
        return {"action": "tick", "sim_time": world.sim_time.isoformat(), "tick": world.tick_count}
    elif req.action == "set_speed":
        world.sim_speed = req.value or 1.0
        return {"action": "set_speed", "speed": world.sim_speed}
    elif req.action == "start":
        world.sim_running = True
        return {"action": "start", "running": True}
    elif req.action == "stop":
        world.sim_running = False
        return {"action": "stop", "running": False}
    else:
        raise HTTPException(400, f"Unknown action: {req.action}")


# ============================================================
# CARRIERS & WAREHOUSES
# ============================================================
@router.get("/carriers")
async def list_carriers():
    """List all carriers."""
    world = get_world_state()
    return {"carriers": world.carriers}


@router.get("/warehouses")
async def list_warehouses():
    """List all warehouses."""
    world = get_world_state()
    return {"warehouses": world.warehouses}
