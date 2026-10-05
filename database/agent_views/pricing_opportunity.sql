-- Accord Retail: Pricing Opportunity agent preparation
CREATE SCHEMA IF NOT EXISTS agent;

CREATE OR REPLACE VIEW agent.pricing_opportunity_context AS
WITH sales AS (
 SELECT s.business_id,s.product_id,
        SUM(COALESCE(s.quantity,0)) AS units_sold,
        SUM(s.revenue)::numeric(15,2) AS revenue,
        SUM(COALESCE(s.discount_applied,0))::numeric(15,2) AS discount_amount,
        MAX(s.sale_date) AS data_as_of
 FROM runtime.sale s GROUP BY s.business_id,s.product_id
), competitor AS (
 SELECT DISTINCT ON (e.business_id,e.about_id)
        e.business_id,e.about_id AS product_id,e.evidence_id,e.observed_at,e.payload_json
 FROM runtime.evidence e
 WHERE e.evidence_type='competitor_price_comparison' AND e.state='present'
 ORDER BY e.business_id,e.about_id,e.observed_at DESC
)
SELECT p.business_id,b.name AS business_name,p.product_id,p.name AS product_name,p.category,p.list_price,p.cogs,
       s.units_sold,s.revenue,s.discount_amount,s.data_as_of,
       ROUND(s.revenue/NULLIF(s.units_sold,0),2) AS realized_unit_price,
       ROUND(100.0*(p.list_price-(s.revenue/NULLIF(s.units_sold,0)))/NULLIF(p.list_price,0),2) AS list_to_realized_discount_pct,
       ROUND(100.0*((s.revenue/NULLIF(s.units_sold,0))-p.cogs)/NULLIF((s.revenue/NULLIF(s.units_sold,0)),0),2) AS realized_gross_margin_pct,
       i.quantity_on_hand,i.reorder_point,
       c.evidence_id AS competitor_evidence_id,c.observed_at AS competitor_observed_at,c.payload_json AS competitor_payload,
       CASE WHEN s.units_sold IS NULL OR s.units_sold=0 OR p.cogs IS NULL THEN 'CANNOT_DECIDE'
            ELSE 'READY' END AS data_quality_status
FROM runtime.product p
JOIN runtime.business b ON b.business_id=p.business_id
LEFT JOIN sales s ON s.business_id=p.business_id AND s.product_id=p.product_id
LEFT JOIN runtime.inventory i ON i.business_id=p.business_id AND i.product_id=p.product_id
LEFT JOIN competitor c ON c.business_id=p.business_id AND c.product_id=p.product_id;

-- Competitor price gap is intentionally not parsed here until the evidence payload contract
-- is fixed in the KB. This prevents guessing a JSON key and keeps missing evidence explicit.
