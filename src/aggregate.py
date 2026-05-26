"""
Gold Layer: Business Aggregations
==================================
Builds analytics-ready aggregate tables for dashboards and reporting.
These tables back the Tableau dashboards and BI consumers.

Star-schema-style outputs:
  - fact_customer_summary      (one row per customer, KPIs)
  - fact_daily_network_metrics (one row per day, network health)
  - fact_regional_performance  (one row per region, geo analytics)
  - dim_customers              (customer dimension)
  - dim_cell_towers            (tower dimension)
"""

from datetime import datetime
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SILVER_DIR = PROJECT_ROOT / "data" / "silver"
GOLD_DIR = PROJECT_ROOT / "data" / "gold"


def build_customer_summary(customers: pd.DataFrame, cdrs: pd.DataFrame) -> pd.DataFrame:
    """One row per customer with engagement + churn KPIs."""
    print("\n[FACT] Building customer summary...")

    cdr_agg = cdrs.groupby("customer_id").agg(
        total_calls=("call_id", "count"),
        total_voice_minutes=("duration_seconds", lambda x: round(x[cdrs.loc[x.index, "call_type"] == "VOICE"].sum() / 60, 2)),
        total_data_mb=("data_mb", "sum"),
        total_sms=("call_type", lambda x: (x == "SMS").sum()),
        dropped_calls=("is_dropped", "sum"),
        avg_call_duration_sec=("duration_seconds", "mean"),
        last_activity_date=("timestamp", "max"),
    ).reset_index()

    summary = customers.merge(cdr_agg, on="customer_id", how="left").fillna({
        "total_calls": 0, "total_voice_minutes": 0, "total_data_mb": 0,
        "total_sms": 0, "dropped_calls": 0, "avg_call_duration_sec": 0,
    })

    # Engagement score: composite of activity metrics, scaled 0-100
    summary["engagement_score"] = (
        (summary["total_calls"].rank(pct=True) * 40)
        + (summary["total_data_mb"].rank(pct=True) * 40)
        + (summary["tenure"].rank(pct=True) * 20)
    ).round(2)

    # Customer lifetime value (CLV) proxy
    summary["estimated_clv_usd"] = (
        summary["monthlycharges"] * summary["tenure"]
    ).round(2)

    print(f"  ✓ {len(summary):,} customer summary rows")
    return summary


def build_daily_network_metrics(cdrs: pd.DataFrame) -> pd.DataFrame:
    """One row per day — network operations KPIs."""
    print("\n[FACT] Building daily network metrics...")

    daily = cdrs.groupby("call_date").agg(
        total_calls=("call_id", "count"),
        completed_calls=("is_completed", "sum"),
        dropped_calls=("is_dropped", "sum"),
        unique_customers_active=("customer_id", "nunique"),
        total_data_mb=("data_mb", "sum"),
        avg_duration_sec=("duration_seconds", "mean"),
        total_revenue_usd=("cost_usd", "sum"),
    ).reset_index()

    daily["drop_rate_pct"] = (
        daily["dropped_calls"] / daily["total_calls"] * 100
    ).round(3)
    daily["call_success_rate_pct"] = (
        daily["completed_calls"] / daily["total_calls"] * 100
    ).round(3)

    print(f"  ✓ {len(daily)} day rows")
    return daily


def build_regional_performance(cdrs: pd.DataFrame, towers: pd.DataFrame) -> pd.DataFrame:
    """Network performance per region — for geo dashboards."""
    print("\n[FACT] Building regional performance...")

    cdrs_with_region = cdrs.merge(
        towers[["cell_tower_id", "region", "city", "technology"]],
        on="cell_tower_id",
        how="left",
    )

    regional = cdrs_with_region.groupby("region").agg(
        total_calls=("call_id", "count"),
        completed_calls=("is_completed", "sum"),
        dropped_calls=("is_dropped", "sum"),
        unique_customers=("customer_id", "nunique"),
        total_data_mb=("data_mb", "sum"),
        total_revenue_usd=("cost_usd", "sum"),
        active_towers=("cell_tower_id", "nunique"),
    ).reset_index()

    regional["drop_rate_pct"] = (
        regional["dropped_calls"] / regional["total_calls"] * 100
    ).round(3)
    regional["revenue_per_customer_usd"] = (
        regional["total_revenue_usd"] / regional["unique_customers"]
    ).round(2)

    print(f"  ✓ {len(regional)} regions")
    return regional


def build_churn_cohort_analysis(customers: pd.DataFrame) -> pd.DataFrame:
    """Churn breakdown by tenure cohort, contract, payment method."""
    print("\n[FACT] Building churn cohort analysis...")

    by_cohort = customers.groupby(["tenure_cohort", "contract", "paymentmethod"], observed=True).agg(
        customer_count=("customer_id", "count"),
        churn_count=("churn_flag", "sum"),
        avg_monthly_charges=("monthlycharges", "mean"),
        avg_total_charges=("totalcharges", "mean"),
        avg_clv=("estimated_clv_usd", "mean"),
    ).reset_index()

    by_cohort["churn_rate_pct"] = (
        by_cohort["churn_count"] / by_cohort["customer_count"] * 100
    ).round(2)

    by_cohort = by_cohort.sort_values("churn_rate_pct", ascending=False)

    print(f"  ✓ {len(by_cohort)} cohort segments")
    return by_cohort


def main():
    print("=" * 60)
    print("GOLD LAYER — Business Aggregations")
    print("=" * 60)

    GOLD_DIR.mkdir(parents=True, exist_ok=True)

    customers = pd.read_parquet(SILVER_DIR / "customers.parquet")
    cdrs = pd.read_parquet(SILVER_DIR / "cdrs.parquet")
    towers = pd.read_parquet(SILVER_DIR / "cell_towers.parquet")

    # Build all aggregate tables
    customer_summary = build_customer_summary(customers, cdrs)
    daily_network = build_daily_network_metrics(cdrs)
    regional = build_regional_performance(cdrs, towers)
    churn_cohort = build_churn_cohort_analysis(customer_summary)

    # Write Gold tables — both CSV (for Tableau) and Parquet (for warehouse)
    customer_summary.to_csv(GOLD_DIR / "fact_customer_summary.csv", index=False)
    customer_summary.to_parquet(GOLD_DIR / "fact_customer_summary.parquet", index=False)

    daily_network.to_csv(GOLD_DIR / "fact_daily_network_metrics.csv", index=False)
    daily_network.to_parquet(GOLD_DIR / "fact_daily_network_metrics.parquet", index=False)

    regional.to_csv(GOLD_DIR / "fact_regional_performance.csv", index=False)
    regional.to_parquet(GOLD_DIR / "fact_regional_performance.parquet", index=False)

    churn_cohort.to_csv(GOLD_DIR / "fact_churn_cohort.csv", index=False)
    churn_cohort.to_parquet(GOLD_DIR / "fact_churn_cohort.parquet", index=False)

    # Dimension tables
    towers.to_csv(GOLD_DIR / "dim_cell_towers.csv", index=False)
    towers.to_parquet(GOLD_DIR / "dim_cell_towers.parquet", index=False)

    print(f"\n✓ Gold layer written: {GOLD_DIR}")
    print(f"\n=== Top 5 Churn Cohorts ===")
    print(churn_cohort.head(5).to_string(index=False))


if __name__ == "__main__":
    main()