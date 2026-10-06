-- ============================================================
-- Accord Retail Decision OS: common deterministic decision layer
-- Mirrors the proven dental-os decision_outputs + bundle pattern.
-- Does not replace legacy Phase 3B agent_* tables.
-- ============================================================

BEGIN;

CREATE TABLE IF NOT EXISTS runtime.retail_decision_outputs (
    output_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id         UUID NOT NULL,
    subject_type        VARCHAR(30) NOT NULL,
    subject_id          UUID NOT NULL,
    agent_id            VARCHAR(50) NOT NULL,
    agent_version       VARCHAR(30) NOT NULL,
    decision            VARCHAR(60) NOT NULL,
    severity            VARCHAR(20) NOT NULL,
    recommendation      TEXT NOT NULL,
    confidence          NUMERIC(4,3),
    evidence            JSONB NOT NULL DEFAULT '[]',
    calculations        JSONB NOT NULL DEFAULT '{}',
    rules_evaluated     JSONB NOT NULL DEFAULT '[]',
    rules_fired         JSONB NOT NULL DEFAULT '[]',
    boundary            JSONB NOT NULL DEFAULT '{}',
    allowed_actions     JSONB NOT NULL DEFAULT '[]',
    restricted_actions  JSONB NOT NULL DEFAULT '[]',
    context_snapshot    JSONB NOT NULL DEFAULT '{}',
    kb_version          VARCHAR(100),
    rule_version        VARCHAR(100),
    metric_version      VARCHAR(100),
    source_view         VARCHAR(100),
    data_as_of          TIMESTAMPTZ,
    bundle_id           UUID,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT retail_decision_subject_type_chk
      CHECK (subject_type IN ('business','product','customer')),
    CONSTRAINT retail_decision_severity_chk
      CHECK (severity IN ('UNKNOWN','LOW','MEDIUM','HIGH','CRITICAL')),
    CONSTRAINT retail_decision_confidence_chk
      CHECK (confidence IS NULL OR (confidence >= 0 AND confidence <= 1))
);

COMMENT ON TABLE runtime.retail_decision_outputs IS
'Append-only common contract for deterministic Retail agent decisions. One row per agent/subject/pass.';

CREATE INDEX IF NOT EXISTS idx_retail_decision_business
  ON runtime.retail_decision_outputs (business_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_retail_decision_subject
  ON runtime.retail_decision_outputs (subject_type, subject_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_retail_decision_agent
  ON runtime.retail_decision_outputs (agent_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_retail_decision_bundle
  ON runtime.retail_decision_outputs (bundle_id);

CREATE TABLE IF NOT EXISTS runtime.retail_decision_bundles (
    bundle_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id        UUID NOT NULL,
    run_id             UUID NOT NULL DEFAULT gen_random_uuid(),
    context_snapshot   JSONB NOT NULL DEFAULT '{}',
    rules_snapshot     JSONB NOT NULL DEFAULT '{}',
    agent_outputs      JSONB NOT NULL DEFAULT '[]',
    all_signals        JSONB NOT NULL DEFAULT '[]',
    is_current         BOOLEAN NOT NULL DEFAULT TRUE,
    version            INTEGER NOT NULL DEFAULT 1,
    retail_os_version  VARCHAR(30) NOT NULL DEFAULT '0.1.0',
    completed_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE runtime.retail_decision_bundles IS
'Frozen audit/replay snapshot for one Retail orchestration pass, analogous to dental-os persona_bundles.';

CREATE INDEX IF NOT EXISTS idx_retail_bundle_business
  ON runtime.retail_decision_bundles (business_id, completed_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS idx_retail_bundle_current
  ON runtime.retail_decision_bundles (business_id)
  WHERE is_current;

COMMIT;
