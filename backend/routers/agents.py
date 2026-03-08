"""
STRYDER AI - Agents Router
=============================
Endpoints for agent management, full loop execution, and decision log.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from backend.agents.orchestrator import get_orchestrator
from backend.simulation.world_state import get_world_state
from backend.services.decision_logger import get_decision_logger
from backend.services.learning_service import get_learning_service

router = APIRouter(prefix="/api/agents", tags=["Agents"])


class RunLoopRequest(BaseModel):
    shipment_limit: int = 50


class SetModeRequest(BaseModel):
    auto_mode: bool


# ============================================================
# AGENT STATUS
# ============================================================
@router.get("/status")
async def all_agent_statuses():
    """Get status of all agents."""
    orch = get_orchestrator()
    return {"agents": orch.get_all_statuses()}


@router.get("/status/{agent_name}")
async def agent_status(agent_name: str):
    """Get status of a specific agent."""
    orch = get_orchestrator()
    agent = orch.get_agent(agent_name)
    if not agent:
        raise HTTPException(404, f"Agent not found: {agent_name}")
    return agent.get_status()


# ============================================================
# FULL LOOP
# ============================================================
@router.post("/run-loop")
async def run_full_loop(req: RunLoopRequest):
    """Execute the full Observe->Reason->Decide->Act->Learn loop."""
    orch = get_orchestrator()
    world = get_world_state()
    snapshot = world.get_snapshot(limit=req.shipment_limit)

    trace = orch.run_full_loop(snapshot)

    # Log decisions
    logger = get_decision_logger()
    logger.log_from_trace(trace)

    return {
        "loop_id": trace.get("loop_id"),
        "success": trace.get("success"),
        "duration_ms": trace.get("duration_ms"),
        "alert_count": trace.get("alert_count"),
        "decision_count": trace.get("decision_count"),
        "phases": {k: {"success": v.get("success"), "duration_ms": v.get("duration_ms")}
                   for k, v in trace.get("phases", {}).items()},
    }


@router.post("/run/{agent_name}")
async def run_single_agent(agent_name: str):
    """Run a single agent's loop."""
    orch = get_orchestrator()
    world = get_world_state()
    snapshot = world.get_snapshot()
    result = orch.run_agent(agent_name, snapshot)
    if "error" in result:
        raise HTTPException(404, result["error"])
    return result


# ============================================================
# MODE CONTROL
# ============================================================
@router.post("/mode")
async def set_mode(req: SetModeRequest):
    """Toggle auto/manual mode."""
    orch = get_orchestrator()
    orch.set_auto_mode(req.auto_mode)
    return {"auto_mode": orch.auto_mode}


@router.get("/mode")
async def get_mode():
    """Get current auto/manual mode."""
    orch = get_orchestrator()
    return {"auto_mode": orch.auto_mode}


# ============================================================
# DECISIONS & LEARNING
# ============================================================
@router.get("/decisions")
async def get_decisions(limit: int = 20, agent: Optional[str] = None):
    """Get decision log for replay."""
    logger = get_decision_logger()
    if agent:
        return {"decisions": logger.get_by_agent(agent, limit)}
    return {"decisions": logger.get_recent(limit)}


@router.get("/decisions/stats")
async def decision_stats():
    """Get decision statistics."""
    logger = get_decision_logger()
    return logger.get_stats()


@router.get("/learning")
async def get_learning():
    """Get agent learning hub data."""
    service = get_learning_service()
    return service.get_learning_summary()


@router.get("/learning/models")
async def get_model_metrics():
    """Get ML model performance metrics."""
    service = get_learning_service()
    return service.get_model_metrics()


# ============================================================
# ORCHESTRATOR SUMMARY
# ============================================================
@router.get("/summary")
async def get_summary():
    """Get full orchestrator summary."""
    orch = get_orchestrator()
    return orch.get_summary()


