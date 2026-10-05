-- Accord Retail: Customer Retention agent preparation
-- Missing observations remain NULL; zero is reserved for an observed zero.
CREATE SCHEMA IF NOT EXISTS agent;

CREATE OR REPLACE VIEW agent.customer_retention_context AS
WITH customer_sales AS (
 SELECT c.business_id,c.customer_id,c.acquisition_channel,c.first_purchase_date,c.last_purchase_date,c.repeat_count,c.churn_status,
        COUNT(s.sale_id) AS observed_orders,
        CASE WHEN COUNT(s.sale_id)=0 THEN NULL ELSE SUM(s.revenue)::numeric(15,2) END AS observed_revenue,
        MIN(s.sale_date) AS observed_first_purchase,
        MAX(s.sale_date) AS observed_last_purchase
 FROM runtime.customer c LEFT JOIN runtime.sale s ON s.customer_id=c.customer_id AND s.business_id=c.business_id
 GROUP BY c.business_id,c.customer_id,c.acquisition_channel,c.first_purchase_date,c.last_purchase_date,c.repeat_count,c.churn_status
), anchor AS (
 SELECT business_id,MAX(sale_date)::date AS data_as_of FROM runtime.sale GROUP BY business_id
)
SELECT cs.*,a.data_as_of,
       CASE WHEN COALESCE(cs.observed_last_purchase,cs.last_purchase_date) IS NULL THEN NULL
            ELSE (a.data_as_of-COALESCE(cs.observed_last_purchase,cs.last_purchase_date)::date) END AS recency_days,
       CASE WHEN cs.observed_orders>1 THEN TRUE
            WHEN cs.observed_orders=1 THEN FALSE
            WHEN cs.repeat_count IS NOT NULL THEN cs.repeat_count>1
            ELSE NULL END AS repeat_customer,
       CASE WHEN COALESCE(cs.observed_last_purchase,cs.last_purchase_date) IS NULL THEN NULL
            ELSE (a.data_as_of-COALESCE(cs.observed_last_purchase,cs.last_purchase_date)::date)>90 END AS inactive_90d,
       CASE WHEN COALESCE(cs.observed_first_purchase,cs.first_purchase_date) IS NULL THEN NULL
            ELSE date_trunc('month',COALESCE(cs.observed_first_purchase,cs.first_purchase_date))::date END AS cohort_month,
       CASE WHEN COALESCE(cs.observed_last_purchase,cs.last_purchase_date) IS NULL THEN 'INSUFFICIENT_HISTORY'
            WHEN cs.observed_orders=0 THEN 'PROFILE_ONLY_NO_OBSERVED_SALES'
            ELSE 'READY' END AS retention_evidence_status
FROM customer_sales cs JOIN anchor a ON a.business_id=cs.business_id;

CREATE OR REPLACE VIEW agent.customer_retention_business AS
SELECT business_id,
       COUNT(*) AS customer_count,
       COUNT(*) FILTER(WHERE retention_evidence_status='READY') AS customers_with_observed_sales,
       COUNT(*) FILTER(WHERE repeat_customer IS TRUE) AS repeat_customers,
       ROUND(100.0*COUNT(*) FILTER(WHERE repeat_customer IS TRUE)/NULLIF(COUNT(*) FILTER(WHERE repeat_customer IS NOT NULL),0),2) AS repeat_purchase_rate_pct,
       COUNT(*) FILTER(WHERE inactive_90d IS TRUE) AS inactive_customers_90d,
       ROUND(100.0*COUNT(*) FILTER(WHERE inactive_90d IS TRUE)/NULLIF(COUNT(*) FILTER(WHERE inactive_90d IS NOT NULL),0),2) AS inactivity_rate_90d_pct,
       ROUND(SUM(observed_revenue) FILTER(WHERE inactive_90d IS TRUE),2) AS historical_revenue_of_inactive_customers
FROM agent.customer_retention_context GROUP BY business_id;
