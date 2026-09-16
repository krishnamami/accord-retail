-- Load 10,000 customers (1000 per business)
WITH customer_cohort AS (
  SELECT 
    'biz_' || LPAD((((n-1) / 1000) + 1)::TEXT, 3, '0') as business_id,
    'cust_' || LPAD(n::TEXT, 7, '0') as customer_id,
    CASE 
      WHEN RANDOM() < 0.60 THEN 'active'
      ELSE 'churned'
    END as churn_status
  FROM GENERATE_SERIES(1, 10000) n
)
INSERT INTO runtime.customer (business_id, customer_id, churn_status, created_at)
SELECT business_id, customer_id, churn_status, NOW() FROM customer_cohort;

SELECT business_id, churn_status, COUNT(*) FROM runtime.customer WHERE customer_id LIKE 'cust_%' GROUP BY business_id, churn_status;
