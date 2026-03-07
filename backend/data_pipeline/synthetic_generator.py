"""
STRYDER AI - Phase 4: Synthetic India Logistics Data Generator
================================================================
Generates India-adapted synthetic logistics data for simulation.
Uses the route engine's hub network to create realistic:
  - Shipments with realistic routes between Indian hubs
  - Carrier profiles with reliability variability
  - Warehouse queue/congestion patterns
  - SLA agreements and customer profiles
  - Shipment timelines with delays and disruptions

Output: CSVs in data/synthetic/ for simulation seeding.
"""

import sys
import random
import uuid
from pathlib import Path
from datetime import datetime, timedelta

import pandas as pd
import numpy as np

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.simulation.route_engine import RouteEngine, INDIA_HUBS

DATA_SYNTHETIC = PROJECT_ROOT / "data" / "synthetic"
DATA_SYNTHETIC.mkdir(parents=True, exist_ok=True)

random.seed(42)
np.random.seed(42)

# ============================================================
# CONFIGURATION
# ============================================================
NUM_SHIPMENTS = 500
NUM_CARRIERS = 30
NUM_CUSTOMERS = 100
NUM_WAREHOUSES = len([h for h in INDIA_HUBS.values() if h["type"] in ("warehouse", "distribution_center")])

CARRIER_NAMES = [
    "BlueDart Express", "Delhivery", "DTDC Express", "Ecom Express",
    "Gati KWE", "TCI Express", "Rivigo", "BlackBuck",
    "Safexpress", "Spoton Logistics", "XpressBees", "Shadowfax",
    "LoadShare", "Porter", "FedEx India", "DHL Supply Chain",
    "Mahindra Logistics", "TVS Supply Chain", "Allcargo Logistics",
    "CJ Darcl", "VRL Logistics", "TCI Freight", "Om Logistics",
    "Sical Logistics", "Continental Carriers", "Shreyas Shipping",
    "Jayem Warehousing", "Future Supply Chain", "Snowman Logistics",
    "IndoSpace Logistics",
]

CARGO_TYPES = ["Electronics", "FMCG", "Pharmaceuticals", "Automotive Parts",
               "Textiles", "Machinery", "Chemicals", "Perishables",
               "E-commerce", "Furniture", "Raw Materials", "Agri Products"]

SLA_TIERS = {
    "PREMIUM": {"max_days": 2, "penalty_per_day": 5000, "priority": 1},
    "EXPRESS": {"max_days": 4, "penalty_per_day": 2000, "priority": 2},
    "STANDARD": {"max_days": 7, "penalty_per_day": 500, "priority": 3},
    "ECONOMY": {"max_days": 14, "penalty_per_day": 100, "priority": 4},
}

DISRUPTION_TYPES = [
    "truck_breakdown", "road_congestion", "warehouse_overflow",
    "customs_delay", "weather_disruption", "driver_unavailable",
    "inventory_mismatch", "fuel_shortage", "accident", "strike",
]


# ============================================================
# GENERATORS
# ============================================================
def generate_carriers() -> pd.DataFrame:
    """Generate carrier profiles with varying reliability."""
    carriers = []
    for i in range(NUM_CARRIERS):
        reliability = np.clip(np.random.beta(5, 2), 0.5, 0.99)  # Most carriers decent
        carriers.append({
            "carrier_id": f"CR{i+1:03d}",
            "name": CARRIER_NAMES[i % len(CARRIER_NAMES)],
            "fleet_size": random.randint(10, 500),
            "reliability_score": round(reliability, 4),
            "avg_delay_hours": round(max(0, np.random.exponential(4) * (1 - reliability)), 2),
            "on_time_rate": round(reliability * 100, 1),
            "cost_per_km": round(random.uniform(8, 25), 2),
            "max_load_kg": random.choice([5000, 10000, 15000, 20000, 25000]),
            "vehicle_type": random.choice(["LCV", "MCV", "HCV", "Container", "Reefer"]),
            "regions_served": random.sample(
                ["North", "South", "East", "West", "Central"],
                k=random.randint(2, 5)
            ),
            "active": True,
        })
    return pd.DataFrame(carriers)


