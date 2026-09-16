-- ============================================================
-- ACTION SCORING RULES (Phase 2 - Generate Recommendations)
-- SCD Type 2 Versioning (matches kb_governance_rule pattern)
-- ============================================================

-- ============================================================
-- 1. Base table: Action Scoring Rules (mutable)
-- ============================================================

DROP TABLE IF EXISTS ontology.kb_action_scoring_rule CASCADE;

CREATE TABLE ontology.kb_action_scoring_rule (
  rule_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  kb_version_id UUID NOT NULL REFERENCES ontology.kb_version(kb_version_id) ON DELETE CASCADE,
  
  -- Rule identification
  rule_name VARCHAR(255),
  rule_description TEXT,
  
  -- Scope: What this rule applies to
  action_type VARCHAR(100) NOT NULL,
  bottleneck_type VARCHAR(100) NOT NULL,
  
  -- Scoring criteria (what we evaluate)
  score_metric VARCHAR(100) NOT NULL,
  threshold NUMERIC(10,4) NOT NULL,
  operator VARCHAR(10) NOT NULL,
  
  -- Decision: What verdict to assign
  verdict VARCHAR(50) NOT NULL,
  confidence NUMERIC(3,2),
  
  -- Priority & logic
  priority INT DEFAULT 100,
  logic_json JSONB,
  
  -- Lifecycle
  effective_date DATE NOT NULL DEFAULT CURRENT_DATE,
  sunset_date DATE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  created_by VARCHAR(100) DEFAULT 'system'
);

COMMENT ON TABLE ontology.kb_action_scoring_rule IS 'Rules that determine if an action recommendation should be RECOMMENDED or NOT_RECOMMENDED';

CREATE INDEX idx_action_scoring_rule_kb_version ON ontology.kb_action_scoring_rule(kb_version_id);
CREATE INDEX idx_action_scoring_rule_scope ON ontology.kb_action_scoring_rule(action_type, bottleneck_type);
CREATE INDEX idx_action_scoring_rule_metric ON ontology.kb_action_scoring_rule(score_metric);
CREATE INDEX idx_action_scoring_rule_verdict ON ontology.kb_action_scoring_rule(verdict);
CREATE INDEX idx_action_scoring_rule_priority ON ontology.kb_action_scoring_rule(priority);

-- ============================================================
-- 2. SCD Type 2 table: Version history of rules
-- ============================================================

DROP TABLE IF EXISTS audit.scd_action_scoring_rule_version CASCADE;

CREATE TABLE audit.scd_action_scoring_rule_version (
  rule_version_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  rule_id UUID NOT NULL REFERENCES ontology.kb_action_scoring_rule(rule_id) ON DELETE CASCADE,
  
  rule_version_number INT NOT NULL,
  effective_date DATE NOT NULL,
  end_date DATE,
  is_active BOOLEAN DEFAULT TRUE,
  
  change_reason VARCHAR(500),
  changed_by VARCHAR(100),
  
  action_type VARCHAR(100) NOT NULL,
  bottleneck_type VARCHAR(100) NOT NULL,
  score_metric VARCHAR(100) NOT NULL,
  threshold NUMERIC(10,4) NOT NULL,
  operator VARCHAR(10) NOT NULL,
  verdict VARCHAR(50) NOT NULL,
  confidence NUMERIC(3,2),
  priority INT,
  
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  
  UNIQUE(rule_id, rule_version_number)
);

CREATE INDEX idx_scd_action_rule_active ON audit.scd_action_scoring_rule_version(rule_id, is_active);
CREATE INDEX idx_scd_action_rule_effective ON audit.scd_action_scoring_rule_version(rule_id, effective_date DESC);

-- ============================================================
-- 3. Audit table: Rule application log
-- ============================================================

DROP TABLE IF EXISTS audit.action_scoring_rule_application;

CREATE TABLE audit.action_scoring_rule_application (
  application_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  decision_id UUID,
  business_id UUID,
  rule_id UUID NOT NULL REFERENCES ontology.kb_action_scoring_rule(rule_id),
  rule_version_number INT,
  action_name VARCHAR(255),
  action_type VARCHAR(100),
  bottleneck_type VARCHAR(100),
  score_metric VARCHAR(100),
  metric_value NUMERIC(15,4),
  threshold NUMERIC(10,4),
  operator VARCHAR(10),
  rule_matched BOOLEAN,
  verdict_assigned VARCHAR(50),
  confidence NUMERIC(3,2),
  applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  applied_by VARCHAR(100) DEFAULT 'system'
);

CREATE INDEX idx_action_scoring_app_decision ON audit.action_scoring_rule_application(decision_id);
CREATE INDEX idx_action_scoring_app_business ON audit.action_scoring_rule_application(business_id);
CREATE INDEX idx_action_scoring_app_rule ON audit.action_scoring_rule_application(rule_id, rule_version_number);
CREATE INDEX idx_action_scoring_app_verdict ON audit.action_scoring_rule_application(verdict_assigned);

