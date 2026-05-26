"""
Warehouse Loader
=================
Loads Gold-layer tables into a SQLite warehouse with proper schema
constraints, indexes, and primary keys.

In production this would target Azure Synapse Analytics, Snowflake,
or Redshift. SQLite is used here for portability — same SQL,
zero install. The schema mirrors what would run in the cloud DW.
"""

import sqlite3
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GOLD_DIR = PROJECT_ROOT / "data" / "gold"
WAREHOUSE_DB = PROJECT_ROOT / "warehouse" / "telecom_dw.db"
SCHEMA_SQL = PROJECT_ROOT / "sql" / "schema.sql"


def create_schema(conn: sqlite3.Connection):
    """Execute schema DDL from sql/schema.sql."""
    print("\n[SCHEMA] Creating warehouse schema...")
    with open(SCHEMA_SQL) as f:
        ddl = f.read()
    conn.executescript(ddl)
    conn.commit()
    print("  ✓ Schema created")


def load_table(conn: sqlite3.Connection, table_name: str, parquet_file: str):
    """Truncate-and-load a Gold table into the warehouse."""
    df = pd.read_parquet(GOLD_DIR / parquet_file)

    # Drop columns whose dtypes SQLite can't handle natively (e.g. categoricals)
    for col in df.columns:
        if df[col].dtype.name == "category":
            df[col] = df[col].astype(str)
        elif "datetime" in df[col].dtype.name:
            df[col] = df[col].astype(str)

    conn.execute(f"DELETE FROM {table_name}")
    df.to_sql(table_name, conn, if_exists="append", index=False)
    conn.commit()

    row_count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
    print(f"  ✓ {table_name}: {row_count:,} rows")


def main():
    print("=" * 60)
    print("WAREHOUSE LOADER — Loading Gold to SQLite DW")
    print("=" * 60)

    WAREHOUSE_DB.parent.mkdir(parents=True, exist_ok=True)
    if WAREHOUSE_DB.exists():
        WAREHOUSE_DB.unlink()  # fresh load each run

    conn = sqlite3.connect(WAREHOUSE_DB)

    create_schema(conn)

    print("\n[LOAD] Loading dimension and fact tables...")
    load_table(conn, "dim_cell_towers", "dim_cell_towers.parquet")
    load_table(conn, "fact_customer_summary", "fact_customer_summary.parquet")
    load_table(conn, "fact_daily_network_metrics", "fact_daily_network_metrics.parquet")
    load_table(conn, "fact_regional_performance", "fact_regional_performance.parquet")
    load_table(conn, "fact_churn_cohort", "fact_churn_cohort.parquet")

    # Verify with a sample query
    print("\n[VERIFY] Running smoke-test queries...")
    sample = conn.execute("""
        SELECT region, total_calls, drop_rate_pct, revenue_per_customer_usd
        FROM fact_regional_performance
        ORDER BY total_calls DESC
    """).fetchall()

    print("\n  Regional Performance Snapshot:")
    print("  " + "-" * 60)
    print(f"  {'Region':<10} {'Calls':>10} {'Drop %':>10} {'Rev/Customer':>15}")
    for row in sample:
        print(f"  {row[0]:<10} {row[1]:>10,} {row[2]:>10.2f} ${row[3]:>14.2f}")

    conn.close()
    print(f"\n✓ Warehouse loaded: {WAREHOUSE_DB}")


if __name__ == "__main__":
    main()