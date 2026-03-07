"""
STRYDER AI - Carrier Reliability Model
=========================================
@Strategist:CARRIER_AGENT

Scoring model that rates carrier/driver reliability.
Target: on_time_delivery_rate (continuous 0-1 score)
Features: trips completed, miles, MPG, fuel, idle time, delays

Model: LightGBM Regressor for reliability scoring
"""

import json
from pathlib import Path

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import lightgbm as lgb
import joblib

MODEL_DIR = Path(__file__).parent / "saved_models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "processed"

TARGET_COL = "on_time_delivery_rate"

FEATURE_COLS = [
    "trips_completed", "total_miles", "total_revenue",
    "average_mpg", "total_fuel_gallons",
    "average_idle_hours", "detention_minutes",
    "delay_minutes", "is_delayed", "on_time_binary",
    "actual_distance_miles", "actual_duration_hours",
    "fuel_gallons_used", "idle_time_hours",
    "dispatch_month", "dispatch_day_of_week",
]


def load_data():
    """Load carrier reliability training data."""
    df = pd.read_csv(DATA_DIR / "train_carrier_reliability.csv")

    if TARGET_COL not in df.columns:
        # Synthesize target from on_time_binary if available
        if "on_time_binary" in df.columns:
            # Use on_time_binary directly as a proxy
            df[TARGET_COL] = df["on_time_binary"].astype(float)
        else:
            raise ValueError(f"Target {TARGET_COL} not found")

    available = [c for c in FEATURE_COLS if c in df.columns and c != TARGET_COL]
    if len(available) < 3:
        available = [c for c in df.select_dtypes(include=[np.number]).columns if c != TARGET_COL]

    X = df[available].copy().fillna(0)
    y = df[TARGET_COL].copy()

    # Clean invalid values
    mask = y.notna() & np.isfinite(y)
    X = X[mask]
    y = y[mask]

    # Clamp to [0, 1]
    y = y.clip(0, 1)

    return X, y, available


def train_model():
    """Train the carrier reliability model."""
    print("=" * 60)
    print("STRYDER AI - CARRIER RELIABILITY MODEL")
    print("=" * 60)

    X, y, features = load_data()
    print(f"Target: {TARGET_COL}")
    print(f"Features ({len(features)}): {features[:6]}...")
    print(f"Dataset: {X.shape[0]:,} samples")
    print(f"Target range: [{y.min():.2f}, {y.max():.2f}], mean={y.mean():.4f}")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    print(f"\nTraining LightGBM Regressor...")
    model = lgb.LGBMRegressor(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_samples=10,
        random_state=42,
        n_jobs=-1,
        verbose=-1,
    )
    model.fit(
        X_train_scaled, y_train,
        eval_set=[(X_test_scaled, y_test)],
    )

    y_pred = model.predict(X_test_scaled)
    y_pred = np.clip(y_pred, 0, 1)

    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    r2 = r2_score(y_test, y_pred)

    cv_scores = cross_val_score(model, X_train_scaled, y_train, cv=5,
                                scoring="neg_mean_absolute_error")
    cv_mae = -cv_scores.mean()

    print(f"\n--- Results ---")
    print(f"MAE:  {mae:.4f}")
    print(f"RMSE: {rmse:.4f}")
    print(f"R²:   {r2:.4f}")
    print(f"CV MAE: {cv_mae:.4f}")

    importance = dict(zip(features, model.feature_importances_))
    importance = dict(sorted(importance.items(), key=lambda x: x[1], reverse=True))
    print(f"\nTop features:")
    for feat, imp in list(importance.items())[:5]:
        print(f"  {feat}: {imp}")

    joblib.dump(model, MODEL_DIR / "carrier_model.joblib")
    joblib.dump(scaler, MODEL_DIR / "carrier_scaler.joblib")

    metadata = {
        "model_type": "LGBMRegressor",
        "target": TARGET_COL,
        "features": features,
        "metrics": {"mae": round(mae, 4), "rmse": round(rmse, 4), "r2": round(r2, 4), "cv_mae": round(cv_mae, 4)},
        "feature_importance": {k: round(float(v), 4) for k, v in importance.items()},
        "train_samples": len(X_train),
        "test_samples": len(X_test),
    }
    with open(MODEL_DIR / "carrier_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"\nModel saved to {MODEL_DIR / 'carrier_model.joblib'}")
    return model, scaler, metadata


def predict(input_data: dict, model=None, scaler=None) -> dict:
    """Score a carrier's reliability."""
    if model is None:
        model = joblib.load(MODEL_DIR / "carrier_model.joblib")
    if scaler is None:
        scaler = joblib.load(MODEL_DIR / "carrier_scaler.joblib")

    meta = json.load(open(MODEL_DIR / "carrier_metadata.json"))
    features = meta["features"]

    X = pd.DataFrame([input_data])
    for f in features:
        if f not in X.columns:
            X[f] = 0
    X = X[features].fillna(0)
    X_scaled = scaler.transform(X)

    score = float(np.clip(model.predict(X_scaled)[0], 0, 1))
    tier = "PREMIUM" if score > 0.9 else "RELIABLE" if score > 0.75 else "STANDARD" if score > 0.5 else "AT_RISK"

    return {
        "reliability_score": round(score, 4),
        "tier": tier,
        "model_r2": meta["metrics"]["r2"],
    }


if __name__ == "__main__":
    train_model()
