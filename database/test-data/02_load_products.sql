-- Load 500 products (50 per business)
WITH product_gen AS (
  SELECT 
    'biz_' || LPAD((((n-1) / 50) + 1)::TEXT, 3, '0') as business_id,
    'prod_' || LPAD(n::TEXT, 5, '0') as product_id,
    CASE 
      WHEN (n % 50) < 10 THEN 'Electronics - Premium'
      WHEN (n % 50) < 20 THEN 'Apparel - Basics'
      WHEN (n % 50) < 30 THEN 'Home & Garden'
      WHEN (n % 50) < 40 THEN 'Sports & Outdoors'
      ELSE 'Accessories & Other'
    END as category,
    'Product ' || n as product_name,
    CASE 
      WHEN (n % 50) < 5 THEN ROUND((RANDOM() * 10 + 40)::NUMERIC, 2)
      WHEN (n % 50) < 40 THEN ROUND((RANDOM() * 15 + 20)::NUMERIC, 2)
      WHEN (n % 50) < 48 THEN ROUND((RANDOM() * 10 + 5)::NUMERIC, 2)
      ELSE ROUND((RANDOM() * 5 - 2)::NUMERIC, 2)
    END as margin_pct,
    ROUND((RANDOM() * 500 + 10)::NUMERIC, 2) as cost_per_unit,
    CASE 
      WHEN (n % 50) < 15 THEN 'online'
      WHEN (n % 50) < 30 THEN 'retail'
      ELSE 'both'
    END as channel
  FROM GENERATE_SERIES(1, 500) n
)
INSERT INTO runtime.product (business_id, product_id, product_name, category, channel, cost_per_unit, created_at)
SELECT business_id, product_id, product_name, category, channel, cost_per_unit, NOW()
FROM product_gen;

SELECT business_id, COUNT(*) as product_count FROM runtime.product WHERE product_id LIKE 'prod_%' GROUP BY business_id;
