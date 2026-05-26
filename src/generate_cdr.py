"""
Synthetic Call Detail Record (CDR) Generator
=============================================
Generates realistic CDR data linked to existing telecom customers.
Mimics raw telecom event data that would land in a data lake from
network operations systems.

CDR fields modeled on real telecom industry standards:
- call_id, customer_id, timestamp, duration_seconds
- call_type (voice/data/sms), cell_tower_id, region
- bytes_transferred (for data sessions)
- call_status (completed/dropped/failed)
"""

import os
import random
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from faker import Faker

# Reproducibility
SEED = 42
random.seed(SEED)
np.random.seed(SEED)
fake = Faker()
Faker.seed(SEED)

# Configuration
PROJECT_ROOT = Path(__file__).resolve().parent.parent
BRONZE_DIR = PROJECT_ROOT / "data" / "bronze"
CDR_OUTPUT = BRONZE_DIR / "cdr_records.csv"
CELL_TOWER_OUTPUT = BRONZE_DIR / "cell_towers.csv"

# Reference data
REGIONS = ["North", "South", "East", "West", "Central"]
CITIES = {
    "North": ["Delhi", "Chandigarh", "Jaipur"],
    "South": ["Bangalore", "Chennai", "Hyderabad"],
    "East": ["Kolkata", "Bhubaneswar", "Patna"],
    "West": ["Mumbai", "Pune", "Ahmedabad"],
    "Central": ["Indore", "Bhopal", "Nagpur"],
}
CALL_TYPES = ["VOICE", "DATA", "SMS"]
CALL_STATUSES = ["COMPLETED", "DROPPED", "FAILED"]


def generate_cell_towers(n_towers: int = 200) -> pd.DataFrame:
    """Generate cell tower reference data."""
    print(f"Generating {n_towers} cell towers...")
    towers = []
    for i in range(n_towers):
        region = random.choice(REGIONS)
        city = random.choice(CITIES[region])
        towers.append({
            "cell_tower_id": f"TWR-{i+1:05d}",
            "region": region,
            "city": city,
            "latitude": round(random.uniform(8.0, 35.0), 6),
            "longitude": round(random.uniform(68.0, 97.0), 6),
            "technology": random.choice(["4G", "5G", "4G", "5G", "4G"]),
            "installation_date": fake.date_between(start_date="-5y", end_date="-1y").isoformat(),
            "capacity_users": random.choice([500, 1000, 2000, 5000]),
        })
    return pd.DataFrame(towers)


def generate_cdrs(customer_ids: list, n_records: int = 50000) -> pd.DataFrame:
    """
    Generate Call Detail Records linked to actual customers.
    Each record represents a network event (call/data/sms).
    """
    print(f"Generating {n_records:,} CDR records for {len(customer_ids)} customers...")

    # Time window: last 90 days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)
    time_range_seconds = int((end_date - start_date).total_seconds())

    tower_ids = [f"TWR-{i+1:05d}" for i in range(200)]

    records = []
    for i in range(n_records):
        customer_id = random.choice(customer_ids)
        call_type = np.random.choice(CALL_TYPES, p=[0.4, 0.45, 0.15])
        # Most calls complete; some drop or fail (realistic distribution)
        status = np.random.choice(CALL_STATUSES, p=[0.92, 0.05, 0.03])

        # Duration logic by call type
        if call_type == "VOICE":
            duration = max(1, int(np.random.exponential(180)))  # avg 3 min
            bytes_transferred = 0
        elif call_type == "DATA":
            duration = max(1, int(np.random.exponential(600)))  # avg 10 min
            bytes_transferred = int(np.random.exponential(50_000_000))  # ~50MB avg
        else:  # SMS
            duration = 1
            bytes_transferred = random.randint(100, 1000)

        # Failed/dropped calls have shorter durations
        if status in ("DROPPED", "FAILED"):
            duration = max(1, int(duration * random.uniform(0.05, 0.3)))

        timestamp = start_date + timedelta(
            seconds=random.randint(0, time_range_seconds)
        )

        records.append({
            "call_id": f"CDR-{i+1:010d}",
            "customer_id": customer_id,
            "timestamp": timestamp.isoformat(),
            "call_type": call_type,
            "duration_seconds": duration,
            "bytes_transferred": bytes_transferred,
            "cell_tower_id": random.choice(tower_ids),
            "call_status": status,
            "cost_usd": round(duration * random.uniform(0.001, 0.01), 4),
        })

        if (i + 1) % 10000 == 0:
            print(f"  Progress: {i+1:,}/{n_records:,}")

    return pd.DataFrame(records)


def main():
    BRONZE_DIR.mkdir(parents=True, exist_ok=True)

    # Generate cell tower master data
    towers_df = generate_cell_towers(n_towers=200)
    towers_df.to_csv(CELL_TOWER_OUTPUT, index=False)
    print(f"✓ Wrote {len(towers_df)} cell tower records → {CELL_TOWER_OUTPUT}")

    # Load existing customer IDs from telco churn dataset
    telco_df = pd.read_csv(BRONZE_DIR / "telco_customer_churn.csv")
    customer_ids = telco_df["customerID"].tolist()

    # Generate CDRs linked to those customers
    cdr_df = generate_cdrs(customer_ids, n_records=50000)
    cdr_df.to_csv(CDR_OUTPUT, index=False)
    print(f"✓ Wrote {len(cdr_df):,} CDR records → {CDR_OUTPUT}")

    print("\n=== Generation Summary ===")
    print(f"  Customers:    {len(customer_ids):,}")
    print(f"  CDR records:  {len(cdr_df):,}")
    print(f"  Cell towers:  {len(towers_df):,}")
    print(f"  CDR by type:\n{cdr_df['call_type'].value_counts().to_string()}")


if __name__ == "__main__":
    main()