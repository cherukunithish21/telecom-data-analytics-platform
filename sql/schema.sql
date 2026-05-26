-- ============================================================
-- Telecom Data Warehouse — Schema DDL
-- ============================================================
-- Star-schema-style design for analytics workloads.
-- Mirrors what would be deployed on Azure Synapse / Snowflake;
-- SQLite-compatible syntax used here for portability.
-- ============================================================

-- ---------- Dimension tables ----------

DROP TABLE IF EXISTS dim_cell_towers;
CREATE TABLE dim_cell_towers (
    cell_tower_id       TEXT PRIMARY KEY,
    region              TEXT NOT NULL,
    city                TEXT,
    latitude            REAL,
    longitude           REAL,
    technology          TEXT CHECK (technology IN ('4G', '5G', '3G')),
    installation_date   TEXT,
    capacity_users      INTEGER,
    years_in_service    REAL
);

CREATE INDEX idx_towers_region     ON dim_cell_towers(region);
CREATE INDEX idx_towers_technology ON dim_cell_towers(technology);


-- ---------- Fact tables ----------

DROP TABLE IF EXISTS fact_customer_summary;
CREATE TABLE fact_customer_summary (
    customer_id              TEXT PRIMARY KEY,
    gender                   TEXT,
    is_senior_citizen        INTEGER,
    partner                  TEXT,
    dependents               TEXT,
    tenure                   INTEGER,
    phoneservice             TEXT,
    multiplelines            TEXT,
    internetservice          TEXT,
    onlinesecurity           TEXT,
    onlinebackup             TEXT,
    deviceprotection         TEXT,
    techsupport              TEXT,
    streamingtv              TEXT,
    streamingmovies          TEXT,
    contract                 TEXT,
    paperlessbilling         TEXT,
    paymentmethod            TEXT,
    monthlycharges           REAL,
    totalcharges             REAL,
    churn                    TEXT,
    seniorcitizen            INTEGER,
    churn_flag               INTEGER NOT NULL,
    tenure_cohort            TEXT,
    total_calls              INTEGER DEFAULT 0,
    total_voice_minutes      REAL DEFAULT 0,
    total_data_mb            REAL DEFAULT 0,
    total_sms                INTEGER DEFAULT 0,
    dropped_calls            INTEGER DEFAULT 0,
    avg_call_duration_sec    REAL DEFAULT 0,
    last_activity_date       TEXT,
    engagement_score         REAL,
    estimated_clv_usd        REAL
);

CREATE INDEX idx_cust_churn      ON fact_customer_summary(churn_flag);
CREATE INDEX idx_cust_contract   ON fact_customer_summary(contract);
CREATE INDEX idx_cust_tenure     ON fact_customer_summary(tenure_cohort);
CREATE INDEX idx_cust_payment    ON fact_customer_summary(paymentmethod);


DROP TABLE IF EXISTS fact_daily_network_metrics;
CREATE TABLE fact_daily_network_metrics (
    call_date                TEXT PRIMARY KEY,
    total_calls              INTEGER NOT NULL,
    completed_calls          INTEGER NOT NULL,
    dropped_calls            INTEGER NOT NULL,
    unique_customers_active  INTEGER NOT NULL,
    total_data_mb            REAL,
    avg_duration_sec         REAL,
    total_revenue_usd        REAL,
    drop_rate_pct            REAL,
    call_success_rate_pct    REAL
);

CREATE INDEX idx_daily_date ON fact_daily_network_metrics(call_date);


DROP TABLE IF EXISTS fact_regional_performance;
CREATE TABLE fact_regional_performance (
    region                       TEXT PRIMARY KEY,
    total_calls                  INTEGER,
    completed_calls              INTEGER,
    dropped_calls                INTEGER,
    unique_customers             INTEGER,
    total_data_mb                REAL,
    total_revenue_usd            REAL,
    active_towers                INTEGER,
    drop_rate_pct                REAL,
    revenue_per_customer_usd     REAL
);


DROP TABLE IF EXISTS fact_churn_cohort;
CREATE TABLE fact_churn_cohort (
    tenure_cohort           TEXT,
    contract                TEXT,
    paymentmethod           TEXT,
    customer_count          INTEGER,
    churn_count             INTEGER,
    avg_monthly_charges     REAL,
    avg_total_charges       REAL,
    avg_clv                 REAL,
    churn_rate_pct          REAL,
    PRIMARY KEY (tenure_cohort, contract, paymentmethod)
);

CREATE INDEX idx_cohort_churn ON fact_churn_cohort(churn_rate_pct);