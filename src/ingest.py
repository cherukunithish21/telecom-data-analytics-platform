"""
Bronze Layer: Raw Data Ingestion
=================================
Validates source files exist, captures metadata, performs basic
audit logging. Mirrors the first stage of a production data lake
pipeline (raw zone — append-only, immutable).

In production this stage would:
  - Ingest from source systems via Azure Data Factory / Kafka / Event Hubs
  - Land raw files in ADLS / S3 with date partitions
  - Capture file-level metadata for lineage tracking

Here we operate on local CSV inputs but produce the same audit artifacts.
"""

import hashlib
import json
from datetime import datetime
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BRONZE_DIR = PROJECT_ROOT / "data" / "bronze"
AUDIT_LOG = BRONZE_DIR / "_ingestion_audit.json"

EXPECTED_SOURCES = {
    "telco_customer_churn.csv": {
        "description": "Customer demographics, services, and churn label",
        "key_column": "customerID",
    },
    "cdr_records.csv": {
        "description": "Call Detail Records — network usage events",
        "key_column": "call_id",
    },
    "cell_towers.csv": {
        "description": "Cell tower master / reference data",
        "key_column": "cell_tower_id",
    },
}


def file_checksum(filepath: Path) -> str:
    """Compute SHA256 checksum — used for lineage / change detection."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def ingest_source(filename: str, metadata: dict) -> dict:
    """Validate and inventory a single source file."""
    filepath = BRONZE_DIR / filename
    if not filepath.exists():
        raise FileNotFoundError(f"Bronze source missing: {filepath}")

    df = pd.read_csv(filepath)
    record = {
        "filename": filename,
        "description": metadata["description"],
        "key_column": metadata["key_column"],
        "row_count": len(df),
        "column_count": len(df.columns),
        "columns": df.columns.tolist(),
        "size_bytes": filepath.stat().st_size,
        "checksum_sha256_16": file_checksum(filepath),
        "ingested_at": datetime.utcnow().isoformat() + "Z",
        "null_counts": df.isnull().sum().to_dict(),
    }
    print(f"  ✓ {filename}: {record['row_count']:,} rows, {record['column_count']} cols")
    return record


def main():
    print("=" * 60)
    print("BRONZE LAYER — Raw Ingestion & Audit")
    print("=" * 60)

    audit_records = []
    for filename, metadata in EXPECTED_SOURCES.items():
        record = ingest_source(filename, metadata)
        audit_records.append(record)

    audit = {
        "pipeline_run_id": datetime.utcnow().strftime("%Y%m%d_%H%M%S"),
        "stage": "bronze",
        "sources": audit_records,
    }

    with open(AUDIT_LOG, "w") as f:
        json.dump(audit, f, indent=2)
    print(f"\n✓ Audit log written → {AUDIT_LOG}")
    print(f"  Total sources: {len(audit_records)}")
    print(f"  Total rows ingested: {sum(r['row_count'] for r in audit_records):,}")


if __name__ == "__main__":
    main()