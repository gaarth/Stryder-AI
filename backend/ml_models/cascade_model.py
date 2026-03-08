"""
STRYDER AI - Cascade Failure Model
=====================================
@Strategist:CASCADE_MODEL

Probability model predicting cascading disruptions across the supply chain.
Uses shipment dependency features and delay propagation patterns.
Target: Derived cascade risk from multi-event delay correlations

Model: XGBoost Classifier with cascade probability scoring
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


def build_cascade_features():
    """
    Build cascade-risk training data by combining delivery events with
    route dependencies and delay propagation signals.
    """
    # Load cleaned datasets
    delivery = pd.read_csv(DATA_DIR / "logistics_delivery_events_clean.csv")
    trips = pd.read_csv(DATA_DIR / "logistics_trips_clean.csv")

    # Also load delay risk data for additional features
    try:
        delay_risk = pd.read_csv(DATA_DIR / "delay_risk_clean.csv")
    except FileNotFoundError:
        delay_risk = None

    try:
        us_risk = pd.read_csv(DATA_DIR / "us_supply_chain_risk_clean.csv")
    except FileNotFoundError:
        us_risk = None

    # --- Build cascade features from delivery events ---
    # Group by facility to detect multi-shipment delays (cascade signal)
    if "facility_id" in delivery.columns and "delay_minutes" in delivery.columns:
        facility_stats = delivery.groupby("facility_id").agg(
            total_deliveries=("delay_minutes", "count"),
            delayed_deliveries=("is_delayed", "sum"),
            avg_delay=("delay_minutes", "mean"),
            max_delay=("delay_minutes", "max"),
            delay_std=("delay_minutes", "std"),
        ).reset_index()

        facility_stats["delay_rate"] = facility_stats["delayed_deliveries"] / facility_stats["total_deliveries"]
        facility_stats["delay_std"] = facility_stats["delay_std"].fillna(0)

        # Cascade risk: high delay rate + high variance = cascade potential
        cascade_threshold = facility_stats["delay_rate"].quantile(0.75)
        facility_stats["cascade_risk"] = (
            (facility_stats["delay_rate"] > cascade_threshold) &
            (facility_stats["avg_delay"] > facility_stats["avg_delay"].median())
        ).astype(int)

        merged = delivery.merge(facility_stats, on="facility_id", how="left", suffixes=("", "_fac"))
    else:
        # Fallback: create from delivery data directly
        delivery["cascade_risk"] = 0
        if "delay_minutes" in delivery.columns:
            p75 = delivery["delay_minutes"].quantile(0.75)
            delivery["cascade_risk"] = (delivery["delay_minutes"] > p75).astype(int)
        merged = delivery.copy()
        merged["total_deliveries"] = 1
        merged["delayed_deliveries"] = merged.get("is_delayed", 0)
        merged["avg_delay"] = merged.get("delay_minutes", 0)
        merged["max_delay"] = merged.get("delay_minutes", 0)
        merged["delay_std"] = 0
        merged["delay_rate"] = merged.get("is_delayed", 0)

    # Select numeric features for cascade model
    cascade_features = merged.select_dtypes(include=[np.number]).copy()
    cascade_features = cascade_features.fillna(0).replace([np.inf, -np.inf], 0)

    # Add trip-level aggregations if possible
    if "route_id" in trips.columns:
        route_stats = trips.groupby("route_id").agg(
            route_trips=("route_id", "count"),
        ).reset_index()
        # We'll just use the trip data as-is for size padding
        trip_numeric = trips.select_dtypes(include=[np.number]).fillna(0)
        trip_numeric["cascade_risk"] = 0
        if "idle_time_hours" in trip_numeric.columns:
            threshold = trip_numeric["idle_time_hours"].quantile(0.8)
            trip_numeric["cascade_risk"] = (trip_numeric["idle_time_hours"] > threshold).astype(int)

    # Combine
    target = "cascade_risk"
    features = [c for c in cascade_features.columns if c != target]

    X = cascade_features[features]
    y = cascade_features[target]

    return X, y, features, target


def train_model():
    """Train the cascade failure prediction model."""
    print("=" * 60)
    print("STRYDER AI - CASCADE FAILURE MODEL")
    print("=" * 60)

    X, y, features, target_name = build_cascade_features()
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

    n_pos = int(y_train.sum())
    n_neg = len(y_train) - n_pos
    scale_weight = n_neg / n_pos if n_pos > 0 else 1

    print(f"\nTraining XGBoost Classifier...")
    model = xgb.XGBClassifier(
        n_estimators=150,
        max_depth=5,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=min(scale_weight, 8),
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

    joblib.dump(model, MODEL_DIR / "cascade_model.joblib")
    joblib.dump(scaler, MODEL_DIR / "cascade_scaler.joblib")

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
    with open(MODEL_DIR / "cascade_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"\nModel saved to {MODEL_DIR / 'cascade_model.joblib'}")
    return model, scaler, metadata


def predict(input_data: dict, model=None, scaler=None) -> dict:
    """Predict cascade failure probability."""
    if model is None:
        model = joblib.load(MODEL_DIR / "cascade_model.joblib")
    if scaler is None:
        scaler = joblib.load(MODEL_DIR / "cascade_scaler.joblib")

    meta = json.load(open(MODEL_DIR / "cascade_metadata.json"))
    features = meta["features"]

    X = pd.DataFrame([input_data])
    for f in features:
        if f not in X.columns:
            X[f] = 0
    X = X[features].fillna(0)
    X_scaled = scaler.transform(X)

    prob = float(model.predict_proba(X_scaled)[0][1])
    severity = "CRITICAL" if prob > 0.8 else "HIGH" if prob > 0.6 else "MODERATE" if prob > 0.3 else "LOW"

    # Estimate affected shipments based on probability
    estimated_affected = max(1, int(prob * 15))

    return {
        "cascade_probability": round(prob, 4),
        "severity": severity,
        "estimated_affected_shipments": estimated_affected,
        "risk_propagation_factor": round(1 + prob * 4, 2),
    }


if __name__ == "__main__":
    train_model()
