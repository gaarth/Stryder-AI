"""
STRYDER AI - ETA Prediction Model
===================================
@Strategist:ETA_AGENT

Regression model predicting shipment arrival time / transit duration.
Target: actual_shipping_days (DataCo) / transit_days (US Logistics)
Features: route distance, shipping mode, order timing, carrier, weight

Model: XGBoost Regressor with hyperparameter tuning
"""

import os
import json
from pathlib import Path

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import xgboost as xgb
import joblib

# Paths
MODEL_DIR = Path(__file__).parent / "saved_models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "processed"

# Feature configuration
TARGET_COL = "actual_shipping_days"
FALLBACK_TARGET = "transit_days"

FEATURE_COLS = [
    "days_for_shipment_scheduled",
    "latitude", "longitude",
    "order_hour", "order_day_of_week", "order_month",
    "shipping_hour", "shipping_day_of_week",
    "shipping_mode_encoded",
    "order_item_quantity",
    "order_item_product_price",
    "order_item_total",
    "weight_kg", "cost", "distance_miles",
    "carrier_encoded",
    "late_delivery_risk",
]


def load_data():
    """Load and prepare the ETA training dataset."""
    df = pd.read_csv(DATA_DIR / "train_eta_prediction.csv")

    # Determine target
    target = TARGET_COL if TARGET_COL in df.columns else FALLBACK_TARGET
    if target not in df.columns:
        raise ValueError(f"Neither {TARGET_COL} nor {FALLBACK_TARGET} found in dataset")

    # Select available features
    available = [c for c in FEATURE_COLS if c in df.columns]
    if len(available) < 5:
        # Fallback: use all numeric columns except target
        available = [c for c in df.select_dtypes(include=[np.number]).columns if c != target]

    X = df[available].copy()
    y = df[target].copy()

    # Remove infinite/NaN
    mask = np.isfinite(y) & (y > 0) & (y < 365)  # reasonable range
    X = X[mask]
    y = y[mask]

    # Fill remaining NaNs
    X = X.fillna(0)

    return X, y, available, target


def train_model():
    """Train the ETA prediction model."""
    print("=" * 60)
    print("STRYDER AI - ETA PREDICTION MODEL")
    print("=" * 60)

    X, y, features, target_name = load_data()
    print(f"Target: {target_name}")
    print(f"Features ({len(features)}): {features[:8]}...")
    print(f"Dataset: {X.shape[0]:,} samples")
    print(f"Target range: [{y.min():.1f}, {y.max():.1f}], mean={y.mean():.2f}")

    # Train/test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    # Scale features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # Train XGBoost
    print("\nTraining XGBoost Regressor...")
    model = xgb.XGBRegressor(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=5,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(
        X_train_scaled, y_train,
        eval_set=[(X_test_scaled, y_test)],
        verbose=False,
    )

    # Evaluate
    y_pred = model.predict(X_test_scaled)
    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    r2 = r2_score(y_test, y_pred)

    # Cross-validation
    cv_scores = cross_val_score(model, X_train_scaled, y_train, cv=5,
                                scoring="neg_mean_absolute_error")
    cv_mae = -cv_scores.mean()

    print(f"\n--- Results ---")
    print(f"MAE:  {mae:.4f} days")
    print(f"RMSE: {rmse:.4f} days")
    print(f"R²:   {r2:.4f}")
    print(f"CV MAE: {cv_mae:.4f} days")

    # Feature importance
    importance = dict(zip(features, model.feature_importances_))
    importance = dict(sorted(importance.items(), key=lambda x: x[1], reverse=True))
    print(f"\nTop features:")
    for feat, imp in list(importance.items())[:5]:
        print(f"  {feat}: {imp:.4f}")

    # Save model + scaler + metadata
    joblib.dump(model, MODEL_DIR / "eta_model.joblib")
    joblib.dump(scaler, MODEL_DIR / "eta_scaler.joblib")

    metadata = {
        "model_type": "XGBRegressor",
        "target": target_name,
        "features": features,
        "metrics": {"mae": round(mae, 4), "rmse": round(rmse, 4), "r2": round(r2, 4), "cv_mae": round(cv_mae, 4)},
        "feature_importance": {k: round(float(v), 4) for k, v in importance.items()},
        "train_samples": len(X_train),
        "test_samples": len(X_test),
    }
    with open(MODEL_DIR / "eta_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"\nModel saved to {MODEL_DIR / 'eta_model.joblib'}")
    return model, scaler, metadata


def predict(input_data: dict, model=None, scaler=None) -> dict:
    """Run inference on a single sample."""
    if model is None:
        model = joblib.load(MODEL_DIR / "eta_model.joblib")
    if scaler is None:
        scaler = joblib.load(MODEL_DIR / "eta_scaler.joblib")

    meta = json.load(open(MODEL_DIR / "eta_metadata.json"))
    features = meta["features"]

    X = pd.DataFrame([input_data])
    for f in features:
        if f not in X.columns:
            X[f] = 0
    X = X[features].fillna(0)

    X_scaled = scaler.transform(X)
    pred = model.predict(X_scaled)[0]

    return {
        "predicted_eta_days": round(float(pred), 2),
        "confidence": round(float(meta["metrics"]["r2"]) * 100, 1),
        "model_mae": meta["metrics"]["mae"],
    }


if __name__ == "__main__":
    train_model()
