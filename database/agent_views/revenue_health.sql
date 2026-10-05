-- Accord Retail: Revenue Health agent preparation
-- Deterministic context only. No recommendation logic in this view.
CREATE SCHEMA IF NOT EXISTS agent;

CREATE OR REPLACE VIEW agent.revenue_health_monthly AS
WITH monthly AS (
  SELECT s.business_id,
         date_trunc('month', s.sale_date)::date AS period_start,
         SUM(s.revenue)::numeric(15,2) AS revenue,
         SUM(COALESCE(s.quantity,0))::numeric(15,2) AS units_sold,
         COUNT(DISTINCT s.customer_id) AS purchasing_customers
  FROM runtime.sale s
  GROUP BY s.business_id, date_trunc('month', s.sale_date)::date
), trended AS (
  SELECT m.*,
         LAG(revenue) OVER (PARTITION BY business_id ORDER BY period_start) AS prior_revenue,
         LAG(units_sold) OVER (PARTITION BY business_id ORDER BY period_start) AS prior_units,
         LAG(purchasing_customers) OVER (PARTITION BY business_id ORDER BY period_start) AS prior_customers
  FROM monthly m
)
SELECT t.*,
       ROUND(100.0*(revenue-prior_revenue)/NULLIF(prior_revenue,0),2) AS revenue_change_pct,
       ROUND(100.0*(units_sold-prior_units)/NULLIF(prior_units,0),2) AS unit_change_pct,
       ROUND(100.0*(purchasing_customers-prior_customers)/NULLIF(prior_customers,0),2) AS purchasing_customer_change_pct,
       ROUND(revenue/NULLIF(units_sold,0),2) AS realized_revenue_per_unit
FROM trended t;

CREATE OR REPLACE VIEW agent.revenue_health_context AS
WITH latest AS (
  SELECT DISTINCT ON (business_id) *
  FROM agent.revenue_health_monthly
  ORDER BY business_id, period_start DESC
), channels AS (
  SELECT s.business_id,
         jsonb_object_agg(s.channel, s.channel_revenue ORDER BY s.channel) AS revenue_by_channel
  FROM (
    SELECT business_id, channel, ROUND(SUM(revenue),2) AS channel_revenue
    FROM runtime.sale GROUP BY business_id, channel
  ) s GROUP BY s.business_id
), products AS (
  SELECT business_id,
         jsonb_agg(jsonb_build_object('product_id',product_id,'product',name,'category',category,'revenue',revenue,'units',units,'revenue_pct',revenue_pct) ORDER BY revenue DESC) AS product_contribution
  FROM (
    SELECT p.business_id,p.product_id,p.name,p.category,
           ROUND(SUM(s.revenue),2) revenue,SUM(COALESCE(s.quantity,0)) units,
           ROUND(100.0*SUM(s.revenue)/NULLIF(SUM(SUM(s.revenue)) OVER (PARTITION BY p.business_id),0),2) revenue_pct
    FROM runtime.product p LEFT JOIN runtime.sale s ON s.product_id=p.product_id
    GROUP BY p.business_id,p.product_id,p.name,p.category
  ) x GROUP BY business_id
)
SELECT b.business_id,b.name AS business_name,l.period_start,l.revenue,l.prior_revenue,l.revenue_change_pct,
       l.units_sold,l.unit_change_pct,l.purchasing_customers,l.purchasing_customer_change_pct,l.realized_revenue_per_unit,
       c.revenue_by_channel,p.product_contribution,
       CASE WHEN l.prior_revenue IS NULL THEN 'INSUFFICIENT_HISTORY' ELSE 'READY' END AS data_quality_status
FROM runtime.business b
LEFT JOIN latest l ON l.business_id=b.business_id
LEFT JOIN channels c ON c.business_id=b.business_id
LEFT JOIN products p ON p.business_id=b.business_id;
