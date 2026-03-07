"""
STRYDER AI - Master Model Training Pipeline
=============================================
Trains all 5 ML models from scratch in sequence.
Validates each model and produces a consolidated report.

Models:
  1. ETA Prediction (XGBoost Regressor)
  2. Delay Risk (XGBoost Classifier)
  3. Carrier Reliability (LightGBM Regressor)
  4. Hub Congestion (XGBoost Classifier)
  5. Cascade Failure (XGBoost Classifier)
"""

import sys
import json
import traceback
from pathlib import Path
from datetime import datetime

MODEL_DIR = Path(__file__).parent / "saved_models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)


def train_all():
    """Train all 5 models and generate consolidated report."""
    print("=" * 70)
    print("STRYDER AI - MASTER MODEL TRAINING PIPELINE")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 70)

    results = {}
    models_trained = 0
    models_failed = 0

    # --- 1. ETA Prediction ---
    print("\n" + "=" * 70)
    print("MODEL 1/5: ETA PREDICTION")
    print("=" * 70)
    try:
        from backend.ml_models.eta_model import train_model as train_eta
        _, _, meta = train_eta()
        results["eta_prediction"] = {"status": "SUCCESS", "metrics": meta["metrics"]}
        models_trained += 1
    except Exception as e:
        print(f"FAILED: {e}")
        traceback.print_exc()
        results["eta_prediction"] = {"status": "FAILED", "error": str(e)}
        models_failed += 1

    # --- 2. Delay Risk ---
    print("\n" + "=" * 70)
    print("MODEL 2/5: DELAY RISK")
    print("=" * 70)
    try:
        from backend.ml_models.delay_model import train_model as train_delay
        _, _, meta = train_delay()
        results["delay_risk"] = {"status": "SUCCESS", "metrics": meta["metrics"]}
        models_trained += 1
    except Exception as e:
        print(f"FAILED: {e}")
        traceback.print_exc()
        results["delay_risk"] = {"status": "FAILED", "error": str(e)}
        models_failed += 1

    # --- 3. Carrier Reliability ---
    print("\n" + "=" * 70)
    print("MODEL 3/5: CARRIER RELIABILITY")
    print("=" * 70)
    try:
        from backend.ml_models.carrier_model import train_model as train_carrier
        _, _, meta = train_carrier()
        results["carrier_reliability"] = {"status": "SUCCESS", "metrics": meta["metrics"]}
        models_trained += 1
    except Exception as e:
        print(f"FAILED: {e}")
        traceback.print_exc()
        results["carrier_reliability"] = {"status": "FAILED", "error": str(e)}
        models_failed += 1

    # --- 4. Hub Congestion ---
    print("\n" + "=" * 70)
    print("MODEL 4/5: HUB CONGESTION")
    print("=" * 70)
    try:
        from backend.ml_models.hub_congestion_model import train_model as train_hub
        _, _, meta = train_hub()
        results["hub_congestion"] = {"status": "SUCCESS", "metrics": meta["metrics"]}
        models_trained += 1
    except Exception as e:
        print(f"FAILED: {e}")
        traceback.print_exc()
        results["hub_congestion"] = {"status": "FAILED", "error": str(e)}
        models_failed += 1

    # --- 5. Cascade Failure ---
    print("\n" + "=" * 70)
    print("MODEL 5/5: CASCADE FAILURE")
    print("=" * 70)
    try:
        from backend.ml_models.cascade_model import train_model as train_cascade
        _, _, meta = train_cascade()
        results["cascade_failure"] = {"status": "SUCCESS", "metrics": meta["metrics"]}
        models_trained += 1
    except Exception as e:
        print(f"FAILED: {e}")
        traceback.print_exc()
        results["cascade_failure"] = {"status": "FAILED", "error": str(e)}
        models_failed += 1

    # Consolidated report
    print("\n\n" + "=" * 70)
    print("TRAINING PIPELINE COMPLETE")
    print("=" * 70)
    print(f"\nModels trained: {models_trained}/5")
    print(f"Models failed:  {models_failed}/5")

    print(f"\n{'Model':<25} {'Status':<10} {'Key Metric':<20}")
    print("-" * 60)
    for name, result in results.items():
        status = result["status"]
        if status == "SUCCESS":
            metrics = result["metrics"]
            if "r2" in metrics:
                key = f"R²={metrics['r2']:.4f}"
            elif "auc_roc" in metrics:
                key = f"AUC={metrics['auc_roc']:.4f}"
            else:
                key = str(list(metrics.values())[0])
        else:
            key = result.get("error", "Unknown")[:30]
        print(f"{name:<25} {status:<10} {key:<20}")

    # Save consolidated report
    report = {
        "timestamp": datetime.now().isoformat(),
        "models_trained": models_trained,
        "models_failed": models_failed,
        "results": results,
    }
    with open(MODEL_DIR / "training_report.json", "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nReport saved: {MODEL_DIR / 'training_report.json'}")

    # List saved model files
    print(f"\nSaved model files:")
    for f in sorted(MODEL_DIR.glob("*")):
        size_kb = f.stat().st_size / 1024
        print(f"  {f.name:<40} {size_kb:>8.1f} KB")

    print(f"\nFinished: {datetime.now().isoformat()}")
    return models_failed == 0


if __name__ == "__main__":
    success = train_all()
    sys.exit(0 if success else 1)
