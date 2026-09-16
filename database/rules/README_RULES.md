# Rules Engine

## Summary
- 15 deterministic rules
- 10 BOTTLENECK_DIAGNOSIS rules
- 5 RECOMMENDATION_ASSESSMENT rules
- SCD Type 2 versioning

## Key Rules
1. CHR_001: Customer Retention Crisis (churn > 30%)
2. RPR_001: Low Repeat Rate (repeats < 25%)
3. MAR_001: Margin Erosion (margin < 15%)
4. INV_001: Slow Inventory (turnover < 1.5x)

## Execute in order:
1. 01_load_rules_v1.sql
2. 02_rules_scd_versioning.sql
