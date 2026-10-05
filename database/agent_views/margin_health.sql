-- Accord Retail: Margin Health agent preparation
CREATE SCHEMA IF NOT EXISTS agent;

CREATE OR REPLACE VIEW agent.margin_health_context AS
WITH product_period AS (
  SELECT p.business_id,p.product_id,p.name AS product_name,p.category,p.cogs,p.list_price,
         date_trunc('month',s.sale_date)::date AS period_start,
         SUM(COALESCE(s.quantity,0)) AS units_sold,
         SUM(s.revenue)::numeric(15,2) AS revenue,
         SUM(COALESCE(s.quantity,0)*COALESCE(p.cogs,0))::numeric(15,2) AS cogs_total,
         SUM(COALESCE(s.discount_applied,0))::numeric(15,2) AS discount_amount
  FROM runtime.product p JOIN runtime.sale s ON s.product_id=p.product_id
  GROUP BY p.business_id,p.product_id,p.name,p.category,p.cogs,p.list_price,date_trunc('month',s.sale_date)::date
), calc AS (
 SELECT x.*,(revenue-cogs_total)::numeric(15,2) AS gross_profit,
        ROUND(100.0*(revenue-cogs_total)/NULLIF(revenue,0),2) AS gross_margin_pct,
        ROUND(revenue/NULLIF(units_sold,0),2) AS realized_unit_revenue,
        ROUND(cogs_total/NULLIF(units_sold,0),2) AS realized_unit_cost,
        ROUND(100.0*discount_amount/NULLIF(revenue+discount_amount,0),2) AS effective_discount_pct
 FROM product_period x
), trended AS (
 SELECT c.*,
        LAG(gross_margin_pct) OVER(PARTITION BY product_id ORDER BY period_start) AS prior_margin_pct
 FROM calc c
)
SELECT t.*,
       ROUND(gross_margin_pct-prior_margin_pct,2) AS margin_change_points,
       CASE WHEN revenue IS NULL OR revenue=0 OR cogs IS NULL THEN 'CANNOT_DECIDE' ELSE 'READY' END AS data_quality_status
FROM trended t;