def generate_customers() -> pd.DataFrame:
    """Generate customer profiles with SLA agreements."""
    customers = []
    hub_ids = list(INDIA_HUBS.keys())

    for i in range(NUM_CUSTOMERS):
        sla_tier = random.choices(
            list(SLA_TIERS.keys()),
            weights=[10, 25, 45, 20],
            k=1
        )[0]
        primary_hub = random.choice(hub_ids)
        hub_info = INDIA_HUBS[primary_hub]

        customers.append({
            "customer_id": f"CU{i+1:04d}",
            "company_name": f"Client_{i+1:04d}_{hub_info['city']}",
            "sla_tier": sla_tier,
            "sla_max_days": SLA_TIERS[sla_tier]["max_days"],
            "sla_penalty_per_day": SLA_TIERS[sla_tier]["penalty_per_day"],
            "primary_hub": primary_hub,
            "city": hub_info["city"],
            "lat": hub_info["lat"] + random.uniform(-0.1, 0.1),
            "lon": hub_info["lon"] + random.uniform(-0.1, 0.1),
            "monthly_shipments": random.randint(5, 200),
            "avg_order_value": round(random.uniform(5000, 500000), 2),
            "priority_score": SLA_TIERS[sla_tier]["priority"],
        })
    return pd.DataFrame(customers)


def generate_warehouses() -> pd.DataFrame:
    """Generate warehouse state data from hub network."""
    warehouses = []
    hub_types = ("warehouse", "distribution_center")

    for hub_id, info in INDIA_HUBS.items():
        if info["type"] not in hub_types:
            continue

        utilization = np.clip(np.random.beta(3, 2), 0.2, 0.95)
        warehouses.append({
            "warehouse_id": hub_id,
            "name": info["name"],
            "city": info["city"],
            "lat": info["lat"],
            "lon": info["lon"],
            "type": info["type"],
            "total_capacity": info["capacity"],
            "current_load": int(info["capacity"] * utilization),
            "utilization_pct": round(utilization * 100, 1),
            "dock_doors": random.randint(4, 20),
            "avg_processing_hours": round(random.uniform(2, 12), 1),
            "queue_length": random.randint(0, 30),
            "inbound_today": random.randint(10, 100),
            "outbound_today": random.randint(10, 100),
            "congestion_level": "HIGH" if utilization > 0.8 else "MEDIUM" if utilization > 0.6 else "LOW",
        })
    return pd.DataFrame(warehouses)


