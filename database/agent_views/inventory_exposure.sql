-- Accord Retail: Inventory Exposure agent preparation
CREATE SCHEMA IF NOT EXISTS agent;

CREATE OR REPLACE VIEW agent.inventory_exposure_context AS
WITH velocity AS (
 SELECT s.business_id,s.product_id,
        MAX(s.sale_date) AS latest_sale_date,
        SUM(COALESCE(s.quantity,0)) FILTER (WHERE s.sale_date >= CURRENT_DATE-INTERVAL '90 days') AS units_90d,
        SUM(COALESCE(s.quantity,0)) FILTER (WHERE s.sale_date >= CURRENT_DATE-INTERVAL '30 days') AS units_30d
 FROM runtime.sale s GROUP BY s.business_id,s.product_id
)
SELECT i.business_id,b.name AS business_name,i.product_id,p.name AS product_name,p.category,
       i.quantity_on_hand,i.reorder_point,i.last_updated,p.cogs,p.list_price,
       ROUND(i.quantity_on_hand*COALESCE(p.cogs,0),2) AS inventory_value,
       v.units_30d,v.units_90d,
       ROUND(v.units_90d/90.0,4) AS daily_sales_velocity_90d,
       ROUND(i.quantity_on_hand/NULLIF(v.units_90d/90.0,0),2) AS days_of_supply,
       (i.quantity_on_hand-i.reorder_point) AS reorder_gap_units,
       CASE WHEN i.quantity_on_hand<=i.reorder_point THEN TRUE ELSE FALSE END AS at_or_below_reorder,
       CASE WHEN v.units_90d=0 AND i.quantity_on_hand>0 THEN TRUE ELSE FALSE END AS slow_moving_candidate,
       CASE WHEN i.last_updated < CURRENT_TIMESTAMP-INTERVAL '7 days' THEN 'STALE_INVENTORY'
            WHEN v.units_90d IS NULL THEN 'INSUFFICIENT_HISTORY' ELSE 'READY' END AS data_quality_status
FROM runtime.inventory i
JOIN runtime.product p ON p.product_id=i.product_id
JOIN runtime.business b ON b.business_id=i.business_id
LEFT JOIN velocity v ON v.business_id=i.business_id AND v.product_id=i.product_id;
