"""
STRYDER AI — Background Tick Loop
====================================
Respects simulation controls: paused, speed, movement_scale, frozen.
"""
import threading, time, logging

log = logging.getLogger("stryder.tick_loop")

_thread: threading.Thread | None = None
_running = False


def start_tick_loop():
    global _thread, _running
    if _thread and _thread.is_alive():
        return
    _running = True
    _thread = threading.Thread(target=_loop, daemon=True, name="stryder-tick-loop")
    _thread.start()
    log.info("[TICK LOOP] Started")


def stop_tick_loop():
    global _running
    _running = False
    log.info("[TICK LOOP] Stopped")


BASE_INTERVAL = 3.0  # seconds at 1x speed


def _loop():
    from backend.simulation.ops_state import get_ops_state
    while _running:
        try:
            state = get_ops_state()
            # Skip if paused or frozen
            if not state.sim_paused and not state.sim_frozen and state.auto_mode:
                state.tick(minutes=15)
                state.sentinel_scan()
                state.cascade_predict()
            # Sleep respects speed setting
            interval = max(0.4, BASE_INTERVAL / max(0.25, state.sim_speed))
        except Exception as e:
            log.error(f"[TICK LOOP] Error: {e}")
            interval = BASE_INTERVAL
        time.sleep(interval)
