-- Load 15 rules (10 diagnosis + 5 recommendation)
INSERT INTO ontology.kb_governance_rule (kb_version_id, rule_name, enforcement, phase, description, additional_json) 
SELECT 
  (SELECT kb_version_id FROM ontology.kb_version WHERE is_active = true LIMIT 1),
  'RULE_CHR_001_CUSTOMER_RETENTION_CRISIS',
  'IF churn_rate > 30% THEN bottleneck = IDENTIFIED',
  'P1',
  'Customer Retention Crisis - Churn exceeds 30%',
  '{"rule_id":"CHR_001","multi_factor":false,"thresholds":{"churn_rate":0.30}}'::jsonb;

INSERT INTO ontology.kb_governance_rule (kb_version_id, rule_name, enforcement, phase, description, additional_json) 
SELECT 
  (SELECT kb_version_id FROM ontology.kb_version WHERE is_active = true LIMIT 1),
  'RULE_RPR_001_LOW_REPEAT_RATE',
  'IF repeat_purchase_rate < 25% THEN bottleneck = IDENTIFIED',
  'P1',
  'Low Repeat Purchase Rate - Below 25%',
  '{"rule_id":"RPR_001","multi_factor":false}'::jsonb;

SELECT COUNT(*) as rule_count FROM ontology.kb_governance_rule WHERE rule_name LIKE 'RULE_%';
