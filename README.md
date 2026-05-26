# 📡 Telecom Customer Analytics Platform

> End-to-end data engineering project: ETL pipeline, layered data warehouse, SQL analytics, and interactive dashboard — built on real telecom customer data with 50,000 synthetic CDR records.

**🔗 [Live Dashboard](https://cherukunithish21.github.io/telecom-data-analytics-platform/dashboards/telecom_dashboard.html)** &nbsp;·&nbsp; **📊 [Dashboard Source](./src/build_dashboard.py)** &nbsp;·&nbsp; **🗄️ [Warehouse Schema](./sql/schema.sql)**

---

## 📈 Headline Metrics

| Metric | Value |
|---|---|
| Customers processed | **7,043** |
| CDR events generated & ingested | **50,000** |
| Cell towers modeled | **200** across 5 regions |
| Monthly recurring revenue | **$456,117** |
| Churn rate | **26.5%** |
| Monthly revenue at risk | **$139,131** |
| End-to-end pipeline runtime | **~13 seconds** |

---

## 🏗️ Architecture

```mermaid
flowchart LR
    A[Raw Sources<br/>CSV / JSON] -->|Ingest| B[Bronze Layer<br/>data/bronze]
    B -->|Clean & Validate| C[Silver Layer<br/>data/silver<br/>+ DQ Report]
    C -->|Aggregate| D[Gold Layer<br/>data/gold<br/>Fact/Dim tables]
    D -->|Load| E[(SQLite Warehouse<br/>star schema)]
    D -->|Visualize| F[Interactive Dashboard<br/>Plotly HTML]
    E -->|Query| G[Analytics SQL<br/>10 business questions]

    style A fill:#1e3a8a,color:#fff
    style B fill:#92400e,color:#fff
    style C fill:#9ca3af,color:#fff
    style D fill:#facc15,color:#000
    style E fill:#0ea5e9,color:#fff
    style F fill:#10b981,color:#fff
    style G fill:#dc2626,color:#fff
```

**Medallion architecture** (Bronze → Silver → Gold) mirrors what runs in production on Azure Synapse / Snowflake / Databricks. SQLite is used here for portability — same SQL, zero install.

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Language | **Python 3.12**, **SQL** |
| Data processing | **Pandas**, **NumPy**, **PyArrow** (Parquet) |
| Warehouse | **SQLite** (SQL syntax compatible with Synapse / Snowflake) |
| Orchestration | Modular pipeline runner (Airflow-ready) |
| Visualization | **Plotly** (interactive HTML dashboard) |
| Data quality | Custom DQ framework with referential-integrity assertions |
| Storage formats | CSV (raw), Parquet (cleaned), SQLite (warehouse) |
| Version control | Git, GitHub |

In production this would map to: **Azure Data Factory** (orchestration), **ADLS** (data lake), **Azure Synapse** (warehouse), **Power BI** (dashboards).

---

## 📂 Project Structure