"""
STRYDER AI — Supabase Persistence Layer
==========================================
Async-compatible Supabase client for syncing simulation state.
Uses service_role key for full CRUD access.
"""
import os
import logging
import threading
from typing import Optional

log = logging.getLogger("stryder.supabase")

# Try to import supabase — graceful fallback if not installed
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    log.warning("[SUPABASE] supabase-py not installed. Running without persistence.")


_client: Optional["Client"] = None
_lock = threading.Lock()


def get_supabase() -> Optional["Client"]:
    """Get or create the Supabase client singleton."""
    global _client
    if not SUPABASE_AVAILABLE:
        return None
    if _client is not None:
        return _client

    with _lock:
        if _client is not None:
            return _client

        url = os.environ.get("NEXT_PUBLIC_SUPABASE_URL", "")
        key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

        if not url or not key:
            log.warning("[SUPABASE] Missing NEXT_PUBLIC_SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")
            return None

        try:
            _client = create_client(url, key)
            log.info(f"[SUPABASE] Connected to {url}")
            return _client
        except Exception as e:
            log.error(f"[SUPABASE] Connection failed: {e}")
            return None


# ═══════════════════════════════════════════
# SYNC OPERATIONS (fire-and-forget writes)
# ═══════════════════════════════════════════

def sync_shipments(shipments: list[dict]):
    """Upsert all shipment records to Supabase."""
    sb = get_supabase()
    if not sb:
        return
    try:
        rows = [{
            "id": s["id"],
            "origin_city": s.get("origin", ""),
            "origin_id": s.get("origin_id"),
            "destination_city": s.get("destination", ""),
            "destination_id": s.get("destination_id"),
            "carrier": s.get("carrier", ""),
            "cargo": s.get("cargo"),
            "status": s.get("status", "IN_TRANSIT"),
            "eta_hours": s.get("eta_hours", 0),
            "base_cost": s.get("base_cost", 0),
            "current_cost": round(s.get("current_cost", 0)),
            "delay_penalty_per_hour": s.get("delay_penalty_per_hour", 0),
            "risk": s.get("risk", "Low"),
            "latitude": s.get("lat"),
            "longitude": s.get("lon"),
            "progress": s.get("progress", 0),
            "disrupted": s.get("disrupted", False),
            "disruption_id": s.get("disruption_id"),
            "priority": s.get("priority"),
        } for s in shipments]
        sb.table("shipments").upsert(rows, on_conflict="id").execute()
    except Exception as e:
        log.error(f"[SUPABASE] sync_shipments error: {e}")


def sync_ports(ports: list[dict]):
    """Upsert port states."""
    sb = get_supabase()
    if not sb:
        return
    try:
        rows = [{
            "id": p["id"],
            "name": p["name"],
            "city": p["name"].replace(" Port", ""),
            "latitude": p["lat"],
            "longitude": p["lon"],
            "congestion_level": p.get("congestion_level", "LOW"),
            "congestion_pct": p.get("congestion_pct", 20),
            "capacity": p.get("capacity", 5000),
            "throughput": p.get("throughput", 200),
            "incoming_count": p.get("incoming_count", 0),
        } for p in ports]
        sb.table("ports").upsert(rows, on_conflict="id").execute()
    except Exception as e:
        log.error(f"[SUPABASE] sync_ports error: {e}")


def sync_warehouses(warehouses: list[dict]):
    """Upsert warehouse states."""
    sb = get_supabase()
    if not sb:
        return
    try:
        rows = [{
            "id": w["id"],
            "name": w["name"],
            "city": w["name"].replace(" Warehouse", ""),
            "latitude": w["lat"],
            "longitude": w["lon"],
            "capacity": w.get("capacity", 10000),
            "utilization_pct": w.get("utilization_pct", 40),
            "incoming_count": w.get("incoming_count", 0),
        } for w in warehouses]
        sb.table("warehouses").upsert(rows, on_conflict="id").execute()
    except Exception as e:
        log.error(f"[SUPABASE] sync_warehouses error: {e}")


