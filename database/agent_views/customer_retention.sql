-- Accord Retail: Customer Retention agent preparation
CREATE SCHEMA IF NOT EXISTS agent;

CREATE OR REPLACE VIEW agent.customer_retention_context AS
WITH customer_sales AS (
 SELECT c.business_id,c.customer_id,c.acquisition_channel,c.first_purchase_date,c.last_purchase_date,c.repeat_count,c.churn_status,
        COUNT(s.sale_id) AS observed_orders,
        SUM(COALESCE(s.revenue,0))::numeric(15,2) AS observed_revenue,
        MIN(s.sale_date) AS observed_first_purchase,
        MAX(s.sale_date) AS observed_last_purchase
 FROM runtime.customer c LEFT JOIN runtime.sale s ON s.customer_id=c.customer_id AND s.business_id=c.business_id
 GROUP BY c.business_id,c.customer_id,c.acquisition_channel,c.first_purchase_date,c.last_purchase_date,c.repeat_count,c.churn_status
), anchor AS (
 SELECT business_id,MAX(sale_date) AS data_as_of FROM runtime.sale GROUP BY business_id
)
SELECT cs.*,a.data_as_of,
       (a.data_as_of-COALESCE(cs.observed_last_purchase,cs.last_purchase_date)) AS recency_days,
       CASE WHEN cs.observed_orders>1 OR cs.repeat_count>1 THEN TRUE ELSE FALSE END AS repeat_customer,
       CASE WHEN a.data_as_of-COALESCE(cs.observed_last_purchase,cs.last_purchase_date) > 90 THEN TRUE ELSE FALSE END AS inactive_90d,
       date_trunc('month',COALESCE(cs.observed_first_purchase,cs.first_purchase_date))::date AS cohort_month,
       CASE WHEN COALESCE(cs.observed_last_purchase,cs.last_purchase_date) IS NULL THEN 'INSUFFICIENT_HISTORY' ELSE 'READY' END AS data_quality_status
FROM customer_sales cs JOIN anchor a ON a.business_id=cs.business_id;

CREATE OR REPLACE VIEW agent.customer_retention_business AS
SELECT business_id,COUNT(*) AS customer_count,
       COUNT(*) FILTER(WHERE repeat_customer) AS repeat_customers,
       ROUND(100.0*COUNT(*) FILTER(WHERE repeat_customer)/NULLIF(COUNT(*),0),2) AS repeat_purchase_rate_pct,
       COUNT(*) FILTER(WHERE inactive_90d) AS inactive_customers_90d,
       ROUND(100.0*COUNT(*) FILTER(WHERE inactive_90d)/NULLIF(COUNT(*),0),2) AS inactivity_rate_90d_pct,
       ROUND(SUM(observed_revenue) FILTER(WHERE inactive_90d),2) AS historical_revenue_of_inactive_customers
FROM agent.customer_retention_context GROUP BY business_id;
