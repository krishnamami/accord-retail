-- Accord Retail: Pricing Opportunity agent preparation
-- Normalizes the product-level competitor evidence contract before agent decisioning.
-- Readiness is evidence-specific; missing, stale, and low-comparability evidence remain explicit.
CREATE SCHEMA IF NOT EXISTS agent;

DROP VIEW IF EXISTS agent.pricing_opportunity_context;

CREATE OR REPLACE VIEW agent.pricing_opportunity_context AS
WITH anchor AS (
    SELECT MAX(sale_date)::date AS data_as_of
    FROM runtime.sale
),
sales AS (
    SELECT
        s.business_id,
        s.product_id,
        SUM(COALESCE(s.quantity,0)) AS units_sold,
        SUM(s.revenue)::numeric(15,2) AS revenue,
        SUM(COALESCE(s.discount_applied,0))::numeric(15,2) AS discount_amount,
        MAX(s.sale_date)::date AS sales_data_as_of
    FROM runtime.sale s
    GROUP BY s.business_id,s.product_id
),
competitor_raw AS (
    SELECT DISTINCT ON (e.business_id,e.about_id)
        e.business_id,
        e.about_id AS product_id,
        e.evidence_id,
        e.observed_at,
        e.asserted_by,
        e.source_system,
        e.payload_json
    FROM runtime.evidence e
    WHERE e.evidence_type='competitor_price_comparison'
      AND e.about_type='product'
      AND e.state='present'
    ORDER BY e.business_id,e.about_id,e.observed_at DESC,e.evidence_id DESC
),
competitor AS (
    SELECT
        cr.*,
        NULLIF(cr.payload_json->'value'->>'competitor_name','') AS competitor_name,
        NULLIF(cr.payload_json->'value'->>'currency','') AS competitor_currency,
        CASE
            WHEN cr.payload_json->'value' ? 'competitor_price'
            THEN (cr.payload_json->'value'->>'competitor_price')::numeric
            ELSE NULL
        END AS competitor_price,
        CASE
            WHEN cr.payload_json->'value' ? 'comparability_score'
            THEN (cr.payload_json->'value'->>'comparability_score')::numeric
            ELSE NULL
        END AS competitor_comparability_score,
        CASE
            WHEN cr.payload_json ? 'confidence_0_to_1'
            THEN (cr.payload_json->>'confidence_0_to_1')::numeric
            ELSE NULL
        END AS competitor_confidence,
        CASE
            WHEN cr.payload_json->'value' ? 'comparable'
            THEN (cr.payload_json->'value'->>'comparable')::boolean
            ELSE NULL
        END AS competitor_comparable
    FROM competitor_raw cr
),
base AS (
    SELECT
        p.business_id,
        b.name AS business_name,
        p.product_id,
        p.name AS product_name,
        p.category,
        p.list_price,
        p.cogs,
        s.units_sold,
        s.revenue,
        s.discount_amount,
        s.sales_data_as_of,
        a.data_as_of,
        ROUND(s.revenue/NULLIF(s.units_sold,0),2) AS realized_unit_price,
        ROUND(100.0*(p.list_price-(s.revenue/NULLIF(s.units_sold,0)))/NULLIF(p.list_price,0),2) AS list_to_realized_discount_pct,
        ROUND(100.0*((s.revenue/NULLIF(s.units_sold,0))-p.cogs)/NULLIF((s.revenue/NULLIF(s.units_sold,0)),0),2) AS realized_gross_margin_pct,
        i.quantity_on_hand,
        i.reorder_point,
        i.last_updated AS inventory_observed_at,
        c.evidence_id AS competitor_evidence_id,
        c.observed_at AS competitor_observed_at,
        c.asserted_by AS competitor_asserted_by,
        c.source_system AS competitor_source_system,
        c.competitor_name,
        c.competitor_currency,
        c.competitor_price,
        c.competitor_comparability_score,
        c.competitor_confidence,
        c.competitor_comparable,
        c.payload_json AS competitor_payload,
        ROUND(c.competitor_price-(s.revenue/NULLIF(s.units_sold,0)),2) AS competitor_price_gap_amount,
        ROUND(100.0*(c.competitor_price-(s.revenue/NULLIF(s.units_sold,0)))/NULLIF((s.revenue/NULLIF(s.units_sold,0)),0),2) AS competitor_price_gap_pct
    FROM runtime.product p
    CROSS JOIN anchor a
    JOIN runtime.business b ON b.business_id=p.business_id
    LEFT JOIN sales s ON s.business_id=p.business_id AND s.product_id=p.product_id
    LEFT JOIN runtime.inventory i ON i.business_id=p.business_id AND i.product_id=p.product_id
    LEFT JOIN competitor c ON c.business_id=p.business_id AND c.product_id=p.product_id
)
SELECT
    base.*,
    CASE
        WHEN units_sold IS NULL OR units_sold=0 OR revenue IS NULL THEN 'MISSING_OR_ZERO_SALES'
        ELSE 'READY'
    END AS sales_evidence_status,
    CASE
        WHEN list_price IS NULL OR cogs IS NULL THEN 'MISSING_PRICE_OR_COGS'
        ELSE 'READY'
    END AS margin_evidence_status,
    CASE
        WHEN inventory_observed_at IS NULL THEN 'MISSING_INVENTORY'
        WHEN inventory_observed_at::date < data_as_of-7 THEN 'STALE_INVENTORY'
        ELSE 'READY'
    END AS inventory_evidence_status,
    CASE
        WHEN competitor_evidence_id IS NULL THEN 'MISSING_COMPETITOR_EVIDENCE'
        WHEN competitor_price IS NULL THEN 'INVALID_COMPETITOR_PRICE'
        WHEN competitor_currency IS DISTINCT FROM 'USD' THEN 'UNSUPPORTED_COMPETITOR_CURRENCY'
        WHEN competitor_comparability_score IS NULL THEN 'MISSING_COMPARABILITY'
        WHEN competitor_comparability_score < 0.80 OR competitor_comparable IS NOT TRUE THEN 'LOW_COMPARABILITY'
        WHEN competitor_observed_at::date < data_as_of-7 THEN 'STALE_COMPETITOR_EVIDENCE'
        ELSE 'READY'
    END AS competitor_evidence_status,
    CASE
        WHEN units_sold IS NULL OR units_sold=0 OR revenue IS NULL OR list_price IS NULL OR cogs IS NULL
            THEN 'CANNOT_DECIDE'
        WHEN competitor_evidence_id IS NULL
            THEN 'LIMITED_NO_COMPETITOR_EVIDENCE'
        WHEN competitor_price IS NULL OR competitor_currency IS DISTINCT FROM 'USD'
            THEN 'LIMITED_INVALID_COMPETITOR_EVIDENCE'
        WHEN competitor_comparability_score IS NULL OR competitor_comparability_score < 0.80 OR competitor_comparable IS NOT TRUE
            THEN 'LIMITED_LOW_COMPARABILITY'
        WHEN competitor_observed_at::date < data_as_of-7
            THEN 'LIMITED_STALE_COMPETITOR_EVIDENCE'
        WHEN inventory_observed_at IS NULL OR inventory_observed_at::date < data_as_of-7
            THEN 'LIMITED_INVENTORY_EVIDENCE'
        ELSE 'READY'
    END AS recommendation_readiness
FROM base;
