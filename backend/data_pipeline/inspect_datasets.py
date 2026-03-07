"""
STRYDER AI - Phase 1: Dataset Inspection & Schema Discovery
============================================================
Inspects all Kaggle CSV datasets in data/raw/kaggle datasets/
Produces a comprehensive report covering:
  - Column schemas and data types
  - Row/column counts
  - Missing value analysis
  - Numeric statistics and outlier detection
  - Unique value counts for categorical columns
  - Feature engineering suggestions
  - Relevance mapping to STRYDER AI ML models
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

import pandas as pd
import numpy as np

# Project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_RAW = PROJECT_ROOT / "data" / "raw" / "kaggle datasets"
REPORT_DIR = PROJECT_ROOT / "data" / "processed"
REPORT_DIR.mkdir(parents=True, exist_ok=True)


def detect_outliers_iqr(series: pd.Series) -> dict:
    """Detect outliers using IQR method for numeric columns."""
    q1 = series.quantile(0.25)
    q3 = series.quantile(0.75)
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    outlier_count = int(((series < lower) | (series > upper)).sum())
    return {
        "q1": round(float(q1), 4),
        "q3": round(float(q3), 4),
        "iqr": round(float(iqr), 4),
        "lower_bound": round(float(lower), 4),
        "upper_bound": round(float(upper), 4),
        "outlier_count": outlier_count,
        "outlier_pct": round(outlier_count / len(series) * 100, 2) if len(series) > 0 else 0,
    }


def infer_feature_role(col_name: str, dtype: str) -> str:
    """Heuristic to suggest the role of a column for ML feature engineering."""
    name = col_name.lower()

    # Target-like columns
    target_keywords = ["delay", "late", "risk", "status", "delivered", "on_time",
                       "breach", "congestion", "reliability", "score", "eta"]
    for kw in target_keywords:
        if kw in name:
            return "POTENTIAL_TARGET"

    # Temporal features
    time_keywords = ["date", "time", "timestamp", "hour", "day", "month", "year",
                     "departure", "arrival", "created", "updated", "scheduled"]
    for kw in time_keywords:
        if kw in name:
            return "TEMPORAL"

    # Geographic features
    geo_keywords = ["lat", "lon", "lng", "city", "state", "country", "region",
                    "origin", "destination", "port", "hub", "warehouse", "zip",
                    "address", "location", "route"]
    for kw in geo_keywords:
        if kw in name:
            return "GEOGRAPHIC"

    # Carrier / entity features
    entity_keywords = ["carrier", "driver", "truck", "vehicle", "customer",
                       "client", "supplier", "vendor", "company", "shipper"]
    for kw in entity_keywords:
        if kw in name:
            return "ENTITY_ID"

    # Numeric / measurement
    if dtype in ("int64", "float64", "int32", "float32"):
        return "NUMERIC_FEATURE"

    # IDs
    id_keywords = ["id", "code", "number", "no", "num"]
    for kw in id_keywords:
        if kw in name:
            return "IDENTIFIER"

    return "CATEGORICAL" if dtype == "object" else "FEATURE"


def map_to_models(col_name: str) -> list:
    """Map column to relevant STRYDER AI ML models."""
    name = col_name.lower()
    models = []

    eta_kw = ["eta", "arrival", "delivery", "travel", "distance", "route", "speed", "time", "duration"]
    delay_kw = ["delay", "late", "breach", "sla", "on_time", "backlog", "pickup"]
    carrier_kw = ["carrier", "driver", "vehicle", "truck", "performance", "reliability"]
    hub_kw = ["warehouse", "hub", "dock", "queue", "capacity", "throughput", "congestion", "facility"]
    cascade_kw = ["cascade", "dependency", "downstream", "impact", "chain", "propagat"]

    for kw in eta_kw:
        if kw in name:
            models.append("ETA_PREDICTION")
            break
    for kw in delay_kw:
        if kw in name:
            models.append("DELAY_RISK")
            break
    for kw in carrier_kw:
        if kw in name:
            models.append("CARRIER_RELIABILITY")
            break
    for kw in hub_kw:
        if kw in name:
            models.append("HUB_CONGESTION")
            break
    for kw in cascade_kw:
        if kw in name:
            models.append("CASCADE_FAILURE")
            break

    return models if models else ["GENERAL"]


def inspect_csv(filepath: Path) -> dict:
    """Full inspection of a single CSV file."""
    print(f"  Inspecting: {filepath.name}")

    try:
        df = pd.read_csv(filepath, encoding="utf-8", low_memory=False)
    except UnicodeDecodeError:
        try:
            df = pd.read_csv(filepath, encoding="latin-1", low_memory=False)
        except Exception as e:
            return {"error": str(e), "file": str(filepath)}

    report = {
        "file": filepath.name,
        "parent_dataset": filepath.parent.name,
        "rows": len(df),
        "columns": len(df.columns),
        "memory_mb": round(df.memory_usage(deep=True).sum() / 1024 / 1024, 2),
        "column_details": [],
        "missing_summary": {},
        "feature_engineering_suggestions": [],
    }

    # Missing value summary
    missing = df.isnull().sum()
    missing_pct = (missing / len(df) * 100).round(2)
    total_missing = int(missing.sum())
    report["missing_summary"] = {
        "total_missing_values": total_missing,
        "total_missing_pct": round(total_missing / (len(df) * len(df.columns)) * 100, 2) if len(df) > 0 else 0,
        "columns_with_missing": int((missing > 0).sum()),
    }

    for col in df.columns:
        col_info = {
            "name": col,
            "dtype": str(df[col].dtype),
            "non_null_count": int(df[col].notna().sum()),
            "null_count": int(df[col].isnull().sum()),
            "null_pct": round(float(df[col].isnull().mean() * 100), 2),
            "unique_count": int(df[col].nunique()),
            "inferred_role": infer_feature_role(col, str(df[col].dtype)),
            "model_relevance": map_to_models(col),
        }

        # Numeric stats + outliers (skip boolean columns)
        if pd.api.types.is_numeric_dtype(df[col]) and not pd.api.types.is_bool_dtype(df[col]):
            try:
                numeric_series = pd.to_numeric(df[col], errors="coerce").dropna()
                if len(numeric_series) > 0:
                    desc = numeric_series.describe()
                    col_info["statistics"] = {
                        "mean": round(float(desc.get("mean", 0)), 4),
                        "std": round(float(desc.get("std", 0)), 4),
                        "min": round(float(desc.get("min", 0)), 4),
                        "25%": round(float(desc.get("25%", 0)), 4),
                        "50%": round(float(desc.get("50%", 0)), 4),
                        "75%": round(float(desc.get("75%", 0)), 4),
                        "max": round(float(desc.get("max", 0)), 4),
                    }
                    if len(numeric_series) > 10:
                        col_info["outliers"] = detect_outliers_iqr(numeric_series)
            except (TypeError, ValueError):
                pass  # Skip columns that can't be processed numerically

        # Categorical: top values
        elif df[col].dtype == "object":
            top_vals = df[col].value_counts().head(10)
            col_info["top_values"] = {str(k): int(v) for k, v in top_vals.items()}
            if df[col].nunique() < 20:
                col_info["all_unique_values"] = sorted(df[col].dropna().unique().tolist())

        report["column_details"].append(col_info)

    # Feature engineering suggestions
    suggestions = []
    cols_lower = [c.lower() for c in df.columns]

    # Temporal feature extraction
    date_cols = [c for c in df.columns if any(kw in c.lower() for kw in ["date", "time", "timestamp"])]
    if date_cols:
        suggestions.append(f"Extract hour/day/month/weekday from temporal columns: {date_cols}")

    # Route distance calculation
    origin_cols = [c for c in df.columns if any(kw in c.lower() for kw in ["origin", "source", "from"])]
    dest_cols = [c for c in df.columns if any(kw in c.lower() for kw in ["destination", "dest", "to"])]
    if origin_cols and dest_cols:
        suggestions.append(f"Compute route distance from origin ({origin_cols}) to destination ({dest_cols})")

    # Delay-related features
    if any("delay" in c for c in cols_lower) or any("late" in c for c in cols_lower):
        suggestions.append("Create binary delay flag and delay severity categories")

    # Carrier aggregation
    if any("carrier" in c for c in cols_lower):
        suggestions.append("Aggregate carrier-level performance metrics (mean delay, on-time rate)")

    # High cardinality encoding
    high_card = [c for c in df.columns if df[c].dtype == "object" and df[c].nunique() > 50]
    if high_card:
        suggestions.append(f"Apply target encoding or hashing for high-cardinality categoricals: {high_card}")

    report["feature_engineering_suggestions"] = suggestions
    return report


def run_full_inspection():
    """Run inspection across all datasets."""
    print("=" * 70)
    print("STRYDER AI - DATASET INSPECTION ENGINE")
    print(f"Started: {datetime.now().isoformat()}")
    print(f"Scanning: {DATA_RAW}")
    print("=" * 70)

    all_reports = []
    dataset_summary = []

    # Walk all subdirectories
    for dataset_dir in sorted(DATA_RAW.iterdir()):
        if not dataset_dir.is_dir():
            continue

        print(f"\nDataset: {dataset_dir.name}")
        print("-" * 50)

        csv_files = sorted(dataset_dir.glob("*.csv"))
        if not csv_files:
            print("  No CSV files found.")
            continue

        for csv_file in csv_files:
            report = inspect_csv(csv_file)
            all_reports.append(report)
            if "error" not in report:
                dataset_summary.append({
                    "dataset": report["parent_dataset"],
                    "file": report["file"],
                    "rows": report["rows"],
                    "columns": report["columns"],
                    "memory_mb": report["memory_mb"],
                    "missing_pct": report["missing_summary"]["total_missing_pct"],
                    "columns_with_missing": report["missing_summary"]["columns_with_missing"],
                })

    # Save full JSON report
    report_path = REPORT_DIR / "dataset_inspection_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(all_reports, f, indent=2, default=str)
    print(f"\nFull report saved: {report_path}")

    # Print summary table
    print("\n" + "=" * 70)
    print("INSPECTION SUMMARY")
    print("=" * 70)
    print(f"{'Dataset':<45} {'File':<50} {'Rows':>8} {'Cols':>5} {'MB':>7} {'Miss%':>6}")
    print("-" * 130)
    for s in dataset_summary:
        print(f"{s['dataset'][:44]:<45} {s['file'][:49]:<50} {s['rows']:>8,} {s['columns']:>5} {s['memory_mb']:>7.1f} {s['missing_pct']:>5.1f}%")

    print(f"\nTotal datasets inspected: {len(dataset_summary)}")
    print(f"Total CSV files: {len(all_reports)}")
    total_rows = sum(s['rows'] for s in dataset_summary)
    print(f"Total data rows: {total_rows:,}")

    # Print model relevance mapping
    print("\n" + "=" * 70)
    print("MODEL RELEVANCE MAPPING")
    print("=" * 70)
    model_cols = {}
    for report in all_reports:
        if "error" in report:
            continue
        for col in report["column_details"]:
            for model in col["model_relevance"]:
                if model not in model_cols:
                    model_cols[model] = []
                model_cols[model].append(f"{report['file']}.{col['name']}")

    for model, cols in sorted(model_cols.items()):
        print(f"\n{model}:")
        for c in cols[:10]:
            print(f"  - {c}")
        if len(cols) > 10:
            print(f"  ... and {len(cols) - 10} more")

    # Print feature engineering suggestions
    print("\n" + "=" * 70)
    print("FEATURE ENGINEERING SUGGESTIONS")
    print("=" * 70)
    for report in all_reports:
        if "error" in report or not report.get("feature_engineering_suggestions"):
            continue
        print(f"\n{report['parent_dataset']} / {report['file']}:")
        for s in report["feature_engineering_suggestions"]:
            print(f"  - {s}")

    # Save summary CSV
    summary_path = REPORT_DIR / "dataset_summary.csv"
    pd.DataFrame(dataset_summary).to_csv(summary_path, index=False)
    print(f"\nSummary CSV saved: {summary_path}")

    return all_reports


if __name__ == "__main__":
    run_full_inspection()
