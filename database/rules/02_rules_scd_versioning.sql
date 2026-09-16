-- SCD Type 2 Rule Versioning
CREATE TABLE IF NOT EXISTS audit.rule_version_history (
  rule_version_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  rule_id TEXT NOT NULL,
  rule_version_number INT NOT NULL,
  rule_name TEXT NOT NULL,
  rule_logic_json JSONB NOT NULL,
  effective_date TIMESTAMP NOT NULL,
  deprecated_date TIMESTAMP,
  is_active BOOLEAN NOT NULL DEFAULT false,
  created_by TEXT DEFAULT 'system',
  created_at TIMESTAMP DEFAULT NOW()
);

INSERT INTO audit.rule_version_history (rule_id, rule_version_number, rule_name, rule_logic_json, effective_date, is_active)
SELECT
  (additional_json->>'rule_id')::TEXT,
  1,
  rule_name,
  additional_json,
  '2026-01-01'::TIMESTAMP,
  true
FROM ontology.kb_governance_rule
WHERE rule_name LIKE 'RULE_%' ON CONFLICT DO NOTHING;

SELECT COUNT(*) as active_rules FROM audit.rule_version_history WHERE is_active = true;
