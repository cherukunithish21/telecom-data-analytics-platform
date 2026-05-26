-- =====================================================================
-- SQL OPTIMIZATION EXAMPLES
-- =====================================================================
-- Demonstrates how index design, query rewrites, and predicate pushdown
-- materially affect performance on the warehouse. Each block shows the
-- "before" / naive form and the "after" / tuned form.
-- =====================================================================


-- ---------------------------------------------------------------------
-- EXAMPLE 1: Predicate pushdown beats post-aggregation filtering
-- ---------------------------------------------------------------------

-- ❌ SLOW: aggregate everything, then filter
-- SQLite has to compute churn_rate_pct for ALL contracts then discard most.
SELECT contract, AVG(churn_flag) * 100 AS churn_rate_pct
FROM fact_customer_summary
GROUP BY contract
HAVING contract = 'Month-to-month';

-- ✅ FAST: push the filter down before aggregation
-- Index on contract (idx_cust_contract) is now actually useful.
SELECT contract, AVG(churn_flag) * 100 AS churn_rate_pct
FROM fact_customer_summary
WHERE contract = 'Month-to-month'
GROUP BY contract;


-- ---------------------------------------------------------------------
-- EXAMPLE 2: COUNT(DISTINCT) vs GROUP BY for cardinality estimation
-- ---------------------------------------------------------------------

-- ❌ SLOW for very large tables: implicit hash-distinct
-- SELECT region, COUNT(DISTINCT customer_id) FROM fact_regional_performance
-- JOIN fact_customer_summary USING (...) GROUP BY region;
-- (Pseudocode; demonstrates the anti-pattern at scale)

-- ✅ FAST: pre-aggregate to one row per customer first, then count
-- This is exactly the pattern the Gold layer already materializes.
SELECT region, unique_customers FROM fact_regional_performance;


-- ---------------------------------------------------------------------
-- EXAMPLE 3: Index utilization — composite index design
-- ---------------------------------------------------------------------

-- We want top churn cohorts. With idx_cohort_churn on (churn_rate_pct),
-- the optimizer can use the index for the ORDER BY + LIMIT.

EXPLAIN QUERY PLAN
SELECT tenure_cohort, contract, paymentmethod, churn_rate_pct
FROM fact_churn_cohort
WHERE customer_count >= 50
ORDER BY churn_rate_pct DESC
LIMIT 10;


-- ---------------------------------------------------------------------
-- EXAMPLE 4: Avoid functions on indexed columns
-- ---------------------------------------------------------------------

-- ❌ SLOW: function on the indexed column kills the index
SELECT * FROM fact_customer_summary
WHERE UPPER(contract) = 'MONTH-TO-MONTH';

-- ✅ FAST: compare against the indexed column as-is
SELECT * FROM fact_customer_summary
WHERE contract = 'Month-to-month';


-- ---------------------------------------------------------------------
-- EXAMPLE 5: Window functions for ranking — replaces correlated subqueries
-- ---------------------------------------------------------------------

-- Rank customers by CLV within each tenure cohort.
-- Correlated subquery version would be O(N²); window function is O(N log N).
SELECT
    customer_id,
    tenure_cohort,
    estimated_clv_usd,
    RANK() OVER (
        PARTITION BY tenure_cohort
        ORDER BY estimated_clv_usd DESC
    ) AS clv_rank_in_cohort
FROM fact_customer_summary
WHERE churn_flag = 0
ORDER BY tenure_cohort, clv_rank_in_cohort
LIMIT 50;


-- ---------------------------------------------------------------------
-- EXAMPLE 6: CTE for readability (no perf cost when the planner inlines)
-- ---------------------------------------------------------------------

WITH at_risk AS (
    SELECT customer_id, monthlycharges, contract, tenure_cohort
    FROM fact_customer_summary
    WHERE churn_flag = 0
      AND contract = 'Month-to-month'
      AND monthlycharges > 70
),
cohort_summary AS (
    SELECT tenure_cohort,
           COUNT(*)                     AS at_risk_count,
           SUM(monthlycharges)          AS monthly_revenue_at_risk
    FROM at_risk
    GROUP BY tenure_cohort
)
SELECT *
FROM cohort_summary
ORDER BY monthly_revenue_at_risk DESC;