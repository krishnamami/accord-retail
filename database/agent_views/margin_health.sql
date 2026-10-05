-- Accord Retail: Margin Health agent preparation
-- Product/month margin context with explicit calendar-aware comparison readiness.
-- Missing months are never silently treated as the prior month.
CREATE SCHEMA IF NOT EXISTS agent;

DROP VIEW IF EXISTS agent.margin_health_context;

CREATE OR REPLACE VIEW agent.margin_health_context AS
WITH anchor AS (
  SELECT business_id, MAX(sale_date)::date AS data_as_of
  FROM runtime.sale
  GROUP BY business_id
),
product_period AS (
  SELECT
      p.business_id,
      p.product_id,
      p.name AS product_name,
      p.category,
      p.cogs,
      p.list_price,
      date_trunc('month', s.sale_date)::date AS period_start,
      SUM(COALESCE(s.quantity,0)) AS units_sold,
      SUM(s.revenue)::numeric(15,2) AS revenue,
      SUM(COALESCE(s.quantity,0) * COALESCE(p.cogs,0))::numeric(15,2) AS cogs_total,
      SUM(COALESCE(s.discount_applied,0))::numeric(15,2) AS discount_amount,
      MAX(s.sale_date)::date AS period_data_through
  FROM runtime.product p
  JOIN runtime.sale s
    ON s.product_id = p.product_id
   AND s.business_id = p.business_id
  GROUP BY
      p.business_id,p.product_id,p.name,p.category,p.cogs,p.list_price,
      date_trunc('month', s.sale_date)::date
),
calc AS (
  SELECT
      pp.*,
      a.data_as_of,
      (pp.period_start = date_trunc('month',a.data_as_of)::date) AS is_current_period,
      CASE
        WHEN pp.period_start = date_trunc('month',a.data_as_of)::date
          THEN EXTRACT(day FROM a.data_as_of)::int
        ELSE EXTRACT(day FROM (pp.period_start + INTERVAL '1 month - 1 day'))::int
      END AS observed_days,
      (pp.revenue - pp.cogs_total)::numeric(15,2) AS gross_profit,
      ROUND(100.0*(pp.revenue-pp.cogs_total)/NULLIF(pp.revenue,0),2) AS gross_margin_pct,
      ROUND(pp.revenue/NULLIF(pp.units_sold,0),2) AS realized_unit_revenue,
      ROUND(pp.cogs_total/NULLIF(pp.units_sold,0),2) AS realized_unit_cost,
      ROUND(100.0*pp.discount_amount/NULLIF(pp.revenue+pp.discount_amount,0),2) AS effective_discount_pct
  FROM product_period pp
  JOIN anchor a ON a.business_id=pp.business_id
),
calendar_prior AS (
  SELECT
      c.*,
      p.period_start AS comparison_period_start,
      p.gross_margin_pct AS prior_margin_pct,
      p.revenue AS prior_revenue,
      p.gross_profit AS prior_gross_profit,
      p.units_sold AS prior_units_sold,
      p.effective_discount_pct AS prior_effective_discount_pct
  FROM calc c
  LEFT JOIN calc p
    ON p.business_id=c.business_id
   AND p.product_id=c.product_id
   AND p.period_start=(c.period_start-INTERVAL '1 month')::date
)
SELECT
    cp.business_id,
    cp.product_id,
    cp.product_name,
    cp.category,
    cp.cogs,
    cp.list_price,
    cp.period_start,
    cp.comparison_period_start,
    CASE
      WHEN cp.comparison_period_start IS NULL THEN 'NO_PRIOR_CALENDAR_MONTH'
      WHEN cp.is_current_period THEN 'CURRENT_PARTIAL_MONTH_MARGIN_VS_PRIOR_FULL_MONTH_MARGIN'
      ELSE 'FULL_MONTH_MARGIN_VS_PRIOR_CALENDAR_MONTH_MARGIN'
    END AS comparison_basis,
    cp.data_as_of,
    cp.period_data_through,
    cp.is_current_period,
    cp.observed_days,
    cp.units_sold,
    cp.revenue,
    cp.cogs_total,
    cp.discount_amount,
    cp.gross_profit,
    cp.gross_margin_pct,
    cp.realized_unit_revenue,
    cp.realized_unit_cost,
    cp.effective_discount_pct,
    cp.prior_margin_pct,
    ROUND(cp.gross_margin_pct-cp.prior_margin_pct,2) AS margin_change_points,
    cp.prior_revenue,
    cp.prior_gross_profit,
    cp.prior_units_sold,
    cp.prior_effective_discount_pct,
    CASE
      WHEN cp.revenue IS NULL OR cp.revenue=0 OR cp.cogs IS NULL THEN 'CANNOT_DECIDE'
      WHEN cp.comparison_period_start IS NULL THEN 'MISSING_PRIOR_MONTH'
      WHEN cp.gross_margin_pct IS NULL OR cp.prior_margin_pct IS NULL THEN 'INSUFFICIENT_MARGIN_EVIDENCE'
      ELSE 'READY'
    END AS margin_evidence_status,
    CASE
      WHEN cp.is_current_period THEN 'PARTIAL_PERIOD_TOTALS_NOT_COMPARABLE'
      WHEN cp.comparison_period_start IS NULL THEN 'MISSING_PRIOR_MONTH'
      ELSE 'READY'
    END AS period_total_comparison_status
FROM calendar_prior cp;
