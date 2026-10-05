-- Prepare customer-retention test data without changing revenue, margin, or inventory facts.
--
-- Purpose
--   1. Reassign existing sales to existing customer cohorts within the SAME business.
--   2. Produce a realistic mix of customers with observed transactions and profile-only customers.
--   3. Reconcile most customer profile attributes from transaction truth.
--   4. Preserve a small deterministic set of profile-vs-observed conflicts for governance tests.
--
-- IMPORTANT
--   * This script does NOT insert/delete sales and does NOT change sale revenue, quantity,
--     product, channel, or sale_date. Existing revenue/margin/inventory scenarios remain intact.
--   * runtime.customer and runtime.sale are assumed to match the modular runtime schema.
--   * Re-running the script is deterministic for the same customer/sale population.

BEGIN;

-- -----------------------------------------------------------------------------
-- 1. Build deterministic customer ranks inside each business.
--    Roughly 60% of customers are eligible for transaction assignment. With the
--    current 1,000-customer / 2,000-sale shape this creates meaningful repeat
--    behavior while leaving profile-only cohorts for boundary-condition testing.
-- -----------------------------------------------------------------------------
CREATE TEMP TABLE retention_customer_pool ON COMMIT DROP AS
WITH ranked AS (
    SELECT
        c.business_id,
        c.customer_id,
        ROW_NUMBER() OVER (
            PARTITION BY c.business_id
            ORDER BY c.customer_id
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

-- -----------------------------------------------------------------------------
-- 2. Reassign EXISTING sales only. No financial facts are modified.
--
--    Distribution is intentionally skewed:
--      - ~70% of sales go to the first ~35% of observed customers (repeat buyers)
--      - ~30% go to the remaining observed customers (lower-frequency buyers)
--
--    This gives retention logic a better mix than a simple one-sale-per-customer
--    round-robin while remaining fully deterministic.
-- -----------------------------------------------------------------------------
WITH sale_ranked AS (
    SELECT
        s.sale_id,
        s.business_id,
        ROW_NUMBER() OVER (
            PARTITION BY s.business_id
            ORDER BY s.sale_date, s.sale_id
        ) AS sale_rank,
        COUNT(*) OVER (PARTITION BY s.business_id) AS sale_count
    FROM runtime.sale s
),
assignment AS (
    SELECT
        sr.sale_id,
        sr.business_id,
        CASE
            WHEN sr.sale_rank <= CEIL(sr.sale_count * 0.70)::INT THEN
                1 + MOD(
                    sr.sale_rank - 1,
                    GREATEST(
                        1,
                        FLOOR(cp.observed_customer_count * 0.35)::INT
                    )
                )
            ELSE
                GREATEST(1, FLOOR(cp.observed_customer_count * 0.35)::INT) +
                1 + MOD(
                    sr.sale_rank - CEIL(sr.sale_count * 0.70)::INT - 1,
                    GREATEST(
                        1,
                        cp.observed_customer_count -
                        GREATEST(1, FLOOR(cp.observed_customer_count * 0.35)::INT)
                    )
                )
        END AS target_customer_rank
    FROM sale_ranked sr
    JOIN (
        SELECT DISTINCT business_id, observed_customer_count
        FROM retention_customer_pool
    ) cp
      ON cp.business_id = sr.business_id
)
UPDATE runtime.sale s
SET customer_id = cp.customer_id
FROM assignment a
JOIN retention_customer_pool cp
  ON cp.business_id = a.business_id
 AND cp.customer_rank = a.target_customer_rank
WHERE s.sale_id = a.sale_id;

-- -----------------------------------------------------------------------------
-- 3. Derive observed transaction truth per customer.
-- -----------------------------------------------------------------------------
CREATE TEMP TABLE retention_observed_truth ON COMMIT DROP AS
SELECT
    c.business_id,
    c.customer_id,
    MIN(s.sale_date) AS observed_first_purchase_date,
    MAX(s.sale_date) AS observed_last_purchase_date,
    COUNT(s.sale_id)::INT AS observed_order_count,
    COALESCE(SUM(s.revenue), 0)::NUMERIC(14,2) AS observed_revenue
FROM runtime.customer c
LEFT JOIN runtime.sale s
  ON s.business_id = c.business_id
 AND s.customer_id = c.customer_id
GROUP BY c.business_id, c.customer_id;

CREATE INDEX ON retention_observed_truth (business_id, customer_id);

-- -----------------------------------------------------------------------------
-- 4. Reconcile customer assertions for the normal population.
--
--    repeat_count is interpreted as repeat purchases AFTER the first purchase.
--    Churn thresholds for test data:
--      active  : last observed purchase <= 90 days ago
--      dormant : 91-180 days ago
--      churned : > 180 days ago
--      profile-only customers retain a deterministic mix of assertions so the
--               agent can exercise missing-evidence / cannot-decide boundaries.
-- -----------------------------------------------------------------------------
UPDATE runtime.customer c
SET
    first_purchase_date = COALESCE(t.observed_first_purchase_date, c.first_purchase_date),
    last_purchase_date  = COALESCE(t.observed_last_purchase_date, c.last_purchase_date),
    repeat_count = CASE
        WHEN t.observed_order_count > 0 THEN GREATEST(t.observed_order_count - 1, 0)
        ELSE 0
    END,
    churn_status = CASE
        WHEN t.observed_order_count > 0 AND t.observed_last_purchase_date >= CURRENT_DATE - 90
            THEN 'active'
        WHEN t.observed_order_count > 0 AND t.observed_last_purchase_date >= CURRENT_DATE - 180
            THEN 'dormant'
        WHEN t.observed_order_count > 0
            THEN 'churned'
        -- No observed transaction evidence: keep a deterministic assertion mix.
        WHEN MOD(ABS(HASHTEXT(c.customer_id::TEXT)), 10) < 5 THEN 'active'
        WHEN MOD(ABS(HASHTEXT(c.customer_id::TEXT)), 10) < 8 THEN 'dormant'
        ELSE 'churned'
    END,
    updated_at = CURRENT_TIMESTAMP
FROM retention_observed_truth t
WHERE t.business_id = c.business_id
  AND t.customer_id = c.customer_id;

-- -----------------------------------------------------------------------------
-- 5. Introduce a SMALL deterministic conflict population among customers that
--    have observed sales. These are deliberate governance fixtures, not bad data
--    accidentally produced by the generator.
--
--    ~3%: profile says churned although recent observed activity says active.
--    ~2%: profile says active although old observed activity says churned/dormant.
-- -----------------------------------------------------------------------------
UPDATE runtime.customer c
SET
    churn_status = CASE
        WHEN MOD(ABS(HASHTEXT(c.customer_id::TEXT)), 100) < 3
             AND t.observed_last_purchase_date >= CURRENT_DATE - 90
            THEN 'churned'
        WHEN MOD(ABS(HASHTEXT(c.customer_id::TEXT)), 100) BETWEEN 3 AND 4
             AND t.observed_last_purchase_date < CURRENT_DATE - 180
            THEN 'active'
        ELSE c.churn_status
    END,
    updated_at = CURRENT_TIMESTAMP
FROM retention_observed_truth t
WHERE t.business_id = c.business_id
  AND t.customer_id = c.customer_id
  AND t.observed_order_count > 0;

-- -----------------------------------------------------------------------------
-- 6. Validation output. These queries are intentionally part of the script so a
--    developer can immediately verify the retention population after execution.
-- -----------------------------------------------------------------------------

-- A. Every sale must reference a customer in the same business.
SELECT
    COUNT(*) AS invalid_sale_customer_links
FROM runtime.sale s
LEFT JOIN runtime.customer c
  ON c.customer_id = s.customer_id
 AND c.business_id = s.business_id
WHERE s.customer_id IS NULL
   OR c.customer_id IS NULL;

-- Expected: 0

-- B. Population shape by business.
SELECT
    c.business_id,
    COUNT(*) AS total_customers,
    COUNT(*) FILTER (WHERE t.observed_order_count > 0) AS customers_with_sales,
    COUNT(*) FILTER (WHERE t.observed_order_count = 0) AS profile_only_customers,
    ROUND(AVG(t.observed_order_count)::NUMERIC, 2) AS avg_orders_per_customer,
    MAX(t.observed_order_count) AS max_orders_per_customer
FROM runtime.customer c
JOIN retention_observed_truth t
  ON t.business_id = c.business_id
 AND t.customer_id = c.customer_id
GROUP BY c.business_id
ORDER BY c.business_id;

-- C. Retention assertion distribution.
SELECT
    business_id,
    churn_status,
    COUNT(*) AS customer_count
FROM runtime.customer
GROUP BY business_id, churn_status
ORDER BY business_id, churn_status;

-- D. Explicit profile-vs-observed conflicts for governance testing.
SELECT
    c.business_id,
    c.customer_id,
    c.churn_status AS asserted_churn_status,
    t.observed_last_purchase_date,
    t.observed_order_count,
    CASE
        WHEN t.observed_last_purchase_date >= CURRENT_DATE - 90 THEN 'active'
        WHEN t.observed_last_purchase_date >= CURRENT_DATE - 180 THEN 'dormant'
        ELSE 'churned'
    END AS observed_churn_status
FROM runtime.customer c
JOIN retention_observed_truth t
  ON t.business_id = c.business_id
 AND t.customer_id = c.customer_id
WHERE t.observed_order_count > 0
  AND c.churn_status <> CASE
        WHEN t.observed_last_purchase_date >= CURRENT_DATE - 90 THEN 'active'
        WHEN t.observed_last_purchase_date >= CURRENT_DATE - 180 THEN 'dormant'
        ELSE 'churned'
      END
ORDER BY c.business_id, c.customer_id;

COMMIT;
