-- Load 20,000 sales (2000 per business)
WITH sales_gen AS (
  SELECT 
    'biz_' || LPAD((((n-1) / 2000) + 1)::TEXT, 3, '0') as business_id,
    'sale_' || LPAD(n::TEXT, 8, '0') as sale_id,
    'prod_' || LPAD(((((n-1) MOD 2000) MOD 500) + 1)::TEXT, 5, '0') as product_id,
    'cust_' || LPAD((((n-1) MOD 1000) + 1)::TEXT, 7, '0') as customer_id,
    CASE WHEN RANDOM() < 0.60 THEN 'online' WHEN RANDOM() < 0.85 THEN 'retail' ELSE 'marketplace' END as channel,
    (NOW() - INTERVAL '12 months' + INTERVAL '1 day' * (RANDOM() * 365))::DATE as sale_date,
    (RANDOM() * 4 + 1)::INT as units_sold
  FROM GENERATE_SERIES(1, 20000) n
)
INSERT INTO runtime.sale (business_id, sale_id, product_id, customer_id, channel, sale_date, units_sold, created_at)
SELECT business_id, sale_id, product_id, customer_id, channel, sale_date, units_sold, NOW() FROM sales_gen;

SELECT business_id, COUNT(*) as sale_count FROM runtime.sale WHERE sale_id LIKE 'sale_%' GROUP BY business_id;