def log_disruption(disruption: dict):
    """Insert a disruption event."""
    sb = get_supabase()
    if not sb:
        return
    try:
        sb.table("simulation_events").insert({
            "event_type": disruption.get("name", "disruption"),
            "event_name": disruption.get("name"),
            "severity": disruption.get("severity", "MEDIUM"),
            "location": disruption.get("location", ""),
            "location_id": disruption.get("location_id"),
            "eta_impact_h": disruption.get("eta_impact_h", 0),
            "affected_shipments": disruption.get("affected_ids", []),
            "affected_count": disruption.get("affected_count", 0),
            "resolved": disruption.get("resolved", False),
            "scenario_type": disruption.get("scenario_type"),
        }).execute()
    except Exception as e:
        log.error(f"[SUPABASE] log_disruption error: {e}")


def log_scenario(scenario: dict):
    """Insert a scenario history entry."""
    sb = get_supabase()
    if not sb:
        return
    try:
        sb.table("scenario_history").insert({
            "scenario_type": scenario.get("type", ""),
            "location": scenario.get("location", ""),
            "affected_count": scenario.get("affected_count", 0),
            "description": scenario.get("description", ""),
        }).execute()
    except Exception as e:
        log.error(f"[SUPABASE] log_scenario error: {e}")


def log_learning(agent_name: str, message: str, sim_time: str = ""):
    """Insert an agent learning log entry."""
    sb = get_supabase()
    if not sb:
        return
    try:
        sb.table("agent_learning_logs").insert({
            "agent_name": agent_name,
            "log_message": message,
            "sim_time": sim_time,
        }).execute()
    except Exception as e:
        log.error(f"[SUPABASE] log_learning error: {e}")


def log_cascade_alert(alert: dict):
    """Insert a cascade alert."""
    sb = get_supabase()
    if not sb:
        return
    try:
        sb.table("cascade_alerts").insert({
            "alert_type": alert.get("type", ""),
            "location": alert.get("location", ""),
            "location_id": alert.get("location_id"),
            "confidence": alert.get("confidence", 0),
            "impact_count": alert.get("impact_count", 0),
            "suggested_action": alert.get("suggestion", ""),
        }).execute()
    except Exception as e:
        log.error(f"[SUPABASE] log_cascade_alert error: {e}")


def log_metric(name: str, value: float = 0, text: str = "", metric_type: str = "info", sim_time: str = ""):
    """Insert a system metric."""
    sb = get_supabase()
    if not sb:
        return
    try:
        sb.table("system_metrics").insert({
            "metric_name": name,
            "metric_value": value,
            "metric_text": text,
            "metric_type": metric_type,
            "sim_time": sim_time,
        }).execute()
    except Exception as e:
        log.error(f"[SUPABASE] log_metric error: {e}")


def save_agent_memory(memory_type: str, content: dict, agent_name: str = "System"):
    """Upsert agent memory entry."""
    sb = get_supabase()
    if not sb:
        return
    try:
        import json
        # Check if exists
        existing = sb.table("agent_memory").select("id").eq("memory_type", memory_type).eq("agent_name", agent_name).execute()
        if existing.data:
            sb.table("agent_memory").update({"content": content}).eq("id", existing.data[0]["id"]).execute()
        else:
            sb.table("agent_memory").insert({
                "memory_type": memory_type,
                "content": content,
                "agent_name": agent_name,
            }).execute()
    except Exception as e:
        log.error(f"[SUPABASE] save_agent_memory error: {e}")


def clear_simulation_data():
    """Clear all simulation data for a fresh reset."""
    sb = get_supabase()
    if not sb:
        return
    try:
        sb.table("shipments").delete().neq("id", -1).execute()
        sb.table("simulation_events").delete().neq("id", -1).execute()
        sb.table("scenario_history").delete().neq("id", -1).execute()
        sb.table("cascade_alerts").delete().neq("id", -1).execute()
        sb.table("agent_learning_logs").delete().neq("id", -1).execute()
        sb.table("system_metrics").delete().neq("id", -1).execute()
        log.info("[SUPABASE] Simulation data cleared")
    except Exception as e:
        log.error(f"[SUPABASE] clear_simulation_data error: {e}")
