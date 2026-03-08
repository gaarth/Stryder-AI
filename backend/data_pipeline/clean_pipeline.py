"""
STRYDER AI - Phase 2: Dataset Cleaning & Preprocessing Pipeline
================================================================
Cleans and preprocesses all Kaggle datasets for ML model training.
Creates model-specific training datasets optimized for:
  - ETA Prediction Model
  - Delay Risk Model
  - Carrier Reliability Model
  - Hub Congestion Model
  - Cascade Failure Model

Output: Cleaned CSVs in data/processed/ ready for model training.
"""

import os
import sys
from pathlib import Path
from datetime import datetime

import pandas as pd
import numpy as np

# ============================================================
# Paths
# ============================================================
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_RAW = PROJECT_ROOT / "data" / "raw" / "kaggle datasets"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
DATA_PROCESSED.mkdir(parents=True, exist_ok=True)


def log(msg: str):
    print(f"  [{datetime.now().strftime('%H:%M:%S')}] {msg}")


# ============================================================
# 1. DataCo Supply Chain Cleaner
# ============================================================
def clean_dataco_supply_chain() -> pd.DataFrame:
    """
    DataCoSupplyChainDataset.csv - 180K rows, 53 cols
    Rich supply chain dataset with delivery, shipping, orders.
    Key columns: Late_delivery_risk, Delivery Status, shipping dates, routes.
    """
    log("Cleaning DataCo Supply Chain...")
    path = DATA_RAW / "DataCo SMART SUPPLY CHAIN FOR BIG DATA ANALYSIS" / "DataCoSupplyChainDataset.csv"
    df = pd.read_csv(path, encoding="latin-1", low_memory=False)

    # Standardize column names
    df.columns = [c.strip().replace(" ", "_").replace("(", "").replace(")", "").lower() for c in df.columns]

    # Parse date columns
    for col in ["order_date_dateorders", "shipping_date_dateorders"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    # Extract temporal features
    if "order_date_dateorders" in df.columns:
        df["order_hour"] = df["order_date_dateorders"].dt.hour
        df["order_day_of_week"] = df["order_date_dateorders"].dt.dayofweek
        df["order_month"] = df["order_date_dateorders"].dt.month

    if "shipping_date_dateorders" in df.columns:
        df["shipping_hour"] = df["shipping_date_dateorders"].dt.hour
        df["shipping_day_of_week"] = df["shipping_date_dateorders"].dt.dayofweek

    # Calculate actual shipping duration
    if "order_date_dateorders" in df.columns and "shipping_date_dateorders" in df.columns:
        df["actual_shipping_days"] = (df["shipping_date_dateorders"] - df["order_date_dateorders"]).dt.total_seconds() / 86400

    # Encode delivery status
    if "delivery_status" in df.columns:
        status_map = {"Advance shipping": 0, "Shipping on time": 1, "Late delivery": 2, "Shipping canceled": 3}
        df["delivery_status_encoded"] = df["delivery_status"].map(status_map).fillna(-1).astype(int)

    # Encode shipping mode
    if "shipping_mode" in df.columns:
        df["shipping_mode_encoded"] = df["shipping_mode"].astype("category").cat.codes

    # Handle missing values - fill numeric with median, categorical with mode
    for col in df.select_dtypes(include=[np.number]).columns:
        if df[col].isnull().sum() > 0:
            df[col] = df[col].fillna(df[col].median())

    for col in df.select_dtypes(include=["object"]).columns:
        if df[col].isnull().sum() > 0:
            df[col] = df[col].fillna(df[col].mode().iloc[0] if len(df[col].mode()) > 0 else "UNKNOWN")

    # Drop low-value columns
    drop_cols = [c for c in df.columns if "email" in c or "password" in c or "zipcode" in c]
    df = df.drop(columns=drop_cols, errors="ignore")

    log(f"  DataCo cleaned: {df.shape[0]} rows x {df.shape[1]} cols")
    return df


# ============================================================
# 2. Logistics Operations Database Cleaner
# ============================================================
def clean_logistics_ops() -> dict:
    """
    14 CSV files covering trips, deliveries, drivers, trucks, routes, etc.
    This is the richest operational dataset.
    """
    log("Cleaning Logistics Operations Database...")
    base = DATA_RAW / "Logistics Operations Database"
    cleaned = {}

    # --- delivery_events ---
    df = pd.read_csv(base / "delivery_events.csv")
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    for col in ["scheduled_datetime", "actual_datetime"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    if "scheduled_datetime" in df.columns and "actual_datetime" in df.columns:
        df["delay_minutes"] = (df["actual_datetime"] - df["scheduled_datetime"]).dt.total_seconds() / 60
        df["is_delayed"] = (df["delay_minutes"] > 0).astype(int)
    if "on_time_flag" in df.columns:
        df["on_time_binary"] = df["on_time_flag"].map({True: 1, False: 0, "True": 1, "False": 0}).fillna(0).astype(int)
    cleaned["delivery_events"] = df
    log(f"  delivery_events: {df.shape}")

    # --- trips ---
    df = pd.read_csv(base / "trips.csv")
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    if "dispatch_date" in df.columns:
        df["dispatch_date"] = pd.to_datetime(df["dispatch_date"], errors="coerce")
        df["dispatch_month"] = df["dispatch_date"].dt.month
        df["dispatch_day_of_week"] = df["dispatch_date"].dt.dayofweek
    for col in df.select_dtypes(include=[np.number]).columns:
        if df[col].isnull().sum() > 0:
            df[col] = df[col].fillna(df[col].median())
    cleaned["trips"] = df
    log(f"  trips: {df.shape}")

    # --- drivers ---
    df = pd.read_csv(base / "drivers.csv")
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    for col in ["hire_date", "termination_date", "date_of_birth"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    if "hire_date" in df.columns:
        df["years_of_service"] = (pd.Timestamp.now() - df["hire_date"]).dt.days / 365.25
    for col in df.select_dtypes(include=[np.number]).columns:
        if df[col].isnull().sum() > 0:
            df[col] = df[col].fillna(df[col].median())
    cleaned["drivers"] = df
    log(f"  drivers: {df.shape}")

    # --- driver_monthly_metrics ---
    df = pd.read_csv(base / "driver_monthly_metrics.csv")
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    cleaned["driver_monthly_metrics"] = df
    log(f"  driver_monthly_metrics: {df.shape}")

    # --- routes ---
    df = pd.read_csv(base / "routes.csv")
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    cleaned["routes"] = df
    log(f"  routes: {df.shape}")

    # --- facilities ---
    df = pd.read_csv(base / "facilities.csv")
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    cleaned["facilities"] = df
    log(f"  facilities: {df.shape}")

    # --- loads ---
    df = pd.read_csv(base / "loads.csv")
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    if "load_date" in df.columns:
        df["load_date"] = pd.to_datetime(df["load_date"], errors="coerce")
    cleaned["loads"] = df
    log(f"  loads: {df.shape}")

    # --- trucks ---
    df = pd.read_csv(base / "trucks.csv")
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    cleaned["trucks"] = df
    log(f"  trucks: {df.shape}")

    # --- trailers ---
    df = pd.read_csv(base / "trailers.csv")
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    cleaned["trailers"] = df
    log(f"  trailers: {df.shape}")

    # --- maintenance_records ---
    df = pd.read_csv(base / "maintenance_records.csv")
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    if "maintenance_date" in df.columns:
        df["maintenance_date"] = pd.to_datetime(df["maintenance_date"], errors="coerce")
    cleaned["maintenance_records"] = df
    log(f"  maintenance_records: {df.shape}")

    # --- fuel_purchases ---
    df = pd.read_csv(base / "fuel_purchases.csv")
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    if "purchase_date" in df.columns:
        df["purchase_date"] = pd.to_datetime(df["purchase_date"], errors="coerce")
    for col in df.select_dtypes(include=[np.number]).columns:
        if df[col].isnull().sum() > 0:
            df[col] = df[col].fillna(df[col].median())
    cleaned["fuel_purchases"] = df
    log(f"  fuel_purchases: {df.shape}")

    # --- safety_incidents ---
    df = pd.read_csv(base / "safety_incidents.csv")
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    if "incident_date" in df.columns:
        df["incident_date"] = pd.to_datetime(df["incident_date"], errors="coerce")
    for col in df.select_dtypes(include=[np.number]).columns:
        if df[col].isnull().sum() > 0:
            df[col] = df[col].fillna(0)
    cleaned["safety_incidents"] = df
    log(f"  safety_incidents: {df.shape}")

    # --- customers ---
    df = pd.read_csv(base / "customers.csv")
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    cleaned["customers"] = df
    log(f"  customers: {df.shape}")

    # --- truck_utilization_metrics ---
    df = pd.read_csv(base / "truck_utilization_metrics.csv")
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    cleaned["truck_utilization_metrics"] = df
    log(f"  truck_utilization_metrics: {df.shape}")

    return cleaned


# ============================================================
# 3. Supply Chain Delay Risk Cleaner
# ============================================================
def clean_delay_risk() -> pd.DataFrame:
    """
    supply_chain_order_fulfillment_delay_risk.csv - 2,800 rows
    Perfect for Delay Risk Model training.
    """
    log("Cleaning Supply Chain Delay Risk...")
    path = DATA_RAW / "Supply Chain Order Delay Risk Analysis" / "supply_chain_order_fulfillment_delay_risk.csv"
    df = pd.read_csv(path)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    if "order_date" in df.columns:
        df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")
        df["order_month"] = df["order_date"].dt.month
        df["order_day_of_week"] = df["order_date"].dt.dayofweek

    # Encode categoricals
    for col in df.select_dtypes(include=["object"]).columns:
        if df[col].nunique() < 30:
            df[f"{col}_encoded"] = df[col].astype("category").cat.codes

    log(f"  delay_risk: {df.shape}")
    return df


# ============================================================
# 4. US Logistics Performance Cleaner
# ============================================================
def clean_us_logistics() -> pd.DataFrame:
    """
    logistics_shipments_dataset.csv - 2,000 rows
    Shipment-level data with carriers, origins, destinations, dates.
    """
    log("Cleaning US Logistics Performance...")
    path = DATA_RAW / "US Logistics Performance Dataset" / "logistics_shipments_dataset.csv"
    df = pd.read_csv(path)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    for col in ["shipment_date", "delivery_date"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    if "shipment_date" in df.columns and "delivery_date" in df.columns:
        df["transit_days"] = (df["delivery_date"] - df["shipment_date"]).dt.days
        df["is_delayed"] = (df["transit_days"] > df["transit_days"].median()).astype(int)

    # Encode carrier
    if "carrier" in df.columns:
        df["carrier_encoded"] = df["carrier"].astype("category").cat.codes

    for col in df.select_dtypes(include=[np.number]).columns:
        if df[col].isnull().sum() > 0:
            df[col] = df[col].fillna(df[col].median())

    log(f"  us_logistics: {df.shape}")
    return df


# ============================================================
# 5. US Supply Chain Risk Cleaner
# ============================================================
def clean_us_supply_chain_risk() -> pd.DataFrame:
    """
    data.csv - 1,000 rows, 24 cols
    Delay days, risk factors, supply chain disruption data.
    """
    log("Cleaning US Supply Chain Risk...")
    path = DATA_RAW / "US Supply Chain Risk Analysis Dataset" / "data.csv"
    df = pd.read_csv(path)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    for col in ["order_date", "dispatch_date", "delivery_date"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    # Compute transit and delay features
    if "dispatch_date" in df.columns and "delivery_date" in df.columns:
        df["delivery_duration_days"] = (df["delivery_date"] - df["dispatch_date"]).dt.days

    if "order_date" in df.columns and "dispatch_date" in df.columns:
        df["processing_days"] = (df["dispatch_date"] - df["order_date"]).dt.days

    # Delay flag
    if "delay_days" in df.columns:
        df["is_delayed"] = (df["delay_days"] > 0).astype(int)
        df["delay_severity"] = pd.cut(df["delay_days"], bins=[-1, 0, 3, 7, 999], labels=["on_time", "minor", "moderate", "severe"])
        df["delay_severity_encoded"] = df["delay_severity"].cat.codes

    for col in df.select_dtypes(include=[np.number]).columns:
        if df[col].isnull().sum() > 0:
            df[col] = df[col].fillna(df[col].median())

    for col in df.select_dtypes(include=["object"]).columns:
        if df[col].nunique() < 30 and df[col].isnull().sum() > 0:
            df[col] = df[col].fillna("UNKNOWN")

    log(f"  us_supply_chain_risk: {df.shape}")
    return df


# ============================================================
# 6. Smart Logistics Dataset Cleaner
# ============================================================
def clean_smart_logistics() -> pd.DataFrame:
    """
    smart_logistics_dataset.csv - 1,000 rows
    Contains delay reasons, waiting time, logistics metrics.
    """
    log("Cleaning Smart Logistics...")
    path = DATA_RAW / "Smart Logistics Supply Chain Dataset" / "smart_logistics_dataset.csv"
    df = pd.read_csv(path)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        df["hour"] = df["timestamp"].dt.hour
        df["day_of_week"] = df["timestamp"].dt.dayofweek

    # Encode delay reason
    if "logistics_delay_reason" in df.columns:
        df["delay_reason_encoded"] = df["logistics_delay_reason"].astype("category").cat.codes

    # Encode delay flag
    if "logistics_delay" in df.columns:
        df["delay_binary"] = df["logistics_delay"].map({"Yes": 1, "No": 0, True: 1, False: 0}).fillna(0).astype(int)

    for col in df.select_dtypes(include=[np.number]).columns:
        if df[col].isnull().sum() > 0:
            df[col] = df[col].fillna(df[col].median())

    log(f"  smart_logistics: {df.shape}")
    return df


# ============================================================
# 7. Maritime Port Performance Cleaner
# ============================================================
def clean_maritime_port() -> pd.DataFrame:
    """
    Maritime Port Performance Project Dataset.csv - 803 rows, 40% missing
    Hub congestion and port performance data. Heavy missing values.
    """
    log("Cleaning Maritime Port Performance...")
    path = DATA_RAW / "Maritime Port Performance Dataset" / "Maritime Port Performance Project Dataset.csv"
    df = pd.read_csv(path)
    df.columns = [c.strip().lower().replace(" ", "_").replace("(", "").replace(")", "") for c in df.columns]

    # Drop columns with >70% missing
    threshold = 0.7
    missing_pct = df.isnull().mean()
    drop_cols = missing_pct[missing_pct > threshold].index.tolist()
    df = df.drop(columns=drop_cols, errors="ignore")
    log(f"  Dropped {len(drop_cols)} cols with >{threshold*100}% missing")

    # Fill remaining numeric with median
    for col in df.select_dtypes(include=[np.number]).columns:
        if df[col].isnull().sum() > 0:
            df[col] = df[col].fillna(df[col].median())

    for col in df.select_dtypes(include=["object"]).columns:
        if df[col].isnull().sum() > 0:
            df[col] = df[col].fillna("UNKNOWN")

    log(f"  maritime_port: {df.shape}")
    return df


# ============================================================
# 8. Global Port Activity Cleaner
# ============================================================
def clean_global_port_activity() -> pd.DataFrame:
    """
    Daily_Port_Activity_Data_and_Trade_Estimates.csv - 3.49M rows
    Massive dataset. We'll sample for training and extract relevant features.
    """
    log("Cleaning Global Port Activity (sampling 50K rows)...")
    path = DATA_RAW / "Global Daily Port Activity and Trade Estimates" / "Daily_Port_Activity_Data_and_Trade_Estimates.csv"

    # Sample to keep manageable for training
    df = pd.read_csv(path, nrows=50000)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df["month"] = df["date"].dt.month
        df["day_of_week"] = df["date"].dt.dayofweek
        df["year"] = df["date"].dt.year

    for col in df.select_dtypes(include=[np.number]).columns:
        if df[col].isnull().sum() > 0:
            df[col] = df[col].fillna(df[col].median())

    log(f"  global_port_activity: {df.shape}")
    return df


# ============================================================
# MODEL-SPECIFIC TRAINING DATASET BUILDERS
# ============================================================

def build_eta_training_set(dataco: pd.DataFrame, logistics_ops: dict, us_logistics: pd.DataFrame) -> pd.DataFrame:
    """
    Build ETA prediction training set by combining relevant features.
    Target: actual shipping/transit time.
    """
    log("Building ETA training dataset...")
    frames = []

    # From DataCo - use shipping duration as target
    if dataco is not None and "actual_shipping_days" in dataco.columns:
        eta_cols = [c for c in dataco.columns if any(kw in c for kw in
                    ["shipping", "order", "latitude", "longitude", "days_for_shipping",
                     "days_for_shipment", "delivery_status_encoded", "shipping_mode_encoded",
                     "actual_shipping_days", "late_delivery_risk", "order_hour",
                     "order_day_of_week", "order_month"])]
        eta_df = dataco[eta_cols].dropna(subset=["actual_shipping_days"])
        eta_df = eta_df.select_dtypes(include=[np.number])
        frames.append(eta_df)

    # From US Logistics - use transit_days as target
    if us_logistics is not None and "transit_days" in us_logistics.columns:
        transit_cols = [c for c in us_logistics.select_dtypes(include=[np.number]).columns]
        frames.append(us_logistics[transit_cols].dropna(subset=["transit_days"]))

    if frames:
        # Combine with standardized columns
        result = pd.concat(frames, ignore_index=True, sort=False)
        result = result.fillna(0)
        log(f"  ETA training set: {result.shape}")
        return result
    return pd.DataFrame()


def build_delay_training_set(dataco: pd.DataFrame, delay_risk: pd.DataFrame,
                             us_risk: pd.DataFrame, smart_log: pd.DataFrame) -> pd.DataFrame:
    """
    Build delay risk classification training set.
    Target: is_delayed / late_delivery_risk.
    """
    log("Building Delay Risk training dataset...")
    frames = []

    # From DataCo
    if dataco is not None and "late_delivery_risk" in dataco.columns:
        delay_cols = dataco.select_dtypes(include=[np.number]).columns.tolist()
        frames.append(dataco[delay_cols])

    # From delay risk dataset
    if delay_risk is not None and "delayed" in delay_risk.columns:
        delay_cols = delay_risk.select_dtypes(include=[np.number]).columns.tolist()
        frames.append(delay_risk[delay_cols])

    # From US supply chain risk
    if us_risk is not None and "is_delayed" in us_risk.columns:
        delay_cols = us_risk.select_dtypes(include=[np.number]).columns.tolist()
        frames.append(us_risk[delay_cols])

    # From smart logistics
    if smart_log is not None and "delay_binary" in smart_log.columns:
        delay_cols = smart_log.select_dtypes(include=[np.number]).columns.tolist()
        frames.append(smart_log[delay_cols])

    if frames:
        result = pd.concat(frames, ignore_index=True, sort=False)
        result = result.fillna(0)
        log(f"  Delay Risk training set: {result.shape}")
        return result
    return pd.DataFrame()


def build_carrier_training_set(logistics_ops: dict) -> pd.DataFrame:
    """
    Build carrier reliability training set from driver metrics + delivery events.
    Target: on_time_delivery_rate / reliability score.
    """
    log("Building Carrier Reliability training dataset...")

    frames = []
    if "driver_monthly_metrics" in logistics_ops:
        frames.append(logistics_ops["driver_monthly_metrics"].select_dtypes(include=[np.number]))

    if "delivery_events" in logistics_ops:
        de = logistics_ops["delivery_events"]
        de_numeric = de.select_dtypes(include=[np.number])
        frames.append(de_numeric)

    if "trips" in logistics_ops:
        trips = logistics_ops["trips"]
        trips_numeric = trips.select_dtypes(include=[np.number])
        frames.append(trips_numeric)

    if frames:
        result = pd.concat(frames, ignore_index=True, sort=False)
        result = result.fillna(0)
        log(f"  Carrier training set: {result.shape}")
        return result
    return pd.DataFrame()


def build_hub_congestion_training_set(logistics_ops: dict, maritime: pd.DataFrame,
                                      port_activity: pd.DataFrame) -> pd.DataFrame:
    """
    Build hub congestion training set from facilities, port data.
    Target: congestion probability / queue time.
    """
    log("Building Hub Congestion training dataset...")
    frames = []

    if "facilities" in logistics_ops:
        frames.append(logistics_ops["facilities"].select_dtypes(include=[np.number]))

    if maritime is not None:
        frames.append(maritime.select_dtypes(include=[np.number]))

    if port_activity is not None:
        frames.append(port_activity.select_dtypes(include=[np.number]))

    if "truck_utilization_metrics" in logistics_ops:
        frames.append(logistics_ops["truck_utilization_metrics"].select_dtypes(include=[np.number]))

    if frames:
        result = pd.concat(frames, ignore_index=True, sort=False)
        result = result.fillna(0)
        log(f"  Hub Congestion training set: {result.shape}")
        return result
    return pd.DataFrame()


# ============================================================
# MAIN PIPELINE
# ============================================================
def run_cleaning_pipeline():
    """Run the full cleaning pipeline."""
    print("=" * 70)
    print("STRYDER AI - DATA CLEANING PIPELINE")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 70)

    # Clean individual datasets
    print("\n--- STAGE 1: Cleaning Individual Datasets ---")
    dataco = clean_dataco_supply_chain()
    logistics_ops = clean_logistics_ops()
    delay_risk = clean_delay_risk()
    us_logistics = clean_us_logistics()
    us_risk = clean_us_supply_chain_risk()
    smart_log = clean_smart_logistics()
    maritime = clean_maritime_port()
    port_activity = clean_global_port_activity()

    # Save cleaned individual datasets
    print("\n--- STAGE 2: Saving Cleaned Datasets ---")
    dataco.to_csv(DATA_PROCESSED / "dataco_supply_chain_clean.csv", index=False)
    log("Saved dataco_supply_chain_clean.csv")

    for name, df in logistics_ops.items():
        df.to_csv(DATA_PROCESSED / f"logistics_{name}_clean.csv", index=False)
        log(f"Saved logistics_{name}_clean.csv")

    delay_risk.to_csv(DATA_PROCESSED / "delay_risk_clean.csv", index=False)
    log("Saved delay_risk_clean.csv")

    us_logistics.to_csv(DATA_PROCESSED / "us_logistics_clean.csv", index=False)
    log("Saved us_logistics_clean.csv")

    us_risk.to_csv(DATA_PROCESSED / "us_supply_chain_risk_clean.csv", index=False)
    log("Saved us_supply_chain_risk_clean.csv")

    smart_log.to_csv(DATA_PROCESSED / "smart_logistics_clean.csv", index=False)
    log("Saved smart_logistics_clean.csv")

    maritime.to_csv(DATA_PROCESSED / "maritime_port_clean.csv", index=False)
    log("Saved maritime_port_clean.csv")

    port_activity.to_csv(DATA_PROCESSED / "global_port_activity_clean.csv", index=False)
    log("Saved global_port_activity_clean.csv")

    # Build model-specific training datasets
    print("\n--- STAGE 3: Building Model Training Datasets ---")
    eta_train = build_eta_training_set(dataco, logistics_ops, us_logistics)
    if not eta_train.empty:
        eta_train.to_csv(DATA_PROCESSED / "train_eta_prediction.csv", index=False)
        log(f"Saved train_eta_prediction.csv ({eta_train.shape})")

    delay_train = build_delay_training_set(dataco, delay_risk, us_risk, smart_log)
    if not delay_train.empty:
        delay_train.to_csv(DATA_PROCESSED / "train_delay_risk.csv", index=False)
        log(f"Saved train_delay_risk.csv ({delay_train.shape})")

    carrier_train = build_carrier_training_set(logistics_ops)
    if not carrier_train.empty:
        carrier_train.to_csv(DATA_PROCESSED / "train_carrier_reliability.csv", index=False)
        log(f"Saved train_carrier_reliability.csv ({carrier_train.shape})")

    hub_train = build_hub_congestion_training_set(logistics_ops, maritime, port_activity)
    if not hub_train.empty:
        hub_train.to_csv(DATA_PROCESSED / "train_hub_congestion.csv", index=False)
        log(f"Saved train_hub_congestion.csv ({hub_train.shape})")

    # Summary report
    print("\n" + "=" * 70)
    print("CLEANING PIPELINE COMPLETE")
    print("=" * 70)

    processed_files = sorted(DATA_PROCESSED.glob("*.csv"))
    total_size_mb = 0
    print(f"\n{'File':<50} {'Size (MB)':>10}")
    print("-" * 62)
    for f in processed_files:
        size_mb = f.stat().st_size / 1024 / 1024
        total_size_mb += size_mb
        print(f"{f.name:<50} {size_mb:>10.2f}")
    print("-" * 62)
    print(f"{'TOTAL':<50} {total_size_mb:>10.2f}")
    print(f"\nTotal output files: {len(processed_files)}")
    print(f"Finished: {datetime.now().isoformat()}")

    return True


if __name__ == "__main__":
    success = run_cleaning_pipeline()
    sys.exit(0 if success else 1)
