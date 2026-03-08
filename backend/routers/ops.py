"""
STRYDER AI — Operations API Router v3
========================================
Full CRUD + agent commands + cost optimization + cascade alerts
+ sim controls + scenario injection.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from backend.simulation.ops_state import get_ops_state

router = APIRouter(prefix="/api/ops", tags=["Operations"])


# ──── CORE STATE ────
@router.get("/state")
async def snapshot():
    return get_ops_state().get_snapshot()


@router.post("/tick")
async def tick(minutes: int = 30):
    state = get_ops_state()
    state.tick(minutes)
    return {"tick": state.time_tick, "sim_time": state.sim_time.isoformat()}


@router.post("/reset")
async def reset():
    state = get_ops_state()
    state.reset()
    return {"message": "Simulation reset", "tick": 0}


# ──── SIMULATION CONTROLS ────
class SimControlRequest(BaseModel):
    paused: Optional[bool] = None
    speed: Optional[float] = None
    movement_scale: Optional[float] = None
    frozen: Optional[bool] = None

@router.post("/sim-control")
async def sim_control(req: SimControlRequest):
    state = get_ops_state()
    if req.paused is not None:
        state.sim_paused = req.paused
    if req.speed is not None:
        state.sim_speed = max(0.25, min(5.0, req.speed))
    if req.movement_scale is not None:
        state.movement_scale = max(0.0, min(1.0, req.movement_scale))
    if req.frozen is not None:
        state.sim_frozen = req.frozen
    return {
        "sim_paused": state.sim_paused,
        "sim_speed": state.sim_speed,
        "movement_scale": state.movement_scale,
        "sim_frozen": state.sim_frozen,
    }


# ──── DISRUPTIONS & AGENTS ────
@router.post("/disrupt")
async def inject_disruption():
    state = get_ops_state()
    d = state.inject_disruption()
    steps = state.run_agents(d) if state.auto_mode else []
    return {"disruption": d, "agent_steps": steps, "auto_resolved": state.auto_mode}


@router.post("/run-agents")
async def run_agents():
    state = get_ops_state()
    steps = state.run_agents()
    return {"agent_steps": steps}


@router.post("/mode")
async def toggle_mode(auto: bool = True):
    state = get_ops_state()
    state.auto_mode = auto
    return {"auto_mode": state.auto_mode}


# ──── SCENARIO INJECTION ────
class ScenarioRequest(BaseModel):
    scenario_type: str  # PORT_CONGESTION, CARRIER_STRIKE, etc.

@router.post("/scenario")
async def inject_scenario(req: ScenarioRequest):
    state = get_ops_state()
    d = state.inject_scenario(req.scenario_type)
    if "error" in d:
        return d
    steps = state.run_agents(d) if state.auto_mode else []
    return {"disruption": d, "agent_steps": steps, "auto_resolved": state.auto_mode}

@router.get("/scenarios")
async def list_scenarios():
    return {"scenarios": [
        {"type": "PORT_CONGESTION", "label": "Port Congestion", "severity": "HIGH"},
        {"type": "CARRIER_STRIKE", "label": "Carrier Strike", "severity": "HIGH"},
        {"type": "WEATHER_DISRUPTION", "label": "Weather Disruption", "severity": "MEDIUM"},
        {"type": "WAREHOUSE_OVERFLOW", "label": "Warehouse Overflow", "severity": "MEDIUM"},
        {"type": "CUSTOMS_DELAY", "label": "Customs Delay", "severity": "LOW"},
        {"type": "ROUTE_BLOCKAGE", "label": "Route Blockage", "severity": "HIGH"},
    ]}


# ──── STRATEGY ────
class StrategyRequest(BaseModel):
    strategy: str
    shipment_id: Optional[int] = None

@router.post("/strategy")
async def set_strategy(req: StrategyRequest):
    state = get_ops_state()
    if req.shipment_id:
        return state.execute_command("SET_PRIORITY", {"shipment_id": req.shipment_id, "priority": req.strategy})
    return state.execute_command("SET_STRATEGY", {"strategy": req.strategy})


# ──── ETA OPTIMIZATION ────
@router.get("/optimize/{ship_id}")
async def optimize_eta(ship_id: int):
    return get_ops_state().optimize_eta(ship_id)


class ApplyOptionRequest(BaseModel):
    shipment_id: int
    option_index: int

@router.post("/apply-option")
async def apply_option(req: ApplyOptionRequest):
    return get_ops_state().apply_option(req.shipment_id, req.option_index)


# ──── COMMAND EXECUTION ────
class CommandRequest(BaseModel):
    cmd_type: str
    params: dict

@router.post("/execute")
async def execute_command(req: CommandRequest):
    return get_ops_state().execute_command(req.cmd_type, req.params)


# ──── SHIPMENT DETAIL ────
@router.get("/shipment/{ship_id}")
async def get_shipment(ship_id: int):
    state = get_ops_state()
    for s in state.shipments:
        if s["id"] == ship_id:
            from backend.simulation.ops_state import _ship_summary
            return _ship_summary(s)
    return {"error": "Shipment not found"}


@router.post("/shipment/{ship_id}/dismiss")
async def dismiss_update(ship_id: int):
    state = get_ops_state()
    for s in state.shipments:
        if s["id"] == ship_id:
            s["has_update"] = False
            return {"ok": True}
    return {"error": "Shipment not found"}


# ──── PORT / WAREHOUSE DETAILS ────
@router.get("/port/{port_id}")
async def get_port(port_id: str):
    for p in get_ops_state().port_states:
        if p["id"] == port_id:
            return p
    return {"error": "Port not found"}


@router.get("/warehouse/{wh_id}")
async def get_warehouse(wh_id: str):
    for w in get_ops_state().wh_states:
        if w["id"] == wh_id:
            return w
    return {"error": "Warehouse not found"}


# ──── CASCADE / STATS / EVENTS ────
@router.get("/cascade-alerts")
async def cascade_alerts():
    return {"alerts": get_ops_state().cascade_alerts}


@router.get("/agent-stats")
async def agent_stats():
    state = get_ops_state()
    return {"stats": state.agent_stats, "memory": state.agent_memory["agent_learnings"]}


@router.get("/events")
async def get_events():
    return {"events": get_ops_state().event_log}


@router.get("/events/{event_id}")
async def get_event(event_id: int):
    for e in get_ops_state().event_log:
        if e["id"] == event_id:
            return e
    return {"error": "Event not found"}


@router.get("/learning-logs")
async def learning_logs():
    return {"logs": get_ops_state().learning_logs}