def generate_shipments(carriers: pd.DataFrame, customers: pd.DataFrame) -> pd.DataFrame:
    """Generate shipment records with realistic India logistics patterns."""
    engine = RouteEngine()
    hub_ids = list(INDIA_HUBS.keys())
    # Only use warehouse/DC hubs for origin/destination
    valid_hubs = [h for h, info in INDIA_HUBS.items()
                  if info["type"] in ("warehouse", "distribution_center")]

    shipments = []
    base_date = datetime(2026, 1, 1)

    for i in range(NUM_SHIPMENTS):
        # Pick origin and destination (different hubs)
        origin = random.choice(valid_hubs)
        destination = random.choice([h for h in valid_hubs if h != origin])

        # Get route
        route = engine.calculate_route(origin, destination)
        if "error" in route:
            continue

        # Assign carrier and customer
        carrier = carriers.iloc[random.randint(0, len(carriers) - 1)]
        customer = customers.iloc[random.randint(0, len(customers) - 1)]

        # Timing
        creation_date = base_date + timedelta(days=random.randint(0, 60))
        pickup_date = creation_date + timedelta(hours=random.randint(2, 48))
        expected_travel_hours = route["total_travel_hours"]

        # Add realistic variability
        actual_factor = np.random.lognormal(0, 0.2)  # some faster, some slower
        actual_travel_hours = expected_travel_hours * actual_factor

        # Apply disruption probability
        has_disruption = random.random() < 0.25  # 25% have some disruption
        disruption_type = None
        disruption_delay_hours = 0

        if has_disruption:
            disruption_type = random.choice(DISRUPTION_TYPES)
            disruption_delay_hours = np.random.exponential(8)  # avg 8 hour delay
            actual_travel_hours += disruption_delay_hours

        # Calculate dates
        expected_delivery = pickup_date + timedelta(hours=expected_travel_hours)
        actual_delivery = pickup_date + timedelta(hours=actual_travel_hours)

        # SLA check
        sla_days = customer["sla_max_days"]
        actual_days = (actual_delivery - pickup_date).total_seconds() / 86400
        sla_breached = actual_days > sla_days
        delay_days = max(0, actual_days - sla_days)

        # Status
        now = datetime(2026, 3, 7)
        if actual_delivery < now:
            status = "DELIVERED"
        elif pickup_date < now:
            progress = min(100, (now - pickup_date).total_seconds() / (actual_travel_hours * 3600) * 100)
            status = "IN_TRANSIT"
        else:
            status = "PENDING"
            progress = 0

        # Weight and value
        weight_kg = round(random.uniform(50, 15000), 1)
        cargo_type = random.choice(CARGO_TYPES)
        shipment_value = round(random.uniform(10000, 2000000), 2)

        shipments.append({
            "shipment_id": f"S{i+1:04d}",
            "customer_id": customer["customer_id"],
            "carrier_id": carrier["carrier_id"],
            "carrier_name": carrier["name"],
            "origin_hub": origin,
            "origin_city": INDIA_HUBS[origin]["city"],
            "destination_hub": destination,
            "destination_city": INDIA_HUBS[destination]["city"],
            "cargo_type": cargo_type,
            "weight_kg": weight_kg,
            "shipment_value": shipment_value,
            "sla_tier": customer["sla_tier"],
            "sla_max_days": sla_days,
            "creation_date": creation_date.isoformat(),
            "pickup_date": pickup_date.isoformat(),
            "expected_delivery": expected_delivery.isoformat(),
            "actual_delivery": actual_delivery.isoformat() if status == "DELIVERED" else None,
            "route_distance_km": route["total_distance_km"],
            "expected_hours": round(expected_travel_hours, 2),
            "actual_hours": round(actual_travel_hours, 2) if status == "DELIVERED" else None,
            "route_stops": route["num_stops"],
            "route_path": ",".join(route["path"]),
            "status": status,
            "progress_pct": round(progress, 1) if status == "IN_TRANSIT" else (100 if status == "DELIVERED" else 0),
            "has_disruption": has_disruption,
            "disruption_type": disruption_type,
            "disruption_delay_hours": round(disruption_delay_hours, 2),
            "sla_breached": sla_breached,
            "delay_days": round(delay_days, 2),
            "priority": customer["priority_score"],
        })

    return pd.DataFrame(shipments)


def generate_shipment_events(shipments: pd.DataFrame) -> pd.DataFrame:
    """Generate detailed shipment timeline events."""
    events = []
    event_types = ["CREATED", "PICKUP_SCHEDULED", "PICKED_UP", "IN_TRANSIT",
                   "HUB_ARRIVAL", "HUB_DEPARTURE", "OUT_FOR_DELIVERY", "DELIVERED"]

    for _, ship in shipments.iterrows():
        creation = datetime.fromisoformat(ship["creation_date"])
        pickup = datetime.fromisoformat(ship["pickup_date"])
        route_path = ship["route_path"].split(",")

        # Creation event
        events.append({
            "shipment_id": ship["shipment_id"],
            "event_type": "CREATED",
            "timestamp": creation.isoformat(),
            "hub_id": ship["origin_hub"],
            "description": f"Shipment created at {ship['origin_city']}",
        })

        # Pickup event
        events.append({
            "shipment_id": ship["shipment_id"],
            "event_type": "PICKED_UP",
            "timestamp": pickup.isoformat(),
            "hub_id": ship["origin_hub"],
            "description": f"Picked up by {ship['carrier_name']}",
        })

        # Transit events for each hub in route
        if len(route_path) > 2:
            hours_per_segment = ship["expected_hours"] / (len(route_path) - 1)
            for j, hub in enumerate(route_path[1:-1], 1):
                event_time = pickup + timedelta(hours=hours_per_segment * j)
                events.append({
                    "shipment_id": ship["shipment_id"],
                    "event_type": "HUB_ARRIVAL",
                    "timestamp": event_time.isoformat(),
                    "hub_id": hub,
                    "description": f"Arrived at {INDIA_HUBS.get(hub, {}).get('name', hub)}",
                })

        # Disruption event if applicable
        if ship["has_disruption"]:
            disruption_time = pickup + timedelta(hours=ship["expected_hours"] * random.uniform(0.2, 0.8))
            events.append({
                "shipment_id": ship["shipment_id"],
                "event_type": "DISRUPTION",
                "timestamp": disruption_time.isoformat(),
                "hub_id": random.choice(route_path),
                "description": f"Disruption: {ship['disruption_type']} (+{ship['disruption_delay_hours']:.1f}h delay)",
            })

        # Delivery event
        if ship["status"] == "DELIVERED" and ship["actual_delivery"]:
            events.append({
                "shipment_id": ship["shipment_id"],
                "event_type": "DELIVERED",
                "timestamp": ship["actual_delivery"],
                "hub_id": ship["destination_hub"],
                "description": f"Delivered at {ship['destination_city']}",
            })

    return pd.DataFrame(events)


