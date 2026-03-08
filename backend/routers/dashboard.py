"""
STRYDER AI - Dashboard Router
================================
Endpoints for the main dashboard: overview, route data, hubs.
"""

from fastapi import APIRouter

from backend.simulation.world_state import get_world_state
from backend.simulation.route_engine import get_route_engine
from backend.agents.orchestrator import get_orchestrator
from backend.services.decision_logger import get_decision_logger

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/overview")
async def dashboard_overview():
    """Get full dashboard overview data."""
    world = get_world_state()
    orch = get_orchestrator()
    logger = get_decision_logger()

    stats = world.get_stats()
    agent_statuses = orch.get_all_statuses()
    decision_stats = logger.get_stats()

    return {
        "simulation": stats,
        "agents": agent_statuses,
        "decisions": decision_stats,
        "auto_mode": orch.auto_mode,
    }


@router.get("/map/hubs")
async def get_map_hubs():
    """Get all hubs for map rendering."""
    engine = get_route_engine()
    return {"hubs": engine.get_all_hubs()}


@router.get("/map/routes")
async def get_map_routes():
    """Get all routes as GeoJSON for map."""
    engine = get_route_engine()
    return engine.get_all_routes_geojson()


@router.get("/map/network")
async def get_network_summary():
    """Get network summary."""
    engine = get_route_engine()
    return engine.get_graph_summary()


@router.get("/map/route/{origin}/{destination}")
async def calculate_route(origin: str, destination: str):
    """Calculate route between two hubs."""
    engine = get_route_engine()
    result = engine.calculate_route(origin, destination)
    return result


@router.get("/map/animate/{origin}/{destination}")
async def get_animation(origin: str, destination: str, points: int = 50):
    """Get animation points for a route."""
    engine = get_route_engine()
    pts = engine.generate_route_animation_points(origin, destination, points)
    return {"points": pts, "count": len(pts)}
