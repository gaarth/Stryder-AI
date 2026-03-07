"""
STRYDER AI - Hub Congestion Model
====================================
@Strategist:HUB_AGENT

Classification model predicting warehouse/port congestion probability.
Target: Derived congestion flag from utilization_rate & port call density
Features: port calls, import/export volume, vessel capacity, dock doors

Model: XGBoost Classifier
"""

import json
from pathlib import Path

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score
)
import xgboost as xgb
import joblib

MODEL_DIR = Path(__file__).parent / "saved_models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "processed"

FEATURE_COLS = [
    "dock_doors", "average_age_of_vessels_years_value",
    "median_time_in_port_days_value", "average_size_gt_of_vessels_value",
    "average_cargo_carrying_capacity_dwt_per_vessel_value",
    "portcalls_container", "portcalls_dry_bulk", "portcalls_cargo", "portcalls",
    "import_container", "import_cargo", "import",
    "export_container", "export_cargo", "export",
    "day_of_week", "month", "year",
    "trips_completed", "total_miles",
    "maintenance_events", "maintenance_cost", "downtime_hours",
    "utilization_rate",
]


def load_data():
    """Load hub congestion data and create congestion target."""
    df = pd.read_csv(DATA_DIR / "train_hub_congestion.csv")

    # Drop unnamed columns
    df = df.drop(columns=[c for c in df.columns if "unnamed" in c.lower()], errors="ignore")

    # Create congestion target
    # Use utilization_rate if available, otherwise derive from port calls
    if "utilization_rate" in df.columns:
        threshold = df["utilization_rate"].quantile(0.75)
        df["congested"] = (df["utilization_rate"] > threshold).astype(int)
        target = "congested"
    elif "portcalls" in df.columns:
        threshold = df["portcalls"].quantile(0.75)
        df["congested"] = (df["portcalls"] > threshold).astype(int)
        target = "congested"
    elif "median_time_in_port_days_value" in df.columns:
        threshold = df["median_time_in_port_days_value"].quantile(0.75)
        df["congested"] = (df["median_time_in_port_days_value"] > threshold).astype(int)
        target = "congested"
    else:
        raise ValueError("Cannot derive congestion target")

    available = [c for c in FEATURE_COLS if c in df.columns and c != target and c != "utilization_rate"]
    if len(available) < 3:
        available = [c for c in df.select_dtypes(include=[np.number]).columns
                     if c != target and c != "utilization_rate"]

    X = df[available].copy().fillna(0)
    y = df[target].copy()

    # Replace inf
    X = X.replace([np.inf, -np.inf], 0)

    return X, y, available, target


def train_model():
    """Train the hub congestion model."""
    print("=" * 60)
    print("STRYDER AI - HUB CONGESTION MODEL")
    print("=" * 60)

    X, y, features, target_name = load_data()
    print(f"Target: {target_name}")
    print(f"Features ({len(features)}): {features[:6]}...")
    print(f"Dataset: {X.shape[0]:,} samples")
    print(f"Class balance: {y.value_counts().to_dict()}")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    n_pos = y_train.sum()
    n_neg = len(y_train) - n_pos
    scale_weight = n_neg / n_pos if n_pos > 0 else 1

    print(f"\nTraining XGBoost Classifier...")
    model = xgb.XGBClassifier(
        n_estimators=150,
        max_depth=5,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=min(scale_weight, 5),
        random_state=42,
        n_jobs=-1,
        eval_metric="logloss",
    )
    model.fit(
        X_train_scaled, y_train,
        eval_set=[(X_test_scaled, y_test)],
        verbose=False,
    )

    y_pred = model.predict(X_test_scaled)
    y_proba = model.predict_proba(X_test_scaled)[:, 1]

    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred, zero_division=0)
    rec = recall_score(y_test, y_pred, zero_division=0)
    f1 = f1_score(y_test, y_pred, zero_division=0)
    auc = roc_auc_score(y_test, y_proba)

    cv_scores = cross_val_score(model, X_train_scaled, y_train, cv=5, scoring="f1")

    print(f"\n--- Results ---")
    print(f"Accuracy:  {acc:.4f}")
    print(f"Precision: {prec:.4f}")
    print(f"Recall:    {rec:.4f}")
    print(f"F1:        {f1:.4f}")
    print(f"AUC-ROC:   {auc:.4f}")
    print(f"CV F1:     {cv_scores.mean():.4f}")

    importance = dict(zip(features, model.feature_importances_))
    importance = dict(sorted(importance.items(), key=lambda x: x[1], reverse=True))
    print(f"\nTop features:")
    for feat, imp in list(importance.items())[:5]:
        print(f"  {feat}: {imp:.4f}")

    joblib.dump(model, MODEL_DIR / "hub_congestion_model.joblib")
    joblib.dump(scaler, MODEL_DIR / "hub_congestion_scaler.joblib")

    metadata = {
        "model_type": "XGBClassifier",
        "target": target_name,
        "features": features,
        "metrics": {
            "accuracy": round(acc, 4), "precision": round(prec, 4),
            "recall": round(rec, 4), "f1": round(f1, 4),
            "auc_roc": round(auc, 4), "cv_f1": round(cv_scores.mean(), 4),
        },
        "feature_importance": {k: round(float(v), 4) for k, v in importance.items()},
        "train_samples": len(X_train),
        "test_samples": len(X_test),
    }
    with open(MODEL_DIR / "hub_congestion_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"\nModel saved to {MODEL_DIR / 'hub_congestion_model.joblib'}")
    return model, scaler, metadata


def predict(input_data: dict, model=None, scaler=None) -> dict:
    """Predict congestion probability for a hub."""
    if model is None:
        model = joblib.load(MODEL_DIR / "hub_congestion_model.joblib")
    if scaler is None:
        scaler = joblib.load(MODEL_DIR / "hub_congestion_scaler.joblib")

    meta = json.load(open(MODEL_DIR / "hub_congestion_metadata.json"))
    features = meta["features"]

    X = pd.DataFrame([input_data])
    for f in features:
        if f not in X.columns:
            X[f] = 0
    X = X[features].fillna(0)
    X_scaled = scaler.transform(X)

    prob = float(model.predict_proba(X_scaled)[0][1])
    level = "CRITICAL" if prob > 0.8 else "HIGH" if prob > 0.6 else "MODERATE" if prob > 0.3 else "LOW"

    return {
        "congestion_probability": round(prob, 4),
        "congestion_level": level,
        "expected_queue_time_multiplier": round(1 + prob * 3, 2),
    }


if __name__ == "__main__":
    train_model()
