-- Accord Retail: deterministic customer-retention data preparation
-- Reassigns existing sales to existing customers WITHIN THE SAME BUSINESS.
-- It does not alter sale revenue, quantity, product, channel, discount, or sale_date.
-- Goal with current data: ~60% customers observed, ~40% profile-only.

BEGIN;

-- 1) Rank customers within each business and choose the first 60% as the
-- observed transaction population.
CREATE TEMP TABLE retention_customer_pool ON COMMIT DROP AS
WITH ranked AS (
    SELECT
        c.business_id,
        c.customer_id,
        ROW_NUMBER() OVER (
            PARTITION BY c.business_id ORDER BY c.customer_id
        ) AS customer_rank,
        COUNT(*) OVER (PARTITION BY c.business_id) AS customer_count
    FROM runtime.customer c
)
SELECT
    business_id,
    customer_id,
    customer_rank,
    customer_count,
    GREATEST(1, FLOOR(customer_count * 0.60)::INT) AS observed_customer_count
FROM ranked;

CREATE INDEX ON retention_customer_pool (business_id, customer_rank);

-- 2) Rank sales within each business. Simple modulo assignment guarantees that
-- every eligible customer receives a sale whenever sales >= eligible customers.
CREATE TEMP TABLE retention_sale_assignment ON COMMIT DROP AS
WITH sale_ranked AS (
    SELECT
        s.sale_id,
        s.business_id,
        ROW_NUMBER() OVER (
            PARTITION BY s.business_id
            ORDER BY s.sale_date, s.sale_id
        ) AS sale_rank
    FROM runtime.sale s
),
pool_size AS (
    SELECT DISTINCT business_id, observed_customer_count
    FROM retention_customer_pool
)
SELECT
    sr.sale_id,
    sr.business_id,
    1 + MOD(sr.sale_rank - 1, ps.observed_customer_count) AS target_customer_rank
FROM sale_ranked sr
JOIN pool_size ps ON ps.business_id = sr.business_id;

UPDATE runtime.sale s
SET customer_id = cp.customer_id
FROM retention_sale_assignment a
JOIN retention_customer_pool cp
  ON cp.business_id = a.business_id
 AND cp.customer_rank = a.target_customer_rank
WHERE s.sale_id = a.sale_id
  AND s.business_id = a.business_id;

-- 3) Derive observed transaction truth using the dataset horizon rather than
-- CURRENT_DATE so the synthetic scenario remains reproducible over time.
CREATE TEMP TABLE retention_business_anchor ON COMMIT DROP AS
SELECT business_id, MAX(sale_date)::date AS data_as_of
FROM runtime.sale
GROUP BY business_id;

CREATE TEMP TABLE retention_observed_truth ON COMMIT DROP AS
SELECT
    c.business_id,
    c.customer_id,
    a.data_as_of,
    MIN(s.sale_date)::date AS observed_first_purchase_date,
    MAX(s.sale_date)::date AS observed_last_purchase_date,
    COUNT(s.sale_id)::INT AS observed_order_count,
    COALESCE(SUM(s.revenue),0)::NUMERIC(14,2) AS observed_revenue
FROM runtime.customer c
JOIN retention_business_anchor a ON a.business_id = c.business_id
LEFT JOIN runtime.sale s
  ON s.business_id = c.business_id
 AND s.customer_id = c.customer_id
GROUP BY c.business_id,c.customer_id,a.data_as_of;

CREATE INDEX ON retention_observed_truth (business_id, customer_id);

-- 4) Reconcile normal customer profile assertions from observed behavior.
-- runtime.customer in the active schema has no updated_at column, so this
-- update intentionally touches only the retention attributes that exist.
UPDATE runtime.customer c
SET
    first_purchase_date = CASE
        WHEN t.observed_order_count > 0 THEN t.observed_first_purchase_date
        ELSE c.first_purchase_date
    END,
    last_purchase_date = CASE
        WHEN t.observed_order_count > 0 THEN t.observed_last_purchase_date
        ELSE c.last_purchase_date
    END,
    repeat_count = CASE
        WHEN t.observed_order_count > 0 THEN GREATEST(t.observed_order_count - 1,0)
        ELSE 0
    END,
    churn_status = CASE
        WHEN t.observed_order_count > 0
         AND t.observed_last_purchase_date >= t.data_as_of - 90 THEN 'active'
        WHEN t.observed_order_count > 0
         AND t.observed_last_purchase_date >= t.data_as_of - 180 THEN 'dormant'
        WHEN t.observed_order_count > 0 THEN 'churned'
        WHEN MOD(ABS(HASHTEXT(c.customer_id::text)),10) < 5 THEN 'active'
        WHEN MOD(ABS(HASHTEXT(c.customer_id::text)),10) < 8 THEN 'dormant'
        ELSE 'churned'
    END
FROM retention_observed_truth t
WHERE t.business_id=c.business_id
  AND t.customer_id=c.customer_id;

-- 5) Preserve a small deterministic assertion-conflict population among
-- customers WITH observed transactions for governance/boundary testing.
UPDATE runtime.customer c
SET churn_status = CASE
    WHEN MOD(ABS(HASHTEXT(c.customer_id::text)),100) < 3
     AND t.observed_last_purchase_date >= t.data_as_of - 90 THEN 'churned'
    WHEN MOD(ABS(HASHTEXT(c.customer_id::text)),100) BETWEEN 3 AND 4
     AND t.observed_last_purchase_date < t.data_as_of - 180 THEN 'active'
    ELSE c.churn_status
END
FROM retention_observed_truth t
WHERE t.business_id=c.business_id
  AND t.customer_id=c.customer_id
  AND t.observed_order_count > 0;

-- 6) Validation. Expected with the current dataset:
-- invalid links = 0; customers_with_sales ~= 6000; profile_only ~= 4000.
SELECT COUNT(*) AS invalid_sale_customer_links
FROM runtime.sale s
LEFT JOIN runtime.customer c
  ON c.business_id=s.business_id AND c.customer_id=s.customer_id
WHERE c.customer_id IS NULL;

SELECT
    COUNT(*) AS total_customers,
    COUNT(*) FILTER (WHERE t.observed_order_count > 0) AS customers_with_sales,
    COUNT(*) FILTER (WHERE t.observed_order_count = 0) AS profile_only,
    ROUND(AVG(t.observed_order_count)::numeric,2) AS avg_orders,
    MAX(t.observed_order_count) AS max_orders
FROM retention_observed_truth t;

SELECT
    c.churn_status,
    COUNT(*) AS customers,
    COUNT(*) FILTER (WHERE t.observed_order_count > 0) AS with_observed_sales,
    COUNT(*) FILTER (WHERE t.observed_order_count = 0) AS profile_only
FROM runtime.customer c
JOIN retention_observed_truth t
  ON t.business_id=c.business_id AND t.customer_id=c.customer_id
GROUP BY c.churn_status
ORDER BY c.churn_status;

SELECT COUNT(*) AS intentional_profile_observation_conflicts
FROM runtime.customer c
JOIN retention_observed_truth t
  ON t.business_id=c.business_id AND t.customer_id=c.customer_id
WHERE t.observed_order_count > 0
  AND c.churn_status <> CASE
      WHEN t.observed_last_purchase_date >= t.data_as_of - 90 THEN 'active'
      WHEN t.observed_last_purchase_date >= t.data_as_of - 180 THEN 'dormant'
      ELSE 'churned'
  END;

COMMIT;