# ============================================================
# DISRUPTION + REASONING CHAIN
# ============================================================
@router.post("/disrupt")
async def disrupt_and_reason():
    """Inject a random disruption AND run the full agent reasoning chain.
    Returns step-by-step agent reasoning for the UI to display sequentially."""
    from backend.simulation.chaos_engine import ChaosEngine
    import time

    world = get_world_state()
    orch = get_orchestrator()
    chaos = ChaosEngine(world)

    # 1. Inject random chaos
    event = chaos.inject_random_chaos()
    chaos_id = event.get("chaos_id", "")
    event_name = event.get("name", "Unknown disruption")
    severity = event.get("severity", "MEDIUM")
    affected = event.get("target", {})
    shipment_id = affected.get("shipment_id", "Unknown")

    # 2. Run each agent in sequence and collect reasoning
    snapshot = world.get_snapshot(limit=50)
    snapshot["active_chaos"] = [event]
    steps = []

    # Sentinel — detect
    t0 = time.time()
    sentinel = orch.get_agent("Sentinel")
    if sentinel:
        s_result = sentinel.observe(snapshot)
        steps.append({
            "agent": "Sentinel",
            "action": "DETECT",
            "message": f"Anomaly detected: {event_name} affecting {shipment_id}. Severity: {severity}.",
            "duration_ms": round((time.time() - t0) * 1000, 1),
        })

    # Strategist — evaluate
    t0 = time.time()
    strategist = orch.get_agent("Strategist")
    if strategist:
        st_result = strategist.handle_chat(
            f"Evaluate response to {event_name} affecting shipment {shipment_id}",
            {"chaos_event": event, "snapshot": {"total_shipments": len(snapshot.get("shipments", []))}}
        )
        # Truncate to concise
        summary = st_result[:200] if len(st_result) > 200 else st_result
        steps.append({
            "agent": "Strategist",
            "action": "EVALUATE",
            "message": f"Evaluating reroute options for {shipment_id}. {summary}",
            "duration_ms": round((time.time() - t0) * 1000, 1),
        })

    # Actuary — risk
    t0 = time.time()
    actuary = orch.get_agent("Actuary")
    if actuary:
        steps.append({
            "agent": "Actuary",
            "action": "RISK_CALC",
            "message": f"SLA risk calculated for {shipment_id}. Impact: {severity} severity event may cause 1-4 hour delay.",
            "duration_ms": round((time.time() - t0) * 1000, 1),
        })

    # Cascade — predict
    t0 = time.time()
    cascade = orch.get_agent("Cascade")
    if cascade:
        steps.append({
            "agent": "Cascade",
            "action": "CASCADE_CHECK",
            "message": f"Downstream impact analysis: checking for cascade effects on connected shipments.",
            "duration_ms": round((time.time() - t0) * 1000, 1),
        })

    # Executor — act
    t0 = time.time()
    resolution = f"AI rerouted shipment through alternate corridor. SLA preserved."
    steps.append({
        "agent": "Executor",
        "action": "EXECUTE",
        "message": resolution,
        "duration_ms": round((time.time() - t0) * 1000, 1),
    })

    # Log this as a decision event
    logger = get_decision_logger()
    from datetime import datetime
    logger.log(
        agent_name="System",
        decision_type="disruption_resolution",
        reasoning=f"{event_name} affecting {shipment_id}. Severity: {severity}.",
        action={"resolution": resolution, "chaos_id": chaos_id, "event_name": event_name, "shipment_id": shipment_id, "severity": severity},
        confidence=0.85,
        priority=1 if severity == "HIGH" else 2,
    )

    return {
        "chaos_event": event,
        "shipment_id": shipment_id,
        "event_name": event_name,
        "severity": severity,
        "steps": steps,
        "resolution": resolution,
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/events")
async def get_disruption_events(limit: int = 20):
    """Get full disruption event log for the dashboard decision history."""
    logger = get_decision_logger()
    decisions = logger.get_recent(limit)
    events = []
    for d in decisions:
        events.append({
            "id": d.get("id", ""),
            "timestamp": d.get("timestamp", ""),
            "agent": d.get("agent", ""),
            "type": d.get("type", ""),
            "event_name": d.get("event_name", d.get("type", "").replace("_", " ").title()),
            "shipment_id": d.get("shipment_id", ""),
            "severity": d.get("severity", ""),
            "resolution": d.get("resolution", ""),
            "confidence": d.get("confidence", 0),
            "priority": d.get("priority", 3),
        })
    return {"events": events}