-- ============================================================
-- 4. Sample rules for different bottleneck types
-- ============================================================

WITH kb_context AS (
  SELECT kb_version_id FROM ontology.kb_version WHERE is_active = true LIMIT 1
)

INSERT INTO ontology.kb_action_scoring_rule (
  kb_version_id, rule_name, rule_description, 
  action_type, bottleneck_type, 
  score_metric, threshold, operator, 
  verdict, confidence, priority, 
  effective_date, created_by
)

SELECT 
  (SELECT kb_version_id FROM ontology.kb_version WHERE is_active = true LIMIT 1),
  rule_name, description,
  action, bottleneck,
  metric, thresh, op,
  verd, conf, pri,
  CURRENT_DATE, 'system'
FROM (VALUES
  ('CHR-P1-ROI-High', 'High ROI actions for churn should be recommended', 'PRICE_CHANGE', 'churn', 'roi', 0.70, '>=', 'RECOMMENDED', 0.95, 1),
  ('CHR-P2-ROI-Medium', 'Medium ROI acceptable for churn if low investment', 'PRICE_CHANGE', 'churn', 'roi', 0.50, '>=', 'CONDITIONAL', 0.85, 2),
  ('CHR-P3-Payback-Fast', 'Fast payback (< 8 weeks) supports recommendation', 'PRICE_CHANGE', 'churn', 'payback_weeks', 8, '<=', 'RECOMMENDED', 0.90, 3),
  ('CHR-P4-Investment-High', 'High investment ($50K+) blocks recommendation for churn', 'PRICE_CHANGE', 'churn', 'investment_usd', 50000, '>=', 'NOT_RECOMMENDED', 0.85, 4),
  ('CHR-L1-ROI-Medium', 'Medium ROI acceptable for loyalty (lower risk)', 'LOYALTY_OFFER', 'churn', 'roi', 0.50, '>=', 'RECOMMENDED', 0.80, 5),
  ('CHR-L2-Payback-Acceptable', 'Loyalty payback <= 12 weeks is acceptable', 'LOYALTY_OFFER', 'churn', 'payback_weeks', 12, '<=', 'RECOMMENDED', 0.85, 6),
  ('CHR-L3-Risk-Manageable', 'Medium risk acceptable for loyalty programs', 'LOYALTY_OFFER', 'churn', 'risk_level', 2, '<=', 'RECOMMENDED', 0.75, 7),
  ('CHR-PK1-ROI-High', 'High ROI required for product discontinuation', 'PRODUCT_KILL', 'churn', 'roi', 0.60, '>=', 'RECOMMENDED', 0.80, 8),
  ('CHR-PK2-Risk-Limit', 'Product kills with HIGH risk not recommended', 'PRODUCT_KILL', 'churn', 'risk_level', 3, '>=', 'NOT_RECOMMENDED', 0.90, 9),
  ('MAR-P1-ROI-High', 'High ROI required for margin improvement via price', 'PRICE_CHANGE', 'margin', 'roi', 0.60, '>=', 'RECOMMENDED', 0.90, 10),
  ('MAR-P2-Customer-Impact', 'Price increases affecting >20% of customers need approval', 'PRICE_CHANGE', 'margin', 'customer_impact_pct', 20, '>=', 'REQUIRES_APPROVAL', 0.85, 11),
  ('INV-R1-ROI-Threshold', 'Inventory rebalancing needs positive ROI', 'INVENTORY_REBALANCE', 'inventory', 'roi', 0.30, '>=', 'RECOMMENDED', 0.75, 12),
  ('INV-R2-Risk-Acceptable', 'Risk must be LOW or MEDIUM for inventory actions', 'INVENTORY_REBALANCE', 'inventory', 'risk_level', 2, '<=', 'RECOMMENDED', 0.80, 13),
  ('UNIV-ROI-Negative', 'No action with negative ROI should be recommended', 'ANY', 'ANY', 'roi', 0.00, '<', 'NOT_RECOMMENDED', 1.00, 0)
) AS rules(rule_name, description, action, bottleneck, metric, thresh, op, verd, conf, pri)
ON CONFLICT DO NOTHING;

-- ============================================================
-- 5. Create initial version history
-- ============================================================

INSERT INTO audit.scd_action_scoring_rule_version (
  rule_id, rule_version_number, effective_date, is_active,
  change_reason, changed_by,
  action_type, bottleneck_type, score_metric, threshold, operator, verdict, confidence, priority
)

SELECT 
  rule_id, 1, CURRENT_DATE, TRUE,
  'Initial rule creation', 'system',
  action_type, bottleneck_type, score_metric, threshold, operator, verdict, confidence, priority
FROM ontology.kb_action_scoring_rule
WHERE kb_version_id = (SELECT kb_version_id FROM ontology.kb_version WHERE is_active = true LIMIT 1)
ON CONFLICT DO NOTHING;
