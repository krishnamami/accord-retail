-- Accord Retail: deterministic economic normalization
-- Run after 06_prepare_customer_retention_data.sql and before 07_prepare_pricing_opportunity_data.sql.
-- Preserves sale dates, customers, products, channels, and quantities.
-- Normalizes product unit economics and recomputes sale revenue/discount consistently.
--
-- Scenario coverage is deterministic, not intended to represent production prevalence.
-- Product target gross margin on list price:
--   ~10% low-margin: 12%-19%
--   ~20% moderate:   22%-29%
--   ~70% healthy:    32%-49%
-- Transaction discounts:
--   ~15% heavy:      15%-24%
--   remaining:        0%-12%

BEGIN;

-- 1) Normalize product economics. Existing list_price is retained.
-- cogs is derived from list_price so list price always exceeds cost.
UPDATE runtime.product p
SET cogs = ROUND(
    p.list_price * (
        1 - CASE
            WHEN MOD(ABS(HASHTEXT(p.product_id::text)),100) < 10
                THEN (12 + MOD(ABS(HASHTEXT(p.product_id::text || ':margin')),8))::numeric / 100.0
            WHEN MOD(ABS(HASHTEXT(p.product_id::text)),100) < 30
                THEN (22 + MOD(ABS(HASHTEXT(p.product_id::text || ':margin')),8))::numeric / 100.0
            ELSE (32 + MOD(ABS(HASHTEXT(p.product_id::text || ':margin')),18))::numeric / 100.0
        END
    ), 2
)
WHERE p.list_price IS NOT NULL
  AND p.list_price > 0;

-- Keep legacy cost_per_unit aligned when that column exists in this model.
UPDATE runtime.product
SET cost_per_unit = cogs
WHERE cogs IS NOT NULL;

-- 2) Build a deterministic sale-level discount rate.
CREATE TEMP TABLE normalized_sale_price ON COMMIT DROP AS
SELECT
    s.business_id,
    s.sale_id,
    s.product_id,
    s.quantity,
    p.list_price,
    CASE
        WHEN MOD(ABS(HASHTEXT(s.sale_id::text || ':discount-class')),100) < 15
            THEN (15 + MOD(ABS(HASHTEXT(s.sale_id::text || ':discount')),10))::numeric / 100.0
        ELSE MOD(ABS(HASHTEXT(s.sale_id::text || ':discount')),13)::numeric / 100.0
    END AS discount_rate
FROM runtime.sale s
JOIN runtime.product p
  ON p.business_id=s.business_id
 AND p.product_id=s.product_id
WHERE p.list_price IS NOT NULL
  AND p.list_price > 0
  AND s.quantity IS NOT NULL
  AND s.quantity > 0;

-- 3) Make revenue, discount, quantity, and list price mathematically coherent.
-- discount_applied is a dollar amount because Margin Health sums it as dollars.
UPDATE runtime.sale s
SET revenue = ROUND(n.quantity * n.list_price * (1-n.discount_rate),2),
    discount_applied = ROUND(n.quantity * n.list_price * n.discount_rate,2)
FROM normalized_sale_price n
WHERE n.business_id=s.business_id
  AND n.sale_id=s.sale_id;

-- 4) Validation.
SELECT
    COUNT(*) AS products,
    COUNT(*) FILTER (WHERE cogs >= list_price) AS invalid_cogs_gte_list,
    ROUND(MIN(100.0*(list_price-cogs)/NULLIF(list_price,0)),2) AS min_list_margin_pct,
    ROUND(AVG(100.0*(list_price-cogs)/NULLIF(list_price,0)),2) AS avg_list_margin_pct,
    ROUND(MAX(100.0*(list_price-cogs)/NULLIF(list_price,0)),2) AS max_list_margin_pct
FROM runtime.product
WHERE list_price IS NOT NULL;

SELECT
    COUNT(*) AS sales,
    COUNT(*) FILTER (WHERE revenue <= 0) AS nonpositive_revenue,
    ROUND(MIN(revenue/NULLIF(quantity,0)),2) AS min_realized_unit_price,
    ROUND(AVG(revenue/NULLIF(quantity,0)),2) AS avg_realized_unit_price,
    ROUND(MAX(revenue/NULLIF(quantity,0)),2) AS max_realized_unit_price,
    ROUND(AVG(100.0*discount_applied/NULLIF(revenue+discount_applied,0)),2) AS avg_discount_pct
FROM runtime.sale;

SELECT
    COUNT(*) AS economically_invalid_sales
FROM runtime.sale s
JOIN runtime.product p
  ON p.business_id=s.business_id AND p.product_id=s.product_id
WHERE s.quantity IS NULL OR s.quantity<=0
   OR s.revenue IS NULL OR s.revenue<=0
   OR (s.revenue/NULLIF(s.quantity,0)) > p.list_price + 0.01;

COMMIT;
