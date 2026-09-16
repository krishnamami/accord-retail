-- Load inventory (500 records)
WITH inventory_gen AS (
  SELECT 
    business_id,
    product_id,
    (RANDOM() * 500)::INT as quantity_on_hand,
    (RANDOM() * 300 + 50)::INT as avg_quantity_held,
    (NOW() - INTERVAL '1 day' * RANDOM())::TIMESTAMP as last_updated
  FROM runtime.product
)
INSERT INTO runtime.inventory (business_id, product_id, quantity_on_hand, avg_quantity_held, last_updated, created_at)
SELECT business_id, product_id, quantity_on_hand, avg_quantity_held, last_updated, NOW() FROM inventory_gen;

SELECT business_id, COUNT(*) as inventory_count FROM runtime.inventory GROUP BY business_id;
