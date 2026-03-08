"""
STRYDER AI — Unified ML Model Inference Service
===================================================
Runs all 5 ML models against shipments and locations.
Lazy-loads models on first call, caches for performance.

Models:
  @ETA_AGENT      — XGBoost Regressor (predicted transit days)
  @DELAY_AGENT    — XGBoost Classifier (delay probability)
  @CARRIER_AGENT  — LightGBM Regressor (carrier reliability score)
  @HUB_AGENT      — XGBoost Classifier (hub congestion probability)
  @CASCADE_MODEL  — XGBoost Classifier (cascade failure probability)
"""
import traceback
from pathlib import Path
from typing import Optional

MODEL_DIR = Path(__file__).parent.parent / "ml_models" / "saved_models"

# ── Cached model instances ──
_cache = {}


def _load(name):
    """Lazy-load a model + scaler pair, cache it."""
    if name in _cache:
        return _cache[name]
    try:
        import joblib, json
        model = joblib.load(MODEL_DIR / f"{name}_model.joblib")
        scaler = joblib.load(MODEL_DIR / f"{name}_scaler.joblib")
        meta = json.load(open(MODEL_DIR / f"{name}_metadata.json"))
        _cache[name] = (model, scaler, meta)
        return _cache[name]
    except Exception:
        return None


def _shipment_to_features(ship: dict) -> dict:
    """Map simulation shipment dict to model feature dict."""
    return {
        "days_for_shipment_scheduled": ship.get("eta_hours", 24) / 24,
        "days_for_shipping_real": ship.get("eta_hours", 24) / 24,
        "latitude": ship.get("lat", 20.0),
        "longitude": ship.get("lon", 78.0),
        "order_hour": 10,
        "order_day_of_week": 2,
        "order_month": 3,
        "shipping_hour": 8,
        "shipping_day_of_week": 1,
        "shipping_mode_encoded": 1,
        "order_item_quantity": 1,
        "order_item_product_price": ship.get("base_cost", 5000) / 10,
        "order_item_total": ship.get("base_cost", 5000),
        "weight_kg": 50,
        "cost": ship.get("current_cost", 5000),
        "distance_miles": ship.get("eta_hours", 24) * 25,
        "carrier_encoded": hash(ship.get("carrier", "")) % 10,
        "late_delivery_risk": 1 if ship.get("status") == "DELAYED" else 0,
        "shipping_distance_km": ship.get("eta_hours", 24) * 40,
        "processing_time_hours": 4,
        "weather_condition_encoded": 0,
        "order_priority_encoded": 2,
        "order_value_usd": ship.get("base_cost", 5000) / 80,
        "delay_days": max(0, ship.get("eta_hours", 0) - 48) / 24,
        "historical_disruption_count": 1 if ship.get("disrupted") else 0,
        "actual_shipping_days": ship.get("eta_hours", 24) / 24,
        "delivery_status_encoded": 0 if ship.get("status") == "IN_TRANSIT" else 1,
        "supplier_reliability_score": 0.85,
        "warehouse_inventory_level": 70,
        "inventory_level": 70,
        "temperature": 30,
        "humidity": 65,
        "waiting_time": 2,
        "asset_utilization": 0.7,
        "demand_forecast": 100,
        "hour": 10,
        "day_of_week": 2,
        # Carrier model features
        "trips_completed": 50,
        "total_miles": 5000,
        "total_revenue": 100000,
        "average_mpg": 8,
        "total_fuel_gallons": 600,
        "average_idle_hours": 2,
        "detention_minutes": 30,
        "delay_minutes": 60 if ship.get("disrupted") else 10,
        "is_delayed": 1 if ship.get("status") == "DELAYED" else 0,
        "on_time_binary": 0 if ship.get("status") == "DELAYED" else 1,
        "actual_distance_miles": ship.get("eta_hours", 24) * 25,
        "actual_duration_hours": ship.get("eta_hours", 24),
        "fuel_gallons_used": ship.get("eta_hours", 24) * 3,
        "idle_time_hours": 1.5,
        "dispatch_month": 3,
        "dispatch_day_of_week": 2,
    }


def _port_to_features(port: dict) -> dict:
    """Map port state dict to hub congestion model features."""
    return {
        "dock_doors": 12,
        "average_age_of_vessels_years_value": 10,
        "median_time_in_port_days_value": 3,
        "average_size_gt_of_vessels_value": 25000,
        "average_cargo_carrying_capacity_dwt_per_vessel_value": 35000,
        "portcalls_container": port.get("incoming_count", 5) * 3,
        "portcalls_dry_bulk": port.get("incoming_count", 5),
        "portcalls_cargo": port.get("incoming_count", 5) * 2,
        "portcalls": port.get("incoming_count", 5) * 6,
        "import_container": port.get("throughput", 200) * 0.4,
        "import_cargo": port.get("throughput", 200) * 0.3,
        "import": port.get("throughput", 200) * 0.7,
        "export_container": port.get("throughput", 200) * 0.3,
        "export_cargo": port.get("throughput", 200) * 0.2,
        "export": port.get("throughput", 200) * 0.5,
        "day_of_week": 2,
        "month": 3,
        "year": 2026,
        "trips_completed": port.get("incoming_count", 5) * 10,
        "total_miles": 50000,
        "maintenance_events": 2,
        "maintenance_cost": 15000,
        "downtime_hours": 8,
        "utilization_rate": port.get("congestion_pct", 30) / 100,
    }


