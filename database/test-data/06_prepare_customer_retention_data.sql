-- Accord Retail: deterministic customer-retention data preparation
-- Creates behavioral cohorts while preserving all financial facts.
-- Changes only runtime.sale.customer_id and customer retention profile attributes.
-- Does NOT alter sale revenue, quantity, product, channel, discount, or sale_date.

BEGIN;

-- 1) Rank customers within each business. First 60% become the observed
-- population; remaining 40% stay profile-only for CANNOT_DECIDE coverage.
CREATE TEMP TABLE retention_customer_pool ON COMMIT DROP AS
WITH ranked AS (
    SELECT c.business_id,c.customer_id,
           ROW_NUMBER() OVER (PARTITION BY c.business_id ORDER BY c.customer_id) AS customer_rank,
           COUNT(*) OVER (PARTITION BY c.business_id) AS customer_count
    FROM runtime.customer c
)
SELECT business_id,customer_id,customer_rank,customer_count,
       GREATEST(1,FLOOR(customer_count*0.60)::int) AS observed_customer_count
FROM ranked;
CREATE INDEX ON retention_customer_pool(business_id,customer_rank);

-- 2) Anchor each business to its own maximum transaction date.
CREATE TEMP TABLE retention_business_anchor ON COMMIT DROP AS
SELECT business_id,MAX(sale_date)::date AS data_as_of
FROM runtime.sale GROUP BY business_id;

-- 3) Give each observed customer a deterministic behavioral cohort.
-- The target percentages are scenario coverage, not production prevalence:
--   ACTIVE 45%, WATCH 20%, DORMANT 20%, CHURN 15%.
-- Cohort windows match the governed Customer Retention rules exactly.
CREATE TEMP TABLE retention_customer_cohort ON COMMIT DROP AS
SELECT p.*,
       CASE
         WHEN p.customer_rank <= FLOOR(p.observed_customer_count*0.45) THEN 'ACTIVE'
         WHEN p.customer_rank <= FLOOR(p.observed_customer_count*0.65) THEN 'WATCH'
         WHEN p.customer_rank <= FLOOR(p.observed_customer_count*0.85) THEN 'DORMANT'
         WHEN p.customer_rank <= p.observed_customer_count THEN 'CHURN'
         ELSE 'PROFILE_ONLY'
       END AS behavioral_cohort
FROM retention_customer_pool p;
CREATE INDEX ON retention_customer_cohort(business_id,behavioral_cohort,customer_rank);

-- 4) Rank existing sales into matching temporal windows. We do NOT change
-- sale_date. Instead, old sales are assigned to CHURN customers, mid-age sales
-- to DORMANT/WATCH customers, and recent sales to ACTIVE customers.
CREATE TEMP TABLE retention_sales_classified ON COMMIT DROP AS
SELECT s.sale_id,s.business_id,s.sale_date::date AS sale_date,a.data_as_of,
       CASE
         WHEN s.sale_date::date >= a.data_as_of-60 THEN 'ACTIVE'
         WHEN s.sale_date::date >= a.data_as_of-90 THEN 'WATCH'
         WHEN s.sale_date::date >= a.data_as_of-180 THEN 'DORMANT'
         ELSE 'CHURN'
       END AS sale_cohort,
       ROW_NUMBER() OVER (
         PARTITION BY s.business_id,
           CASE
             WHEN s.sale_date::date >= a.data_as_of-60 THEN 'ACTIVE'
             WHEN s.sale_date::date >= a.data_as_of-90 THEN 'WATCH'
             WHEN s.sale_date::date >= a.data_as_of-180 THEN 'DORMANT'
             ELSE 'CHURN'
           END
         ORDER BY s.sale_date,s.sale_id
       ) AS cohort_sale_rank
FROM runtime.sale s
JOIN retention_business_anchor a ON a.business_id=s.business_id;

-- 5) Assign each sale only to a customer in the SAME business and SAME temporal
-- cohort. This guarantees that a CHURN customer's last observed transaction is
-- >180 days old, while ACTIVE/WATCH/DORMANT remain in their governed windows.
CREATE TEMP TABLE retention_cohort_sizes ON COMMIT DROP AS
SELECT business_id,behavioral_cohort,COUNT(*)::int AS cohort_customer_count
FROM retention_customer_cohort
WHERE behavioral_cohort<>'PROFILE_ONLY'
GROUP BY business_id,behavioral_cohort;

CREATE TEMP TABLE retention_assignment ON COMMIT DROP AS
SELECT sc.sale_id,sc.business_id,sc.sale_cohort,
       1+MOD(sc.cohort_sale_rank-1,cs.cohort_customer_count) AS cohort_target_rank
FROM retention_sales_classified sc
JOIN retention_cohort_sizes cs
  ON cs.business_id=sc.business_id AND cs.behavioral_cohort=sc.sale_cohort;

WITH cohort_customers AS (
  SELECT business_id,customer_id,behavioral_cohort,
         ROW_NUMBER() OVER(PARTITION BY business_id,behavioral_cohort ORDER BY customer_rank) AS cohort_rank
  FROM retention_customer_cohort
  WHERE behavioral_cohort<>'PROFILE_ONLY'
)
UPDATE runtime.sale s
SET customer_id=cc.customer_id
FROM retention_assignment a
JOIN cohort_customers cc
  ON cc.business_id=a.business_id
 AND cc.behavioral_cohort=a.sale_cohort
 AND cc.cohort_rank=a.cohort_target_rank
