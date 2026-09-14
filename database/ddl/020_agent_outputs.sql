-- ============================================================
-- AGENT OUTPUTS (Phase 3B - Parallel Agent Runtime)
-- ============================================================

DROP TABLE IF EXISTS runtime.agent_execution CASCADE;
CREATE TABLE runtime.agent_execution (
  execution_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  decision_id UUID NOT NULL REFERENCES runtime.decision(decision_id) ON DELETE CASCADE,
  business_id UUID NOT NULL,
  execution_started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  execution_completed_at TIMESTAMP,
  execution_duration_ms INT,
  execution_status VARCHAR(50) NOT NULL CHECK (execution_status IN ('PENDING', 'IN_PROGRESS', 'COMPLETED', 'FAILED')),
  execution_error_message TEXT,
  readiness_agent_status VARCHAR(50),
  explainer_agent_status VARCHAR(50),
  risk_agent_status VARCHAR(50),
  outcome_agent_status VARCHAR(50),
  scenario_agent_status VARCHAR(50),
  triggered_by VARCHAR(100) DEFAULT 'system',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_agent_execution_decision ON runtime.agent_execution(decision_id);
CREATE INDEX idx_agent_execution_business ON runtime.agent_execution(business_id);
CREATE INDEX idx_agent_execution_status ON runtime.agent_execution(execution_status);

DROP TABLE IF EXISTS runtime.agent_decision_readiness CASCADE;
CREATE TABLE runtime.agent_decision_readiness (
  readiness_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  decision_id UUID NOT NULL REFERENCES runtime.decision(decision_id) ON DELETE CASCADE,
  execution_id UUID NOT NULL REFERENCES runtime.agent_execution(execution_id) ON DELETE CASCADE,
  agent_name VARCHAR(100) DEFAULT 'Decision Readiness',
  agent_version VARCHAR(50),
  prompt_version VARCHAR(50),
  model_version VARCHAR(50) DEFAULT 'claude-sonnet-4-6',
  decision_readiness VARCHAR(50) NOT NULL CHECK (decision_readiness IN ('READY', 'CONDITIONAL', 'CANNOT_DECIDE')),
  readiness_rationale TEXT,
  evidence_assessment JSONB,
  assumption_validation JSONB,
  policy_compliance JSONB,
  missing_requirements JSONB,
  blocking_requirements TEXT[],
  recommended_next_steps JSONB,
  decision_quality_summary JSONB,
  input_hash VARCHAR(64),
  output_hash VARCHAR(64),
  confidence_score NUMERIC(3,2),
  generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  generated_by VARCHAR(100) DEFAULT 'claude-sonnet-4-6'
);
CREATE INDEX idx_readiness_decision ON runtime.agent_decision_readiness(decision_id);
CREATE INDEX idx_readiness_verdict ON runtime.agent_decision_readiness(decision_readiness);

DROP TABLE IF EXISTS runtime.agent_recommendation_explainer CASCADE;
CREATE TABLE runtime.agent_recommendation_explainer (
  explainer_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  decision_id UUID NOT NULL REFERENCES runtime.decision(decision_id) ON DELETE CASCADE,
  execution_id UUID NOT NULL REFERENCES runtime.agent_execution(execution_id) ON DELETE CASCADE,
  agent_name VARCHAR(100) DEFAULT 'Recommendation Explainer',
  agent_version VARCHAR(50),
  prompt_version VARCHAR(50),
  model_version VARCHAR(50) DEFAULT 'claude-sonnet-4-6',
  summary TEXT,
  why_now JSONB,
  why_this_option JSONB,
  why_not_other_options JSONB,
  key_evidence JSONB,
  assumptions_to_watch JSONB,
  input_hash VARCHAR(64),
  output_hash VARCHAR(64),
  confidence_score NUMERIC(3,2),
  generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  generated_by VARCHAR(100) DEFAULT 'claude-sonnet-4-6'
);
CREATE INDEX idx_explainer_decision ON runtime.agent_recommendation_explainer(decision_id);

DROP TABLE IF EXISTS runtime.agent_risk_assessment CASCADE;
CREATE TABLE runtime.agent_risk_assessment (
  risk_assessment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  decision_id UUID NOT NULL REFERENCES runtime.decision(decision_id) ON DELETE CASCADE,
  execution_id UUID NOT NULL REFERENCES runtime.agent_execution(execution_id) ON DELETE CASCADE,
  agent_name VARCHAR(100) DEFAULT 'Risk Assessor',
  agent_version VARCHAR(50),
  prompt_version VARCHAR(50),
  model_version VARCHAR(50) DEFAULT 'claude-sonnet-4-6',
  overall_risk VARCHAR(50) NOT NULL CHECK (overall_risk IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
  overall_risk_rationale TEXT,
  risks JSONB,
  blocking_risks TEXT[],
  monitoring_signals JSONB,
  approval_guardrails JSONB,
  input_hash VARCHAR(64),
  output_hash VARCHAR(64),
  confidence_score NUMERIC(3,2),
  generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  generated_by VARCHAR(100) DEFAULT 'claude-sonnet-4-6'
);
CREATE INDEX idx_risk_decision ON runtime.agent_risk_assessment(decision_id);
CREATE INDEX idx_risk_overall ON runtime.agent_risk_assessment(overall_risk);

DROP TABLE IF EXISTS runtime.agent_outcome_prediction CASCADE;
CREATE TABLE runtime.agent_outcome_prediction (
  outcome_prediction_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  decision_id UUID NOT NULL REFERENCES runtime.decision(decision_id) ON DELETE CASCADE,
  execution_id UUID NOT NULL REFERENCES runtime.agent_execution(execution_id) ON DELETE CASCADE,
  agent_name VARCHAR(100) DEFAULT 'Outcome Predictor',
  agent_version VARCHAR(50),
  prompt_version VARCHAR(50),
  model_version VARCHAR(50) DEFAULT 'claude-sonnet-4-6',
  day_30_summary TEXT,
  day_30_expected_changes JSONB,
  day_30_leading_indicators JSONB,
  day_30_warning_signs JSONB,
  day_60_summary TEXT,
  day_60_expected_changes JSONB,
  day_90_summary TEXT,
  day_90_expected_changes JSONB,
  confidence_commentary TEXT,
  assumptions_that_matter JSONB,
  measurement_dashboard JSONB,
  input_hash VARCHAR(64),
  output_hash VARCHAR(64),
  confidence_score NUMERIC(3,2),
  generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  generated_by VARCHAR(100) DEFAULT 'claude-sonnet-4-6'
);
CREATE INDEX idx_outcome_decision ON runtime.agent_outcome_prediction(decision_id);

DROP TABLE IF EXISTS runtime.agent_scenario_analysis CASCADE;
CREATE TABLE runtime.agent_scenario_analysis (
  scenario_analysis_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  decision_id UUID NOT NULL REFERENCES runtime.decision(decision_id) ON DELETE CASCADE,
  execution_id UUID NOT NULL REFERENCES runtime.agent_execution(execution_id) ON DELETE CASCADE,
  agent_name VARCHAR(100) DEFAULT 'What-If Scenario',
  agent_version VARCHAR(50),
  prompt_version VARCHAR(50),
  model_version VARCHAR(50) DEFAULT 'claude-sonnet-4-6',
  scenarios JSONB,
  comparison_narrative TEXT,
  scenario_tradeoff_analysis JSONB,
  risk_assessment_scenario_vs_base JSONB,
  scenarios_similar_to_explore JSONB,
  recommendation_impact TEXT,
  when_to_use_this_scenario TEXT,
  input_hash VARCHAR(64),
  output_hash VARCHAR(64),
  confidence_score NUMERIC(3,2),
  generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  generated_by VARCHAR(100) DEFAULT 'claude-sonnet-4-6'
);
CREATE INDEX idx_scenario_decision ON runtime.agent_scenario_analysis(decision_id);

DROP TABLE IF EXISTS runtime.agent_summary CASCADE;
CREATE TABLE runtime.agent_summary (
  summary_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  decision_id UUID NOT NULL REFERENCES runtime.decision(decision_id) ON DELETE CASCADE,
  execution_id UUID NOT NULL REFERENCES runtime.agent_execution(execution_id) ON DELETE CASCADE,
  decision_readiness VARCHAR(50),
  decision_readiness_rationale TEXT,
  explainer_summary TEXT,
  explainer_why_now TEXT,
  overall_risk VARCHAR(50),
  top_risks JSONB,
  approval_guardrails TEXT[],
  outcome_day_30 TEXT,
  outcome_day_90 TEXT,
  measurement_plan_summary TEXT,
  scenarios_explored TEXT[],
  recommendation_impact TEXT,
  ready_for_human_approval BOOLEAN,
  approval_blockers TEXT[],
  generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  summary_version INT DEFAULT 1
);
CREATE INDEX idx_summary_decision ON runtime.agent_summary(decision_id);
CREATE INDEX idx_summary_ready ON runtime.agent_summary(ready_for_human_approval);

DROP TABLE IF EXISTS audit.agent_invocation_log CASCADE;
CREATE TABLE audit.agent_invocation_log (
  invocation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  execution_id UUID NOT NULL REFERENCES runtime.agent_execution(execution_id),
  agent_name VARCHAR(100) NOT NULL,
  agent_version VARCHAR(50),
  invocation_started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  invocation_completed_at TIMESTAMP,
  invocation_duration_ms INT,
  api_call_count INT DEFAULT 1,
  total_tokens_used INT,
  input_tokens INT,
  output_tokens INT,
  input_hash VARCHAR(64),
  input_size_bytes INT,
  output_hash VARCHAR(64),
  output_size_bytes INT,
  invocation_status VARCHAR(50) CHECK (invocation_status IN ('SUCCESS', 'PARTIAL', 'FAILED')),
  error_message TEXT,
  model_name VARCHAR(100),
  temperature NUMERIC(3,2),
  max_tokens INT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_invocation_execution ON audit.agent_invocation_log(execution_id);
CREATE INDEX idx_invocation_agent ON audit.agent_invocation_log(agent_name);
CREATE INDEX idx_invocation_status ON audit.agent_invocation_log(invocation_status);
