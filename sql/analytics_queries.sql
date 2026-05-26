-- =====================================================================
-- TELECOM DATA WAREHOUSE — ANALYTICS QUERIES
-- =====================================================================
-- Business questions answered by the warehouse. Each query is written
-- for the dashboard consumer (Tableau / Power BI) and tuned for the
-- indexes defined in schema.sql.
-- =====================================================================


-- ---------------------------------------------------------------------
-- Q1. EXECUTIVE KPIs — top-line for the leadership dashboard
-- ---------------------------------------------------------------------
SELECT
    COUNT(*)                                              AS total_customers,
    SUM(churn_flag)                                       AS churned_customers,
    ROUND(AVG(churn_flag) * 100, 2)                       AS churn_rate_pct,
    ROUND(SUM(monthlycharges), 2)                         AS monthly_revenue_usd,
    ROUND(AVG(monthlycharges), 2)                         AS arpu_usd,
    ROUND(SUM(estimated_clv_usd), 2)                      AS total_clv_usd,
    ROUND(AVG(tenure), 1)                                 AS avg_tenure_months
FROM fact_customer_summary;


-- ---------------------------------------------------------------------
-- Q2. CHURN BY CONTRACT TYPE — single biggest churn driver
-- ---------------------------------------------------------------------
SELECT
    contract,
    COUNT(*)                                              AS customer_count,
    SUM(churn_flag)                                       AS churned,
    ROUND(AVG(churn_flag) * 100, 2)                       AS churn_rate_pct,
    ROUND(AVG(monthlycharges), 2)                         AS avg_monthly_charges,
    ROUND(AVG(tenure), 1)                                 AS avg_tenure_months
FROM fact_customer_summary
GROUP BY contract
ORDER BY churn_rate_pct DESC;


-- ---------------------------------------------------------------------
-- Q3. HIGH-RISK SEGMENTS — top 10 churn cohorts
-- ---------------------------------------------------------------------
SELECT
    tenure_cohort,
    contract,
    paymentmethod,
    customer_count,
    churn_count,
    churn_rate_pct,
    ROUND(avg_monthly_charges, 2)                         AS avg_monthly_charges
FROM fact_churn_cohort
WHERE customer_count >= 50
ORDER BY churn_rate_pct DESC
LIMIT 10;


-- ---------------------------------------------------------------------
-- Q4. SERVICE-LINE CHURN — internet service & churn correlation
-- ---------------------------------------------------------------------
SELECT
    internetservice,
    COUNT(*)                                              AS customers,
    SUM(churn_flag)                                       AS churned,
    ROUND(AVG(churn_flag) * 100, 2)                       AS churn_rate_pct,
    ROUND(AVG(monthlycharges), 2)                         AS arpu
FROM fact_customer_summary
GROUP BY internetservice
ORDER BY churn_rate_pct DESC;


-- ---------------------------------------------------------------------
-- Q5. REVENUE AT RISK — high-value customers likely to churn
-- ---------------------------------------------------------------------
SELECT
    tenure_cohort,
    contract,
    COUNT(*)                                              AS at_risk_customer_count,
    ROUND(SUM(monthlycharges), 2)                         AS monthly_revenue_at_risk_usd,
    ROUND(SUM(estimated_clv_usd), 2)                      AS clv_at_risk_usd
FROM fact_customer_summary
WHERE churn_flag = 0
  AND contract = 'Month-to-month'
  AND monthlycharges > 70
GROUP BY tenure_cohort, contract
ORDER BY monthly_revenue_at_risk_usd DESC;


-- ---------------------------------------------------------------------
-- Q6. NETWORK PERFORMANCE BY REGION — operations dashboard
-- ---------------------------------------------------------------------
SELECT
    region,
    total_calls,
    completed_calls,
    dropped_calls,
    drop_rate_pct,
    ROUND(total_data_mb / 1024, 2)                        AS total_data_gb,
    active_towers,
    ROUND(total_calls * 1.0 / active_towers, 1)           AS calls_per_tower,
    revenue_per_customer_usd
FROM fact_regional_performance
ORDER BY total_calls DESC;


-- ---------------------------------------------------------------------
-- Q7. DAILY NETWORK HEALTH TREND — for SRE dashboards
-- ---------------------------------------------------------------------
SELECT
    call_date,
    total_calls,
    drop_rate_pct,
    call_success_rate_pct,
    unique_customers_active,
    ROUND(total_data_mb / 1024, 2)                        AS data_gb,
    ROUND(total_revenue_usd, 2)                           AS revenue_usd
FROM fact_daily_network_metrics
ORDER BY call_date DESC
LIMIT 30;


-- ---------------------------------------------------------------------
-- Q8. ENGAGEMENT vs CHURN — does usage predict retention?
-- ---------------------------------------------------------------------
SELECT
    CASE
        WHEN engagement_score < 25 THEN '1_Low (0-25)'
        WHEN engagement_score < 50 THEN '2_Mid-Low (25-50)'
        WHEN engagement_score < 75 THEN '3_Mid-High (50-75)'
        ELSE '4_High (75-100)'
    END                                                   AS engagement_band,
    COUNT(*)                                              AS customers,
    ROUND(AVG(churn_flag) * 100, 2)                       AS churn_rate_pct,
    ROUND(AVG(monthlycharges), 2)                         AS avg_arpu,
    ROUND(AVG(total_data_mb), 2)                          AS avg_data_mb,
    ROUND(AVG(total_calls), 1)                            AS avg_calls
FROM fact_customer_summary
GROUP BY engagement_band
ORDER BY engagement_band;


-- ---------------------------------------------------------------------
-- Q9. PAYMENT METHOD vs CHURN — common interview ask
-- ---------------------------------------------------------------------
SELECT
    paymentmethod,
    COUNT(*)                                              AS customers,
    ROUND(AVG(churn_flag) * 100, 2)                       AS churn_rate_pct,
    ROUND(AVG(monthlycharges), 2)                         AS avg_arpu,
    ROUND(AVG(tenure), 1)                                 AS avg_tenure
FROM fact_customer_summary
GROUP BY paymentmethod
ORDER BY churn_rate_pct DESC;


-- ---------------------------------------------------------------------
-- Q10. TENURE COHORT REVENUE — retention curve
-- ---------------------------------------------------------------------
SELECT
    tenure_cohort,
    COUNT(*)                                              AS customers,
    ROUND(AVG(churn_flag) * 100, 2)                       AS churn_rate_pct,
    ROUND(SUM(monthlycharges), 2)                         AS monthly_revenue_usd,
    ROUND(AVG(estimated_clv_usd), 2)                      AS avg_clv_usd
FROM fact_customer_summary
GROUP BY tenure_cohort
ORDER BY tenure_cohort;