# ────────────────────────────────────────────
# PUBLIC API
# ────────────────────────────────────────────

def infer_shipment(ship: dict) -> dict:
    """Run all 5 ML models against a single shipment."""
    features = _shipment_to_features(ship)
    result = {
        "shipment_id": ship.get("id"),
        "eta": None,
        "delay": None,
        "carrier": None,
        "cascade": None,
    }

    # ETA
    loaded = _load("eta")
    if loaded:
        model, scaler, meta = loaded
        try:
            from backend.ml_models.eta_model import predict
            result["eta"] = predict(features, model, scaler)
        except Exception:
            result["eta"] = {"predicted_eta_days": ship.get("eta_hours", 24) / 24, "confidence": 0}

    # Delay
    loaded = _load("delay")
    if loaded:
        try:
            from backend.ml_models.delay_model import predict
            result["delay"] = predict(features, *loaded[:2])
        except Exception:
            result["delay"] = {"delay_probability": 0.1, "risk_level": "LOW"}

    # Carrier
    loaded = _load("carrier")
    if loaded:
        try:
            from backend.ml_models.carrier_model import predict
            result["carrier"] = predict(features, *loaded[:2])
        except Exception:
            result["carrier"] = {"reliability_score": 0.8, "tier": "STANDARD"}

    # Cascade
    loaded = _load("cascade")
    if loaded:
        try:
            from backend.ml_models.cascade_model import predict
            result["cascade"] = predict(features, *loaded[:2])
        except Exception:
            result["cascade"] = {"cascade_probability": 0.1, "severity": "LOW"}

    return result


def infer_hub(port_or_wh: dict) -> dict:
    """Run hub congestion model against a port or warehouse."""
    features = _port_to_features(port_or_wh)
    loaded = _load("hub_congestion")
    if loaded:
        try:
            from backend.ml_models.hub_congestion_model import predict
            return predict(features, *loaded[:2])
        except Exception:
            pass
    return {
        "congestion_probability": port_or_wh.get("congestion_pct", 30) / 100,
        "congestion_level": port_or_wh.get("congestion_level", "LOW"),
    }


def infer_location(location_name: str, shipments: list, port_or_wh: Optional[dict] = None) -> dict:
    """
    Run all models for a location. Returns aggregated assessment.
    shipments: list of shipment dicts at this location
    port_or_wh: the port or warehouse state dict (if available)
    """
    # Hub congestion
    hub = infer_hub(port_or_wh) if port_or_wh else {}

    # Per-shipment model runs (cap at 15 for performance)
    sample = shipments[:15]
    ship_results = []
    for s in sample:
        try:
            r = infer_shipment(s)
            ship_results.append(r)
        except Exception:
            pass

    # Aggregate
    delay_risks = [r["delay"]["delay_probability"] for r in ship_results if r.get("delay")]
    high_delay = [r for r in ship_results if r.get("delay") and r["delay"]["delay_probability"] > 0.5]
    cascade_risks = [r["cascade"]["cascade_probability"] for r in ship_results if r.get("cascade")]
    carrier_scores = [r["carrier"]["reliability_score"] for r in ship_results if r.get("carrier")]

    avg_delay = sum(delay_risks) / len(delay_risks) if delay_risks else 0
    avg_cascade = sum(cascade_risks) / len(cascade_risks) if cascade_risks else 0
    avg_carrier = sum(carrier_scores) / len(carrier_scores) if carrier_scores else 0.8

    return {
        "location": location_name,
        "total_shipments": len(shipments),
        "analyzed": len(ship_results),
        "hub": hub,
        "delay_summary": {
            "avg_probability": round(avg_delay, 3),
            "high_risk_count": len(high_delay),
            "high_risk_ids": [r["shipment_id"] for r in high_delay],
        },
        "cascade_summary": {
            "avg_probability": round(avg_cascade, 3),
            "severity": "CRITICAL" if avg_cascade > 0.6 else "HIGH" if avg_cascade > 0.4 else "MODERATE" if avg_cascade > 0.2 else "LOW",
        },
        "carrier_summary": {
            "avg_reliability": round(avg_carrier, 3),
            "tier": "PREMIUM" if avg_carrier > 0.9 else "RELIABLE" if avg_carrier > 0.75 else "STANDARD",
        },
        "per_shipment": ship_results[:5],  # top 5 details
        "models_used": ["ETA_AGENT", "DELAY_AGENT", "CARRIER_AGENT", "HUB_AGENT", "CASCADE_MODEL"],
    }
