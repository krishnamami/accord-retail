-- Accord Retail: Pricing Opportunity competitor evidence preparation
-- Synthetic/demo evidence only. Does not alter sales, products, inventory, or financial facts.
-- Creates deterministic product-level competitor evidence populations:
--   60% fresh + comparable
--   10% stale + comparable
--   10% fresh + low comparability
--   20% no product-level competitor evidence

BEGIN;

-- Idempotent: replace only the synthetic product-level fixtures created here.
DELETE FROM runtime.evidence
WHERE evidence_type = 'competitor_price_comparison'
  AND about_type = 'product'
  AND source_system = 'synthetic_competitor_feed';

WITH ranked AS (
    SELECT
        p.business_id,
        p.product_id,
        p.list_price,
        ROW_NUMBER() OVER (
            PARTITION BY p.business_id ORDER BY p.product_id
        ) AS product_rank,
        COUNT(*) OVER (PARTITION BY p.business_id) AS product_count
    FROM runtime.product p
),
fixture AS (
    SELECT
        r.*,
        CASE
            WHEN product_rank <= FLOOR(product_count * 0.60) THEN 'FRESH_COMPARABLE'
            WHEN product_rank <= FLOOR(product_count * 0.70) THEN 'STALE_COMPARABLE'
            WHEN product_rank <= FLOOR(product_count * 0.80) THEN 'LOW_COMPARABILITY'
            ELSE 'MISSING'
        END AS fixture_class,
        -- Deterministic competitor gap from approximately -15% to +15%.
        ((MOD(ABS(HASHTEXT(product_id::text)), 31) - 15)::numeric / 100.0) AS competitor_delta_pct
    FROM ranked r
),
prepared AS (
    SELECT
        business_id,
        product_id,
        list_price,
        fixture_class,
        competitor_delta_pct,
        ROUND(list_price * (1 + competitor_delta_pct), 2) AS competitor_price,
        CASE fixture_class
            WHEN 'FRESH_COMPARABLE' THEN 0.90
            WHEN 'STALE_COMPARABLE' THEN 0.92
            WHEN 'LOW_COMPARABILITY' THEN 0.45
        END::numeric AS comparability_score,
        CASE fixture_class
            WHEN 'FRESH_COMPARABLE' THEN 0.95
            WHEN 'STALE_COMPARABLE' THEN 0.90
            WHEN 'LOW_COMPARABILITY' THEN 0.70
        END::numeric AS confidence_score,
        CASE fixture_class
            WHEN 'STALE_COMPARABLE' THEN TIMESTAMP '2026-06-01 12:00:00'
            ELSE TIMESTAMP '2026-09-11 12:00:00'
        END AS observed_at
    FROM fixture
    WHERE fixture_class <> 'MISSING'
)
INSERT INTO runtime.evidence (
    evidence_id,
    business_id,
    evidence_type,
    about_type,
    about_id,
    asserted_by,
    source_system,
    state,
    observed_at,
    created_at,
    payload_json,
    traced_from_upload_id
)
SELECT
    gen_random_uuid(),
    business_id,
    'competitor_price_comparison',
    'product',
    product_id,
    'synthetic_feed',
    'synthetic_competitor_feed',
    'present',
    observed_at,
    CURRENT_TIMESTAMP,
    jsonb_build_object(
        'unit', 'USD_and_percentage',
        'value', jsonb_build_object(
            'competitor_name', 'Synthetic Competitor',
            'competitor_price', competitor_price,
            'currency', 'USD',
            'comparable', comparability_score >= 0.80,
            'comparability_score', comparability_score,
            'our_list_price', list_price,
            'competitor_delta_vs_list_pct', ROUND(competitor_delta_pct * 100, 2)
        ),
        'inputs', jsonb_build_object(
            'our_list_price', list_price,
            'fixture_class', fixture_class
        ),
        'formula', 'competitor_price = list_price * (1 + deterministic_competitor_delta_pct)',
        'source_record_id', product_id::text,
        'confidence_0_to_1', confidence_score
    ),
    NULL
FROM prepared;

-- Validation: product-level fixture coverage.
SELECT
    COUNT(*) AS total_products,
    COUNT(e.evidence_id) AS products_with_competitor_evidence,
    COUNT(*) - COUNT(e.evidence_id) AS products_without_competitor_evidence,
    COUNT(*) FILTER (
        WHERE e.evidence_id IS NOT NULL
          AND (e.payload_json->'value'->>'comparability_score')::numeric >= 0.80
          AND e.observed_at >= TIMESTAMP '2026-09-01 00:00:00'
    ) AS fresh_comparable,
    COUNT(*) FILTER (
        WHERE e.evidence_id IS NOT NULL
          AND (e.payload_json->'value'->>'comparability_score')::numeric >= 0.80
          AND e.observed_at < TIMESTAMP '2026-09-01 00:00:00'
    ) AS stale_comparable,
    COUNT(*) FILTER (
        WHERE e.evidence_id IS NOT NULL
          AND (e.payload_json->'value'->>'comparability_score')::numeric < 0.80
    ) AS low_comparability
FROM runtime.product p
LEFT JOIN runtime.evidence e
  ON e.business_id = p.business_id
 AND e.about_type = 'product'
 AND e.about_id = p.product_id
 AND e.evidence_type = 'competitor_price_comparison'
 AND e.source_system = 'synthetic_competitor_feed';

COMMIT;
