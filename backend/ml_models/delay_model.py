"""
STRYDER AI - Delay Risk Model
================================
@Strategist:DELAY_AGENT

Binary classification model predicting probability of SLA breach.
Target: late_delivery_risk / delayed / is_delayed
Features: shipping distance, processing time, carrier, weather, inventory

Model: XGBoost Classifier with probability calibration
"""

import json
from pathlib import Path

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, classification_report
)
import xgboost as xgb
import joblib

MODEL_DIR = Path(__file__).parent / "saved_models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "processed"

# Target priority
TARGET_CANDIDATES = ["late_delivery_risk", "delayed", "is_delayed", "delay_binary"]

FEATURE_COLS = [
    "days_for_shipping_real", "days_for_shipment_scheduled",
    "shipping_mode_encoded", "order_hour", "order_day_of_week", "order_month",
    "shipping_hour", "shipping_day_of_week",
    "order_item_quantity", "order_item_product_price",
    "actual_shipping_days", "delivery_status_encoded",
    "supplier_reliability_score", "warehouse_inventory_level",
    "shipping_distance_km", "processing_time_hours",
    "weather_condition_encoded", "order_priority_encoded",
    "order_value_usd", "delay_days",
    "historical_disruption_count",
    "inventory_level", "temperature", "humidity",
    "waiting_time", "asset_utilization", "demand_forecast",
    "hour", "day_of_week",
]


def load_data():
    """Load delay risk training data."""
    df = pd.read_csv(DATA_DIR / "train_delay_risk.csv")

    # Find target
    target = None
    for candidate in TARGET_CANDIDATES:
        if candidate in df.columns:
            target = candidate
            break
    if target is None:
        raise ValueError(f"No target column found among {TARGET_CANDIDATES}")

    # Select features
    available = [c for c in FEATURE_COLS if c in df.columns and c != target]
    if len(available) < 5:
        available = [c for c in df.select_dtypes(include=[np.number]).columns if c != target]

    X = df[available].copy()
    y = df[target].copy()

    # Ensure binary
    y = (y > 0).astype(int)

    # Clean
    mask = X.notna().all(axis=1) & y.notna()
    X = X[mask].fillna(0)
    y = y[mask]

    return X, y, available, target


def train_model():
    """Train the delay risk classifier."""
    print("=" * 60)
    print("STRYDER AI - DELAY RISK MODEL")
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

    # Calculate scale_pos_weight for imbalanced classes
    n_pos = y_train.sum()
    n_neg = len(y_train) - n_pos
    scale_weight = n_neg / n_pos if n_pos > 0 else 1

    print(f"\nTraining XGBoost Classifier...")
    model = xgb.XGBClassifier(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=min(scale_weight, 10),  # cap at 10
        random_state=42,
        n_jobs=-1,
        eval_metric="logloss",
    )
    model.fit(
        X_train_scaled, y_train,
        eval_set=[(X_test_scaled, y_test)],
        verbose=False,
    )

    # Evaluate
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
    print(f"CV F1:     {cv_scores.mean():.4f} (+/- {cv_scores.std():.4f})")

    # Feature importance
    importance = dict(zip(features, model.feature_importances_))
    importance = dict(sorted(importance.items(), key=lambda x: x[1], reverse=True))
    print(f"\nTop features:")
    for feat, imp in list(importance.items())[:5]:
        print(f"  {feat}: {imp:.4f}")

    # Save
    joblib.dump(model, MODEL_DIR / "delay_model.joblib")
    joblib.dump(scaler, MODEL_DIR / "delay_scaler.joblib")

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
    with open(MODEL_DIR / "delay_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"\nModel saved to {MODEL_DIR / 'delay_model.joblib'}")
    return model, scaler, metadata


def predict(input_data: dict, model=None, scaler=None) -> dict:
    """Predict delay probability for a shipment."""
    if model is None:
        model = joblib.load(MODEL_DIR / "delay_model.joblib")
    if scaler is None:
        scaler = joblib.load(MODEL_DIR / "delay_scaler.joblib")

    meta = json.load(open(MODEL_DIR / "delay_metadata.json"))
    features = meta["features"]

    X = pd.DataFrame([input_data])
    for f in features:
        if f not in X.columns:
            X[f] = 0
    X = X[features].fillna(0)
    X_scaled = scaler.transform(X)

    prob = model.predict_proba(X_scaled)[0][1]
    risk_label = "HIGH" if prob > 0.7 else "MEDIUM" if prob > 0.4 else "LOW"

    return {
        "delay_probability": round(float(prob), 4),
        "risk_level": risk_label,
        "model_accuracy": meta["metrics"]["accuracy"],
    }


if __name__ == "__main__":
    train_model()
