"""
STRYDER AI - FastAPI Backend Entrypoint
=========================================
Main application with all routers, CORS, and startup initialization.
Run: uvicorn backend.main:app --reload --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import CORS_ORIGINS, BACKEND_HOST, BACKEND_PORT
from backend.routers import chat, simulation, agents, models, dashboard, ops

# ============================================================
# APP INITIALIZATION
# ============================================================
app = FastAPI(
    title="STRYDER AI",
    description="Agentic Multi-Agent Logistics Intelligence Platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — regex-based to support Vercel preview deployments
_explicit_origins = list(set(CORS_ORIGINS) | {
    "http://localhost:3000",
    "http://localhost:5173",
    "https://stryder-ai.vercel.app",
    "https://stryder-ai-gaarths-projects.vercel.app",
})
# Regex covers all Vercel preview builds: stryder-ai-*.vercel.app
_origin_regex = r"https://stryder-ai(-[a-z0-9-]+)?\.vercel\.app|http://localhost:(3000|5173)"

print(f"[STRYDER AI] CORS explicit origins: {sorted(_explicit_origins)}")
print(f"[STRYDER AI] CORS regex: {_origin_regex}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_explicit_origins,
    allow_origin_regex=_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=600,
)

# ============================================================
# REGISTER ROUTERS
# ============================================================
app.include_router(chat.router)
app.include_router(simulation.router)
app.include_router(agents.router)
app.include_router(models.router)
app.include_router(dashboard.router)
app.include_router(ops.router)


# ============================================================
# ROOT ENDPOINTS
# ============================================================
@app.get("/")
async def root():
    return {
        "name": "STRYDER AI",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    from backend.simulation.world_state import get_world_state
    from backend.agents.orchestrator import get_orchestrator

    world = get_world_state()
    orch = get_orchestrator()

    print("[STRYDER AI] SYSTEM CONNECTED — healthcheck hit")

    return {
        "status": "healthy",
        "simulation": {
            "shipments": len(world.shipments),
            "carriers": len(world.carriers),
            "warehouses": len(world.warehouses),
            "sim_time": world.sim_time.isoformat() if hasattr(world, 'sim_time') and world.sim_time else None,
            "tick_count": getattr(world, 'tick_count', 0),
            "active_chaos": len(getattr(world, 'chaos_events', [])),
        },
        "agents": len(orch.agents),
        "auto_mode": orch.auto_mode,
    }


# ============================================================
# STARTUP EVENT
# ============================================================
@app.on_event("startup")
async def startup():
    """Initialize world state and start background tick loop."""
    from backend.simulation.world_state import get_world_state
    from backend.simulation.ops_state import get_ops_state
    from backend.simulation.tick_loop import start_tick_loop
    world = get_world_state()
    ops = get_ops_state()
    start_tick_loop()
    print(f"[STRYDER AI] World state loaded: {len(world.shipments)} shipments, "
          f"{len(world.carriers)} carriers, {len(world.warehouses)} warehouses")
    print(f"[STRYDER AI] OpsState: {len(ops.shipments)} shipments, tick loop started")

    # Initial sync to Supabase
    try:
        from backend.services.supabase_sync import get_supabase
        sb = get_supabase()
        if sb:
            ops._sync_to_supabase()
            print("[STRYDER AI] Supabase sync: initial state pushed")
        else:
            print("[STRYDER AI] Supabase: not configured (running without persistence)")
    except Exception as e:
        print(f"[STRYDER AI] Supabase: {e}")

    print(f"[STRYDER AI] API ready at http://{BACKEND_HOST}:{BACKEND_PORT}")


# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host=BACKEND_HOST, port=BACKEND_PORT, reload=True)
