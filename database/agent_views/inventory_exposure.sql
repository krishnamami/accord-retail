-- Accord Retail: Inventory Exposure agent preparation
-- Freshness is evaluated against the business data horizon, not wall-clock CURRENT_DATE.
CREATE SCHEMA IF NOT EXISTS agent;

CREATE OR REPLACE VIEW agent.inventory_exposure_context AS
WITH anchor AS (
 SELECT business_id,MAX(sale_date)::date AS data_as_of FROM runtime.sale GROUP BY business_id
), velocity AS (
 SELECT s.business_id,s.product_id,a.data_as_of,
        MAX(s.sale_date)::date AS latest_sale_date,
        SUM(COALESCE(s.quantity,0)) FILTER (WHERE s.sale_date::date > a.data_as_of-90 AND s.sale_date::date <= a.data_as_of) AS units_90d,
        SUM(COALESCE(s.quantity,0)) FILTER (WHERE s.sale_date::date > a.data_as_of-30 AND s.sale_date::date <= a.data_as_of) AS units_30d
 FROM runtime.sale s JOIN anchor a ON a.business_id=s.business_id
 GROUP BY s.business_id,s.product_id,a.data_as_of
)
SELECT i.business_id,b.name AS business_name,i.product_id,p.name AS product_name,p.category,
       i.quantity_on_hand,i.reorder_point,i.last_updated,p.cogs,p.list_price,v.data_as_of,
       ROUND(i.quantity_on_hand*COALESCE(p.cogs,0),2) AS inventory_value,
       v.units_30d,v.units_90d,
       ROUND(v.units_90d/90.0,4) AS daily_sales_velocity_90d,
       ROUND(i.quantity_on_hand/NULLIF(v.units_90d/90.0,0),2) AS days_of_supply,
       (i.quantity_on_hand-i.reorder_point) AS reorder_gap_units,
       CASE WHEN i.quantity_on_hand<=i.reorder_point THEN TRUE ELSE FALSE END AS at_or_below_reorder,
       CASE WHEN v.units_90d=0 AND i.quantity_on_hand>0 THEN TRUE ELSE FALSE END AS slow_moving_candidate,
       CASE WHEN i.last_updated IS NULL THEN 'MISSING_INVENTORY_TIMESTAMP'
            WHEN i.last_updated::date < v.data_as_of-7 THEN 'STALE_INVENTORY'
            WHEN v.units_90d IS NULL THEN 'INSUFFICIENT_HISTORY'
            ELSE 'READY' END AS inventory_evidence_status
FROM runtime.inventory i
JOIN runtime.product p ON p.product_id=i.product_id AND p.business_id=i.business_id
JOIN runtime.business b ON b.business_id=i.business_id
LEFT JOIN velocity v ON v.business_id=i.business_id AND v.product_id=i.product_id;