WHERE s.sale_id=a.sale_id AND s.business_id=a.business_id;

-- 6) Derive observed truth after reassignment.
CREATE TEMP TABLE retention_observed_truth ON COMMIT DROP AS
SELECT c.business_id,c.customer_id,a.data_as_of,
       MIN(s.sale_date)::date AS observed_first_purchase_date,
       MAX(s.sale_date)::date AS observed_last_purchase_date,
       COUNT(s.sale_id)::int AS observed_order_count,
       CASE WHEN COUNT(s.sale_id)=0 THEN NULL ELSE SUM(s.revenue)::numeric(14,2) END AS observed_revenue
FROM runtime.customer c
JOIN retention_business_anchor a ON a.business_id=c.business_id
LEFT JOIN runtime.sale s ON s.business_id=c.business_id AND s.customer_id=c.customer_id
GROUP BY c.business_id,c.customer_id,a.data_as_of;
CREATE INDEX ON retention_observed_truth(business_id,customer_id);

-- 7) Reconcile normal profile assertions from transaction truth.
UPDATE runtime.customer c
SET first_purchase_date=CASE WHEN t.observed_order_count>0 THEN t.observed_first_purchase_date ELSE c.first_purchase_date END,
    last_purchase_date=CASE WHEN t.observed_order_count>0 THEN t.observed_last_purchase_date ELSE c.last_purchase_date END,
    repeat_count=CASE WHEN t.observed_order_count>0 THEN GREATEST(t.observed_order_count-1,0) ELSE 0 END,
    churn_status=CASE
      WHEN t.observed_order_count>0 AND t.observed_last_purchase_date>=t.data_as_of-90 THEN 'active'
      WHEN t.observed_order_count>0 AND t.observed_last_purchase_date>=t.data_as_of-180 THEN 'dormant'
      WHEN t.observed_order_count>0 THEN 'churned'
      WHEN MOD(ABS(HASHTEXT(c.customer_id::text)),10)<5 THEN 'active'
      WHEN MOD(ABS(HASHTEXT(c.customer_id::text)),10)<8 THEN 'dormant'
      ELSE 'churned'
    END
FROM retention_observed_truth t
WHERE t.business_id=c.business_id AND t.customer_id=c.customer_id;

-- 8) Preserve a small deterministic assertion-conflict population among
-- customers with observed evidence. These are governance fixtures.
UPDATE runtime.customer c
SET churn_status=CASE
  WHEN MOD(ABS(HASHTEXT(c.customer_id::text)),100)<3
   AND t.observed_last_purchase_date>=t.data_as_of-90 THEN 'churned'
  WHEN MOD(ABS(HASHTEXT(c.customer_id::text)),100) BETWEEN 3 AND 4
   AND t.observed_last_purchase_date<t.data_as_of-180 THEN 'active'
  ELSE c.churn_status END
FROM retention_observed_truth t
WHERE t.business_id=c.business_id AND t.customer_id=c.customer_id
  AND t.observed_order_count>0;

-- 9) Validation.
SELECT COUNT(*) AS invalid_sale_customer_links
FROM runtime.sale s LEFT JOIN runtime.customer c
 ON c.business_id=s.business_id AND c.customer_id=s.customer_id
WHERE c.customer_id IS NULL;

SELECT COUNT(*) AS total_customers,
       COUNT(*) FILTER(WHERE observed_order_count>0) AS customers_with_sales,
       COUNT(*) FILTER(WHERE observed_order_count=0) AS profile_only,
       ROUND(AVG(observed_order_count)::numeric,2) AS avg_orders,
       MAX(observed_order_count) AS max_orders
FROM retention_observed_truth;

SELECT
  CASE
    WHEN observed_order_count=0 THEN 'PROFILE_ONLY'
    WHEN observed_last_purchase_date>=data_as_of-60 THEN 'ACTIVE'
    WHEN observed_last_purchase_date>=data_as_of-90 THEN 'WATCH'
    WHEN observed_last_purchase_date>=data_as_of-180 THEN 'DORMANT'
    ELSE 'CHURN'
  END AS observed_cohort,
  COUNT(*) AS customers,
  MIN(CASE WHEN observed_order_count>0 THEN data_as_of-observed_last_purchase_date END) AS min_recency_days,
  MAX(CASE WHEN observed_order_count>0 THEN data_as_of-observed_last_purchase_date END) AS max_recency_days
FROM retention_observed_truth
GROUP BY 1 ORDER BY 1;

SELECT COUNT(*) AS intentional_profile_observation_conflicts
FROM runtime.customer c JOIN retention_observed_truth t
 ON t.business_id=c.business_id AND t.customer_id=c.customer_id
WHERE t.observed_order_count>0
 AND c.churn_status<>CASE
   WHEN t.observed_last_purchase_date>=t.data_as_of-90 THEN 'active'
   WHEN t.observed_last_purchase_date>=t.data_as_of-180 THEN 'dormant'
   ELSE 'churned' END;

COMMIT;
