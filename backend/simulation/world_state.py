"""
STRYDER AI - World State Manager
==================================
Central in-memory state manager for the logistics simulation.
Maintains the live state of all entities: shipments, carriers,
warehouses, routes, and simulation clock.
"""

import time
import threading
from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path

import pandas as pd
import numpy as np


class WorldState:
    """
    In-memory world state for the STRYDER AI simulation.
    Thread-safe singleton that holds all live entity data.
    """

    def __init__(self):
        self.shipments: list[dict] = []
        self.carriers: list[dict] = []
        self.warehouses: list[dict] = []
        self.events: list[dict] = []
        self.chaos_events: list[dict] = []

        # Simulation clock
        self.sim_time = datetime(2026, 3, 7, 0, 0, 0)
        self.sim_speed = 1.0  # 1x real-time
        self.sim_running = False

        # Indexes for fast lookup
        self._shipment_index: dict = {}
        self._carrier_index: dict = {}
        self._warehouse_index: dict = {}

        # Thread safety
        self._lock = threading.Lock()

        # Stats
        self.tick_count = 0
        self.last_update = None

    @staticmethod
    def _sanitize_records(records: list[dict]) -> list[dict]:
        """Replace NaN/inf with None for JSON serialization."""
        import math
        for rec in records:
            for k, v in rec.items():
                if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                    rec[k] = None
        return records

    def load_synthetic_data(self, data_dir: Optional[str] = None):
        """Load synthetic data from CSV files into world state."""
        if data_dir is None:
            data_dir = Path(__file__).resolve().parent.parent.parent / "data" / "synthetic"
        else:
            data_dir = Path(data_dir)

        with self._lock:
            # Load shipments
            ship_file = data_dir / "shipments.csv"
            if ship_file.exists():
                df = pd.read_csv(ship_file)
                self.shipments = self._sanitize_records(df.where(df.notna(), None).to_dict("records"))
                self._shipment_index = {s["shipment_id"]: i for i, s in enumerate(self.shipments)}

            # Load carriers
            car_file = data_dir / "carriers.csv"
            if car_file.exists():
                df = pd.read_csv(car_file)
                self.carriers = self._sanitize_records(df.where(df.notna(), None).to_dict("records"))
                self._carrier_index = {c["carrier_id"]: i for i, c in enumerate(self.carriers)}

            # Load warehouses
            wh_file = data_dir / "warehouses.csv"
            if wh_file.exists():
                df = pd.read_csv(wh_file)
                self.warehouses = self._sanitize_records(df.where(df.notna(), None).to_dict("records"))
                self._warehouse_index = {w["warehouse_id"]: i for i, w in enumerate(self.warehouses)}

            # Load events
            ev_file = data_dir / "shipment_events.csv"
            if ev_file.exists():
                df = pd.read_csv(ev_file)
                self.events = self._sanitize_records(df.where(df.notna(), None).to_dict("records"))

            self.last_update = datetime.now().isoformat()

    # ============================================================
    # ENTITY ACCESSORS
    # ============================================================
    def get_shipment(self, shipment_id: str) -> Optional[dict]:
        with self._lock:
            idx = self._shipment_index.get(shipment_id)
            return self.shipments[idx] if idx is not None else None

    def get_carrier(self, carrier_id: str) -> Optional[dict]:
        with self._lock:
            idx = self._carrier_index.get(carrier_id)
            return self.carriers[idx] if idx is not None else None

    def get_warehouse(self, warehouse_id: str) -> Optional[dict]:
        with self._lock:
            idx = self._warehouse_index.get(warehouse_id)
            return self.warehouses[idx] if idx is not None else None

    def get_shipments_by_status(self, status: str) -> list:
        with self._lock:
            return [s for s in self.shipments if s.get("status") == status]

    def get_shipments_by_carrier(self, carrier_id: str) -> list:
        with self._lock:
            return [s for s in self.shipments if s.get("carrier_id") == carrier_id]

    # ============================================================
    # ENTITY MUTATIONS
    # ============================================================
    def update_shipment(self, shipment_id: str, updates: dict):
        with self._lock:
            idx = self._shipment_index.get(shipment_id)
            if idx is not None:
                self.shipments[idx].update(updates)

    def update_carrier(self, carrier_id: str, updates: dict):
        with self._lock:
            idx = self._carrier_index.get(carrier_id)
            if idx is not None:
                self.carriers[idx].update(updates)

    def update_warehouse(self, warehouse_id: str, updates: dict):
        with self._lock:
            idx = self._warehouse_index.get(warehouse_id)
            if idx is not None:
                self.warehouses[idx].update(updates)

    def add_event(self, event: dict):
        with self._lock:
            self.events.append(event)

    def add_chaos_event(self, event: dict):
        with self._lock:
            self.chaos_events.append(event)

    # ============================================================
    # SIMULATION TICK
    # ============================================================
    def tick(self, delta_minutes: float = 15):
        """Advance simulation by delta_minutes. Updates shipment progress."""
        with self._lock:
            self.sim_time += timedelta(minutes=delta_minutes * self.sim_speed)
            self.tick_count += 1

            for ship in self.shipments:
                if ship.get("status") == "IN_TRANSIT":
                    progress = ship.get("progress_pct", 0)
                    expected_hours = ship.get("expected_hours", 48)
                    if expected_hours > 0:
                        increment = (delta_minutes / 60) / expected_hours * 100
                        new_progress = min(100, progress + increment)
                        ship["progress_pct"] = round(new_progress, 1)
                        if new_progress >= 100:
                            ship["status"] = "DELIVERED"
                            ship["actual_delivery"] = self.sim_time.isoformat()

            self.last_update = datetime.now().isoformat()

    # ============================================================
    # SNAPSHOT
    # ============================================================
    def get_snapshot(self, limit: int = 50) -> dict:
        """Get current world state snapshot for agents."""
        with self._lock:
            return {
                "shipments": self.shipments[:limit],
                "carriers": self.carriers,
                "warehouses": self.warehouses,
                "sim_time": self.sim_time.isoformat(),
                "tick_count": self.tick_count,
                "chaos_events": self.chaos_events[-10:],
            }

    def get_stats(self) -> dict:
        """Get summary statistics."""
        with self._lock:
            status_counts = {}
            for s in self.shipments:
                st = s.get("status", "UNKNOWN")
                status_counts[st] = status_counts.get(st, 0) + 1

            return {
                "total_shipments": len(self.shipments),
                "total_carriers": len(self.carriers),
                "total_warehouses": len(self.warehouses),
                "total_events": len(self.events),
                "total_chaos_events": len(self.chaos_events),
                "shipment_statuses": status_counts,
                "sim_time": self.sim_time.isoformat(),
                "tick_count": self.tick_count,
                "last_update": self.last_update,
            }


# ============================================================
# SINGLETON
# ============================================================
_world: Optional[WorldState] = None


def get_world_state() -> WorldState:
    """Get or create the singleton world state."""
    global _world
    if _world is None:
        _world = WorldState()
        _world.load_synthetic_data()
    return _world