# ============================================================
# MAIN
# ============================================================
def run_generator():
    """Run the full synthetic data generation pipeline."""
    print("=" * 60)
    print("STRYDER AI - SYNTHETIC DATA GENERATOR")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 60)

    # Generate carriers
    print("\nGenerating carriers...")
    carriers = generate_carriers()
    carriers.to_csv(DATA_SYNTHETIC / "carriers.csv", index=False)
    print(f"  Carriers: {len(carriers)} ({DATA_SYNTHETIC / 'carriers.csv'})")

    # Generate customers
    print("Generating customers...")
    customers = generate_customers()
    customers.to_csv(DATA_SYNTHETIC / "customers.csv", index=False)
    print(f"  Customers: {len(customers)} ({DATA_SYNTHETIC / 'customers.csv'})")

    # Generate warehouses
    print("Generating warehouses...")
    warehouses = generate_warehouses()
    warehouses.to_csv(DATA_SYNTHETIC / "warehouses.csv", index=False)
    print(f"  Warehouses: {len(warehouses)} ({DATA_SYNTHETIC / 'warehouses.csv'})")

    # Generate shipments
    print("Generating shipments...")
    shipments = generate_shipments(carriers, customers)
    shipments.to_csv(DATA_SYNTHETIC / "shipments.csv", index=False)
    print(f"  Shipments: {len(shipments)} ({DATA_SYNTHETIC / 'shipments.csv'})")

    # Generate events timeline
    print("Generating shipment events...")
    events = generate_shipment_events(shipments)
    events.to_csv(DATA_SYNTHETIC / "shipment_events.csv", index=False)
    print(f"  Events: {len(events)} ({DATA_SYNTHETIC / 'shipment_events.csv'})")

    # Summary stats
    print("\n" + "=" * 60)
    print("GENERATION COMPLETE")
    print("=" * 60)
    print(f"\nShipment Statistics:")
    print(f"  Total shipments: {len(shipments)}")
    print(f"  Disrupted: {shipments['has_disruption'].sum()} ({shipments['has_disruption'].mean()*100:.1f}%)")
    print(f"  SLA Breached: {shipments['sla_breached'].sum()} ({shipments['sla_breached'].mean()*100:.1f}%)")
    print(f"  Status: {shipments['status'].value_counts().to_dict()}")
    print(f"  Avg route distance: {shipments['route_distance_km'].mean():.0f} km")
    print(f"  Cargo types: {shipments['cargo_type'].nunique()}")

    print(f"\nCarrier Statistics:")
    print(f"  Total carriers: {len(carriers)}")
    print(f"  Avg reliability: {carriers['reliability_score'].mean():.3f}")

    print(f"\nWarehouse Statistics:")
    print(f"  Total warehouses: {len(warehouses)}")
    print(f"  Avg utilization: {warehouses['utilization_pct'].mean():.1f}%")
    print(f"  Congested hubs: {(warehouses['congestion_level'] == 'HIGH').sum()}")

    # Output file sizes
    print(f"\nOutput Files:")
    for f in sorted(DATA_SYNTHETIC.glob("*.csv")):
        size_kb = f.stat().st_size / 1024
        print(f"  {f.name:<30} {size_kb:>8.1f} KB")

    print(f"\nFinished: {datetime.now().isoformat()}")
    return True


if __name__ == "__main__":
    success = run_generator()
    sys.exit(0 if success else 1)
