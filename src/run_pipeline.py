"""
Pipeline Orchestrator
=====================
End-to-end runner: Generate → Bronze → Silver → Gold → Warehouse.
In production this would be an Airflow DAG or ADF pipeline trigger;
here we run the same DAG synchronously for reproducibility.

Usage:
    python src/run_pipeline.py
"""

import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"

STAGES = [
    ("Generate synthetic CDR data",   "generate_cdr.py"),
    ("Bronze: Raw ingestion",         "ingest.py"),
    ("Silver: Clean & validate",      "transform.py"),
    ("Gold: Business aggregations",   "aggregate.py"),
    ("Warehouse: Load to SQLite DW",  "load_warehouse.py"),
]


def run_stage(name: str, script: str) -> bool:
    """Run a single pipeline stage as a subprocess."""
    print("\n" + "▶ " * 30)
    print(f"▶ STAGE: {name}")
    print("▶ " * 30)
    t0 = time.time()
    result = subprocess.run(
        [sys.executable, str(SRC_DIR / script)],
        capture_output=False,
    )
    elapsed = time.time() - t0
    if result.returncode != 0:
        print(f"\n✗ FAILED: {name} (exit={result.returncode})")
        return False
    print(f"\n✓ {name} completed in {elapsed:.1f}s")
    return True


def main():
    print("=" * 70)
    print("TELECOM DATA PIPELINE — End-to-End Run")
    print("=" * 70)
    t_start = time.time()

    for name, script in STAGES:
        ok = run_stage(name, script)
        if not ok:
            print("\n✗ Pipeline halted due to stage failure.")
            sys.exit(1)

    total = time.time() - t_start
    print("\n" + "=" * 70)
    print(f"✅ PIPELINE COMPLETE in {total:.1f}s")
    print("=" * 70)
    print("\nArtifacts produced:")
    print("  data/bronze/*.csv           — raw ingested data")
    print("  data/silver/*.parquet       — cleaned & validated data")
    print("  data/silver/_data_quality_report.json")
    print("  data/gold/*.csv             — analytics-ready tables (for Tableau)")
    print("  data/gold/*.parquet         — analytics-ready tables (for warehouse)")
    print("  warehouse/telecom_dw.db     — SQLite data warehouse")


if __name__ == "__main__":
    main()