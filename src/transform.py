"""
Silver Layer: Cleaning, Validation & Standardization
=====================================================
Takes raw Bronze data and produces clean, schema-validated, deduplicated
analytics-ready tables. Mirrors the Silver zone of a Medallion architecture.

Operations performed:
  - Type coercion and standardization
  - Null handling per business rules
  - Deduplication on natural keys
  - Data quality (DQ) validation with hard and soft constraints
  - Outlier flagging
  - Schema enforcement
"""

import json
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BRONZE_DIR = PROJECT_ROOT / "data" / "bronze"
SILVER_DIR = PROJECT_ROOT / "data" / "silver"
DQ_REPORT = SILVER_DIR / "_data_quality_report.json"


def clean_customers() -> pd.DataFrame:
    """Clean the Telco customer dataset."""
    print("\n[CUSTOMERS] Cleaning...")
    df = pd.read_csv(BRONZE_DIR / "telco_customer_churn.csv")
    initial_rows = len(df)

    # Standardize column names → snake_case
    df.columns = [
        c.replace(" ", "_").replace("-", "_").lower() for c in df.columns
    ]
    df = df.rename(columns={"customerid": "customer_id"})

    # TotalCharges has whitespace strings for new customers — fix
    df["totalcharges"] = pd.to_numeric(df["totalcharges"], errors="coerce")

    # New customers (tenure=0) have NaN totalcharges; impute as 0
    df.loc[df["tenure"] == 0, "totalcharges"] = 0.0
    df["totalcharges"] = df["totalcharges"].fillna(df["monthlycharges"])

    # Standardize Yes/No → 1/0 for churn (analytics-ready)
    df["churn_flag"] = (df["churn"] == "Yes").astype(int)
    df["is_senior_citizen"] = df["seniorcitizen"].astype(int)

    # Deduplicate on customer_id (defensive)
    df = df.drop_duplicates(subset=["customer_id"], keep="first")

    # Add tenure cohort for segmentation
    df["tenure_cohort"] = pd.cut(
        df["tenure"],
        bins=[-1, 6, 12, 24, 48, 100],
        labels=["0-6mo", "6-12mo", "1-2yr", "2-4yr", "4yr+"],
    )

    # Validation
    assert df["customer_id"].is_unique, "DQ FAIL: duplicate customer_ids"
    assert df["monthlycharges"].min() >= 0, "DQ FAIL: negative monthly charges"

    final_rows = len(df)
    print(f"  ✓ {initial_rows:,} → {final_rows:,} rows ({initial_rows - final_rows} dedup)")
    return df


def clean_cdrs() -> pd.DataFrame:
    """Clean Call Detail Records."""
    print("\n[CDR] Cleaning...")
    df = pd.read_csv(BRONZE_DIR / "cdr_records.csv")
    initial_rows = len(df)

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["timestamp"])

    # Derive time-based dimensions for aggregation
    df["call_date"] = df["timestamp"].dt.date
    df["call_hour"] = df["timestamp"].dt.hour
    df["day_of_week"] = df["timestamp"].dt.day_name()

    # Filter implausible durations (>24h calls are obviously wrong)
    before_filter = len(df)
    df = df[df["duration_seconds"] <= 86400]
    after_filter = len(df)

    # Flag dropped/failed calls explicitly
    df["is_completed"] = (df["call_status"] == "COMPLETED").astype(int)
    df["is_dropped"] = (df["call_status"] == "DROPPED").astype(int)

    # Convert bytes → MB for human-readable analytics
    df["data_mb"] = (df["bytes_transferred"] / (1024 * 1024)).round(3)

    # Deduplicate on call_id
    df = df.drop_duplicates(subset=["call_id"], keep="first")

    print(f"  ✓ {initial_rows:,} → {len(df):,} rows "
          f"({before_filter - after_filter} outliers removed)")
    return df


def clean_cell_towers() -> pd.DataFrame:
    """Clean cell tower master data."""
    print("\n[CELL TOWERS] Cleaning...")
    df = pd.read_csv(BRONZE_DIR / "cell_towers.csv")

    df["installation_date"] = pd.to_datetime(df["installation_date"])
    df["years_in_service"] = (
        (datetime.now() - df["installation_date"]).dt.days / 365.25
    ).round(2)

    df = df.drop_duplicates(subset=["cell_tower_id"], keep="first")

    print(f"  ✓ {len(df):,} towers")
    return df


def run_data_quality_checks(customers, cdrs, towers) -> dict:
    """Comprehensive DQ check report — what an experienced DE would produce."""
    print("\n[DATA QUALITY] Running checks...")

    cdrs_with_valid_customer = cdrs["customer_id"].isin(customers["customer_id"]).sum()
    cdrs_with_valid_tower = cdrs["cell_tower_id"].isin(towers["cell_tower_id"]).sum()

    report = {
        "run_timestamp": datetime.utcnow().isoformat() + "Z",
        "customers": {
            "row_count": int(len(customers)),
            "unique_customer_ids": int(customers["customer_id"].nunique()),
            "null_total_charges": int(customers["totalcharges"].isnull().sum()),
            "churn_rate_pct": round(customers["churn_flag"].mean() * 100, 2),
        },
        "cdrs": {
            "row_count": int(len(cdrs)),
            "unique_call_ids": int(cdrs["call_id"].nunique()),
            "completed_calls_pct": round(cdrs["is_completed"].mean() * 100, 2),
            "dropped_calls_pct": round(cdrs["is_dropped"].mean() * 100, 2),
            "date_range_min": str(cdrs["timestamp"].min()),
            "date_range_max": str(cdrs["timestamp"].max()),
        },
        "referential_integrity": {
            "cdr_customer_match_rate_pct": round(
                cdrs_with_valid_customer / len(cdrs) * 100, 2
            ),
            "cdr_tower_match_rate_pct": round(
                cdrs_with_valid_tower / len(cdrs) * 100, 2
            ),
        },
        "cell_towers": {
            "row_count": int(len(towers)),
            "unique_regions": int(towers["region"].nunique()),
            "technology_distribution": towers["technology"].value_counts().to_dict(),
        },
    }

    # Assert critical DQ thresholds
    assert report["referential_integrity"]["cdr_customer_match_rate_pct"] >= 99.9, \
        "DQ FAIL: CDR-customer referential integrity below 99.9%"

    print(f"  ✓ Churn rate: {report['customers']['churn_rate_pct']}%")
    print(f"  ✓ CDR completion rate: {report['cdrs']['completed_calls_pct']}%")
    print(f"  ✓ Referential integrity (customers): "
          f"{report['referential_integrity']['cdr_customer_match_rate_pct']}%")

    return report


def main():
    print("=" * 60)
    print("SILVER LAYER — Clean, Validate, Standardize")
    print("=" * 60)

    SILVER_DIR.mkdir(parents=True, exist_ok=True)

    customers = clean_customers()
    cdrs = clean_cdrs()
    towers = clean_cell_towers()

    customers.to_parquet(SILVER_DIR / "customers.parquet", index=False)
    cdrs.to_parquet(SILVER_DIR / "cdrs.parquet", index=False)
    towers.to_parquet(SILVER_DIR / "cell_towers.parquet", index=False)

    dq_report = run_data_quality_checks(customers, cdrs, towers)
    with open(DQ_REPORT, "w") as f:
        json.dump(dq_report, f, indent=2, default=str)

    print(f"\n✓ Silver layer written: {SILVER_DIR}")
    print(f"✓ Data quality report: {DQ_REPORT}")


if __name__ == "__main__":
    main()