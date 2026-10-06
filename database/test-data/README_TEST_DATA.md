# Test Data

## Summary
- 10 businesses
- 500 products (50 per business)
- 10,000 customers (1000 per business)
- 20,000 sales (2000 per business)
- 500 inventory records

## Execute in order
1. 01_load_businesses.sql
2. 02_load_products.sql
3. 03_load_customers.sql
4. 04_load_sales.sql
5. 05_load_inventory.sql
6. 06_prepare_customer_retention_data.sql
7. 06b_normalize_retail_economics.sql
8. 07_prepare_pricing_opportunity_data.sql

## Preparation contracts
- Customer Retention preparation changes customer assignment/profile assertions but preserves financial facts and sale dates.
- Economic normalization preserves sale dates, customer assignment, product assignment, channel, and quantity. It normalizes product COGS and recomputes sale revenue/discount from list price using deterministic discount scenarios.
- Pricing Opportunity preparation adds product-level competitor evidence and does not alter financial facts.
