-- Accord Retail: Revenue Health agent preparation
-- Deterministic context only. No recommendation logic in this view.
-- Comparisons are FULL_MONTH vs FULL_MONTH or MTD vs PRIOR_MONTH_SAME_DAYS.
CREATE SCHEMA IF NOT EXISTS agent;

CREATE OR REPLACE VIEW agent.revenue_health_monthly AS
WITH anchor AS (
  SELECT business_id, MAX(sale_date)::date AS data_as_of
  FROM runtime.sale
  GROUP BY business_id
), monthly AS (
  SELECT s.business_id,
         date_trunc('month', s.sale_date)::date AS period_start,
         SUM(s.revenue)::numeric(15,2) AS revenue,
         SUM(COALESCE(s.quantity,0))::numeric(15,2) AS units_sold,
         COUNT(DISTINCT s.customer_id) AS purchasing_customers,
         MAX(s.sale_date)::date AS period_data_through
  FROM runtime.sale s
  GROUP BY s.business_id, date_trunc('month', s.sale_date)::date
), enriched AS (
  SELECT m.*, a.data_as_of,
         (m.period_start = date_trunc('month',a.data_as_of)::date) AS is_current_period,
         CASE
           WHEN m.period_start = date_trunc('month',a.data_as_of)::date
             THEN EXTRACT(day FROM a.data_as_of)::int
           ELSE EXTRACT(day FROM (m.period_start + INTERVAL '1 month - 1 day'))::int
         END AS comparable_days
  FROM monthly m JOIN anchor a USING (business_id)
), prior_same_days AS (
  SELECT e.*,
         CASE WHEN e.is_current_period THEN (
           SELECT SUM(s2.revenue)::numeric(15,2)
           FROM runtime.sale s2
           WHERE s2.business_id=e.business_id
             AND s2.sale_date >= (e.period_start-INTERVAL '1 month')
             AND s2.sale_date <  (e.period_start-INTERVAL '1 month') + (e.comparable_days||' days')::interval
         ) ELSE LAG(e.revenue) OVER (PARTITION BY e.business_id ORDER BY e.period_start) END AS prior_comparable_revenue,
         CASE WHEN e.is_current_period THEN (
           SELECT SUM(COALESCE(s2.quantity,0))::numeric(15,2)
           FROM runtime.sale s2
           WHERE s2.business_id=e.business_id
             AND s2.sale_date >= (e.period_start-INTERVAL '1 month')
             AND s2.sale_date <  (e.period_start-INTERVAL '1 month') + (e.comparable_days||' days')::interval
         ) ELSE LAG(e.units_sold) OVER (PARTITION BY e.business_id ORDER BY e.period_start) END AS prior_comparable_units,
         CASE WHEN e.is_current_period THEN (
           SELECT COUNT(DISTINCT s2.customer_id)
           FROM runtime.sale s2
           WHERE s2.business_id=e.business_id
             AND s2.sale_date >= (e.period_start-INTERVAL '1 month')
             AND s2.sale_date <  (e.period_start-INTERVAL '1 month') + (e.comparable_days||' days')::interval
         ) ELSE LAG(e.purchasing_customers) OVER (PARTITION BY e.business_id ORDER BY e.period_start) END AS prior_comparable_customers
  FROM enriched e
)
SELECT p.*,
       CASE WHEN is_current_period THEN 'MTD_VS_PRIOR_MONTH_SAME_DAYS' ELSE 'FULL_MONTH_VS_PRIOR_FULL_MONTH' END AS comparison_basis,
       ROUND(100.0*(revenue-prior_comparable_revenue)/NULLIF(prior_comparable_revenue,0),2) AS revenue_change_pct,
       ROUND(100.0*(units_sold-prior_comparable_units)/NULLIF(prior_comparable_units,0),2) AS unit_change_pct,
       ROUND(100.0*(purchasing_customers-prior_comparable_customers)/NULLIF(prior_comparable_customers,0),2) AS purchasing_customer_change_pct,
       ROUND(revenue/NULLIF(units_sold,0),2) AS realized_revenue_per_unit,
       CASE WHEN prior_comparable_revenue IS NULL THEN 'INSUFFICIENT_COMPARABLE_HISTORY' ELSE 'READY' END AS revenue_evidence_status
FROM prior_same_days p;

CREATE OR REPLACE VIEW agent.revenue_health_context AS
WITH latest AS (
  SELECT DISTINCT ON (business_id) *
  FROM agent.revenue_health_monthly
  ORDER BY business_id, period_start DESC
), channels AS (
  SELECT s.business_id,
         jsonb_object_agg(s.channel, s.channel_revenue ORDER BY s.channel) AS revenue_by_channel
  FROM (SELECT business_id,channel,ROUND(SUM(revenue),2) channel_revenue FROM runtime.sale GROUP BY business_id,channel) s
  GROUP BY s.business_id
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
SELECT b.business_id,b.name AS business_name,l.period_start,l.data_as_of,l.comparison_basis,l.comparable_days,
       l.revenue,l.prior_comparable_revenue,l.revenue_change_pct,l.units_sold,l.prior_comparable_units,l.unit_change_pct,
       l.purchasing_customers,l.prior_comparable_customers,l.purchasing_customer_change_pct,l.realized_revenue_per_unit,
       c.revenue_by_channel,p.product_contribution,l.revenue_evidence_status AS data_quality_status
FROM runtime.business b
LEFT JOIN latest l ON l.business_id=b.business_id
LEFT JOIN channels c ON c.business_id=b.business_id
LEFT JOIN products p ON p.business_id=b.business_id;
