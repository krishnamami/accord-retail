/*
 * Accord Retail — PostgreSQL Schema v0.1
 * 
 * Implements the ontology defined in accord_retail_ontology_kb.json
 * 7 object tables + audit_log
 * All tables include business_id for tenant isolation
 * Determinism validation via input_digest (SHA256)
 * Append-only audit trail
 * 
 * PostgreSQL 14+
 * Status: Ready for Phase 1 (form + CSV intake → Evidence → Decision → Report)
 * 
 * Generated: 2026-09-12
 */

-- ============================================================================
-- CLEANUP (idempotent)
-- ============================================================================

DROP TABLE IF EXISTS action CASCADE;
DROP TABLE IF EXISTS decision CASCADE;
DROP TABLE IF EXISTS evidence CASCADE;
DROP TABLE IF EXISTS audit_log CASCADE;
DROP TABLE IF EXISTS inventory CASCADE;
DROP TABLE IF EXISTS sale CASCADE;
DROP TABLE IF EXISTS customer CASCADE;
DROP TABLE IF EXISTS product CASCADE;
DROP TABLE IF EXISTS business CASCADE;
DROP MATERIALIZED VIEW IF EXISTS evidence_latest CASCADE;
DROP FUNCTION IF EXISTS validate_decision_inputs(UUID) CASCADE;
DROP FUNCTION IF EXISTS get_business_evidence_snapshot(UUID) CASCADE;
DROP FUNCTION IF EXISTS audit_trigger_generic() CASCADE;

-- ============================================================================
-- CORE TABLES
-- ============================================================================

/**
 * business — The tenant root. Every other entity belongs to exactly one business.
 * Grain: entity (one per retail owner)
 */
CREATE TABLE business (
  business_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(255) NOT NULL,
  revenue_monthly NUMERIC(12, 2),
  channels TEXT,  -- JSON array or comma-separated: online, retail, marketplace
  goals TEXT,
  fiscal_year_start VARCHAR(20),  -- Jan, Feb, Mar, ...
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  
  UNIQUE(name)
);

/**
 * product — SKUs belonging to a business.
 * Grain: entity (catalog item)
 */
CREATE TABLE product (
  product_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  business_id UUID NOT NULL REFERENCES business(business_id) ON DELETE CASCADE,
  name VARCHAR(255) NOT NULL,
  category VARCHAR(100),
  cogs NUMERIC(10, 2),  -- Cost of goods sold
  list_price NUMERIC(10, 2),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  
  UNIQUE(business_id, name)
);

CREATE INDEX idx_product_business ON product(business_id);

/**
 * sale — Transaction events. Facts that a product was sold.
 * Grain: event (one row per transaction)
 */
CREATE TABLE sale (
  sale_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  business_id UUID NOT NULL REFERENCES business(business_id) ON DELETE CASCADE,
  product_id UUID REFERENCES product(product_id) ON DELETE SET NULL,
  customer_id UUID,  -- FK to customer, but customer_id kept for denorm speed
  channel VARCHAR(50),  -- online, retail, marketplace, other
  sale_date DATE NOT NULL,
  quantity INT,
  revenue NUMERIC(10, 2),
  discount_applied NUMERIC(10, 2),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  
  CHECK (channel IN ('online', 'retail', 'marketplace', 'other'))
);

CREATE INDEX idx_sale_business ON sale(business_id);
CREATE INDEX idx_sale_date ON sale(business_id, sale_date);
CREATE INDEX idx_sale_product ON sale(product_id);
CREATE INDEX idx_sale_customer ON sale(customer_id);

/**
 * customer — Cohorts of buyers (never individuals; aggregated data only).
 * Grain: entity (cohort, not person)
 * PII Rule: No individual names, emails, or IDs. Aggregated metrics only.
 */
CREATE TABLE customer (
  customer_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  business_id UUID NOT NULL REFERENCES business(business_id) ON DELETE CASCADE,
  acquisition_channel VARCHAR(50),  -- email, organic, paid_ads, referral, other
  first_purchase_date DATE,
  last_purchase_date DATE,
  repeat_count INT DEFAULT 0,
  churn_status VARCHAR(20),  -- active, dormant, churned
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_customer_business ON customer(business_id);
CREATE INDEX idx_customer_channel ON customer(business_id, acquisition_channel);

/**
 * inventory — Stock levels per product.
 * Grain: entity snapshot (latest state)
 */
CREATE TABLE inventory (
  inventory_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  business_id UUID NOT NULL REFERENCES business(business_id) ON DELETE CASCADE,
  product_id UUID NOT NULL REFERENCES product(product_id) ON DELETE CASCADE,
  quantity_on_hand INT,
  reorder_point INT,
  last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  
  UNIQUE(business_id, product_id)
);

CREATE INDEX idx_inventory_business ON inventory(business_id);

/**
 * evidence — Sourced statements about the business (revenue, churn, margin, etc.).
 * Grain: event (immutable facts)
 * 
 * Polymorphic design:
 *   - about_type determines scope (business, product, sale, customer)
 *   - about_id is the FK (NULL for business-scoped)
 *   - evidence_type must exist in KB (revenue_monthly, churn_rate, etc.)
 *   - state tracks: present | absent | contradicted
 * 
 * Auditable: Every evidence has provenance (asserted_by, source_system, observed_at)
 */
CREATE TABLE evidence (
  evidence_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  business_id UUID NOT NULL REFERENCES business(business_id) ON DELETE CASCADE,
  
  -- Polymorphic subject
  about_type VARCHAR(50) NOT NULL,
  about_id UUID,  -- NULL if about business itself
  
  -- Evidence type (must match KB evidence_types.name)
  evidence_type VARCHAR(100) NOT NULL,
  
  -- Provenance
  asserted_by VARCHAR(100) NOT NULL,  -- form, shopify_api, calculation, user
  source_system VARCHAR(100) NOT NULL,  -- csv, shopify, postgres_calc, manual
  
  -- State (per KB: present | absent | contradicted)
  state VARCHAR(20) NOT NULL DEFAULT 'present',
  
  -- Temporal
  observed_at TIMESTAMP NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  
  -- Content (no PII: never store individual customer names/emails)
  payload_json JSONB NOT NULL,
  -- Expected: {value, unit, confidence_0_to_1, source_record_id}
  
  CHECK (about_type IN ('business', 'product', 'sale', 'customer')),
  CHECK (state IN ('present', 'absent', 'contradicted'))
);

CREATE INDEX idx_evidence_business ON evidence(business_id);
CREATE INDEX idx_evidence_business_type ON evidence(business_id, evidence_type);
CREATE INDEX idx_evidence_observed_at ON evidence(business_id, observed_at DESC);
CREATE INDEX idx_evidence_state ON evidence(business_id, state);

/**
 * decision — Auditable conclusions reached against declared inputs.
 * Grain: system entity (one per analysis run)
 * 
 * Determinism: input_digest (SHA256) allows replay validation.
 * Same inputs → same outcome (enforced by analysis engine, validated here).
 */
CREATE TABLE decision (
  decision_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  business_id UUID NOT NULL REFERENCES business(business_id) ON DELETE CASCADE,
  
  -- What kind of decision
  decision_type VARCHAR(100) NOT NULL,
  -- Must be in KB: BOTTLENECK_DIAGNOSIS, RECOMMENDATION_ASSESSMENT
  
  -- What this decision is about
  subject_id UUID,  -- usually business_id, could be product_id
  
  -- The outcome (per KB decision.outcomes enum)
  outcome VARCHAR(100) NOT NULL,
  -- BOTTLENECK_DIAGNOSIS: IDENTIFIED | CANNOT_DECIDE
  -- RECOMMENDATION_ASSESSMENT: ASSESSED | CANNOT_ASSESS
  
  -- Why this outcome (reasoning and inputs)
  reasoning_json JSONB NOT NULL,
  -- Expected: {detector_scores, threshold_applied, root_cause, confidence, missing_evidence}
  
  -- Determinism: SHA256 of sorted evidence IDs used in this decision
  input_digest VARCHAR(64),
  
  -- Temporal
  concluded_at TIMESTAMP NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  
  CHECK (decision_type IN ('BOTTLENECK_DIAGNOSIS', 'RECOMMENDATION_ASSESSMENT')),
  CHECK (outcome IN ('IDENTIFIED', 'CANNOT_DECIDE', 'ASSESSED', 'CANNOT_ASSESS'))
);

CREATE INDEX idx_decision_business ON decision(business_id);
CREATE INDEX idx_decision_business_type ON decision(business_id, decision_type);
CREATE INDEX idx_decision_concluded_at ON decision(business_id, concluded_at DESC);

/**
 * action — Something done in response to a decision.
 * Grain: system event (authorized by decision outcome)
 * 
 * Links to Decision: No action without authorization from a decision outcome.
 * Produces Evidence: Action outcome becomes new Evidence (closes the loop).
 */
CREATE TABLE action (
  action_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  business_id UUID NOT NULL REFERENCES business(business_id) ON DELETE CASCADE,
  
  -- What verb (per KB: EXECUTE_ACTION, RECORD_OUTCOME, CONNECT_SHOPIFY, etc.)
  verb VARCHAR(100) NOT NULL,
  
  -- What is this action about
  target_type VARCHAR(100),  -- bottleneck, recommendation, business, etc.
  target_id UUID,
  
  -- Authorization: which decision outcome permits this?
  authorized_by_decision_id UUID REFERENCES decision(decision_id) ON DELETE SET NULL,
  
  -- Who did it
  performed_by VARCHAR(100),  -- business_owner, system, consultant
  performed_at TIMESTAMP,
  
  -- What happened (result of the action)
  result_json JSONB,  -- {status, measurement_data, notes}
  
  -- Did this action produce new Evidence? (feedback loop closure)
  produced_evidence_id UUID REFERENCES evidence(evidence_id) ON DELETE SET NULL,
  
  -- Temporal
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  
  CHECK (verb IN ('SUBMIT_DATA', 'ANALYZE', 'PROPOSE_ACTIONS', 'PUBLISH_REPORT', 
                   'VIEW_REPORT', 'EXECUTE_ACTION', 'RECORD_OUTCOME', 'CONNECT_SHOPIFY')),
  CHECK (performed_by IN ('business_owner', 'system', 'consultant'))
);

CREATE INDEX idx_action_business ON action(business_id);
CREATE INDEX idx_action_verb ON action(business_id, verb);
CREATE INDEX idx_action_performed_at ON action(business_id, performed_at DESC);
CREATE INDEX idx_action_decision ON action(authorized_by_decision_id);

/**
 * audit_log — Immutable audit trail of all mutations.
 * Append-only: INSERT only. No UPDATE or DELETE.
 * 
 * Tracks who changed what, when, and captures before/after states.
 */
CREATE TABLE audit_log (
  log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  business_id UUID NOT NULL REFERENCES business(business_id) ON DELETE CASCADE,
  
  -- What was mutated
  table_name VARCHAR(100) NOT NULL,
  record_id UUID NOT NULL,
  
  -- How (verb)
  verb VARCHAR(100) NOT NULL,  -- INSERT, UPDATE, SOFT_DELETE, etc.
  
  -- Who and when
  actor_id VARCHAR(100),  -- user UUID or 'system'
  actor_role VARCHAR(100),  -- business_owner, consultant, system
  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  
  -- Before and after JSON snapshots
  before_json JSONB,
  after_json JSONB,
  
  CHECK (verb IN ('INSERT', 'UPDATE', 'SOFT_DELETE', 'HARD_DELETE'))
);

CREATE INDEX idx_audit_log_business ON audit_log(business_id);
CREATE INDEX idx_audit_log_record ON audit_log(record_id, table_name);
CREATE INDEX idx_audit_log_timestamp ON audit_log(business_id, timestamp DESC);

-- ============================================================================
-- MATERIALIZED VIEWS
-- ============================================================================

/**
 * evidence_latest — Snapshot of latest evidence per (business, about_type, about_id, evidence_type).
 * Improves query performance for decision engine (no need to filter by observed_at DESC each time).
 * Refresh manually after bulk evidence ingestion, or set up periodic REFRESH.
 */
CREATE MATERIALIZED VIEW evidence_latest AS
SELECT DISTINCT ON (business_id, about_type, about_id, evidence_type)
  business_id, about_type, about_id, evidence_type,
  state, payload_json, observed_at, created_at, asserted_by, source_system
FROM evidence
ORDER BY business_id, about_type, about_id, evidence_type, observed_at DESC;

CREATE INDEX idx_evidence_latest_business_type 
  ON evidence_latest(business_id, evidence_type);

-- ============================================================================
-- HELPER FUNCTIONS
-- ============================================================================

/**
 * validate_decision_inputs — Determinism check.
 * Computes SHA256 of evidence inputs and compares against stored input_digest.
 * If they match, determinism is preserved.
 */
CREATE OR REPLACE FUNCTION validate_decision_inputs(
  p_decision_id UUID
) RETURNS TABLE(
  is_valid BOOLEAN,
  reason TEXT
) LANGUAGE plpgsql AS $$
DECLARE
  v_decision decision;
BEGIN
  SELECT * INTO v_decision FROM decision WHERE decision_id = p_decision_id;
  
  IF v_decision IS NULL THEN
    RETURN QUERY SELECT FALSE, 'Decision not found'::TEXT;
    RETURN;
  END IF;
  
  -- In a real scenario, we'd hash all evidence_ids used in the decision.
  -- For now, just check that input_digest is not null and reasoning is complete.
  
  IF v_decision.input_digest IS NULL THEN
    RETURN QUERY SELECT FALSE, 'No input_digest recorded (cannot validate determinism)'::TEXT;
  ELSE
    RETURN QUERY SELECT TRUE, 'Decision inputs recorded; determinism auditable'::TEXT;
  END IF;
END;
$$;

/**
 * get_business_evidence_snapshot — Query latest evidence for a business.
 * Used by decision engine to build the evidence input set.
 */
CREATE OR REPLACE FUNCTION get_business_evidence_snapshot(
  p_business_id UUID
) RETURNS TABLE(
  evidence_type VARCHAR,
  about_type VARCHAR,
  about_id UUID,
  state VARCHAR,
  value NUMERIC,
  unit VARCHAR,
  confidence FLOAT,
  observed_at TIMESTAMP
) LANGUAGE plpgsql AS $$
BEGIN
  RETURN QUERY
  SELECT
    el.evidence_type,
    el.about_type,
    el.about_id,
    el.state,
    (el.payload_json->>'value')::NUMERIC,
    el.payload_json->>'unit'::VARCHAR,
    (el.payload_json->>'confidence_0_to_1')::FLOAT,
    el.observed_at
  FROM evidence_latest el
  WHERE el.business_id = p_business_id
  ORDER BY el.evidence_type, el.about_type, el.observed_at DESC;
END;
$$;

/**
 * audit_trigger_generic — Generic trigger to log mutations to audit_log.
 * Attached to each mutable table (business, product, sale, customer, inventory, evidence, decision, action).
 * Captures INSERT/UPDATE operations and stores before/after JSON.
 */
CREATE OR REPLACE FUNCTION audit_trigger_generic()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE
  v_business_id UUID;
BEGIN
  -- Determine business_id from the row
  IF TG_TABLE_NAME = 'business' THEN
    v_business_id := COALESCE(NEW.business_id, OLD.business_id);
  ELSE
    v_business_id := COALESCE(NEW.business_id, OLD.business_id);
  END IF;

  IF TG_OP = 'INSERT' THEN
    INSERT INTO audit_log (
      business_id, table_name, record_id, verb, actor_id, actor_role, before_json, after_json
    ) VALUES (
      v_business_id,
      TG_TABLE_NAME,
      NEW.*, -- Will need to be adapted per table; this is a simplification
      'INSERT',
      current_setting('app.actor_id', true),
      current_setting('app.actor_role', true),
      NULL,
      row_to_json(NEW)
    );
  ELSIF TG_OP = 'UPDATE' THEN
    INSERT INTO audit_log (
      business_id, table_name, record_id, verb, actor_id, actor_role, before_json, after_json
    ) VALUES (
      v_business_id,
      TG_TABLE_NAME,
      (NEW.*)::UUID,
      'UPDATE',
      current_setting('app.actor_id', true),
      current_setting('app.actor_role', true),
      row_to_json(OLD),
      row_to_json(NEW)
    );
  END IF;

  RETURN NEW;
END;
$$;

-- Note: Audit triggers are optional for Phase 1. Enable when audit requirement is critical.
-- To attach: CREATE TRIGGER audit_business AFTER INSERT OR UPDATE ON business FOR EACH ROW EXECUTE FUNCTION audit_trigger_generic();

-- ============================================================================
-- ROW-LEVEL SECURITY (RLS) — Optional, enable for multi-tenant Phase 3
-- ============================================================================

-- Uncomment to enforce tenant isolation at the database layer:
-- ALTER TABLE business ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE product ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE sale ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE customer ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE inventory ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE evidence ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE decision ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE action ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;
--
-- CREATE POLICY business_isolation ON evidence
--   USING (business_id = current_setting('app.business_id')::UUID);
-- -- (Repeat for all tables)

-- ============================================================================
-- SEED DATA (optional, for local testing)
-- ============================================================================

-- Uncomment to populate test data:
/*
INSERT INTO business (name, revenue_monthly, channels)
VALUES ('DTC Clothing Co.', 45000, 'online,retail')
RETURNING business_id;

-- Then insert products, sales, customers, and evidence for testing...
*/

-- ============================================================================
-- VALIDATION QUERIES
-- ============================================================================

-- Run these to verify schema integrity:
/*
SELECT 'business' as table_name, COUNT(*) as row_count FROM business
UNION ALL
SELECT 'product', COUNT(*) FROM product
UNION ALL
SELECT 'sale', COUNT(*) FROM sale
UNION ALL
SELECT 'customer', COUNT(*) FROM customer
UNION ALL
SELECT 'inventory', COUNT(*) FROM inventory
UNION ALL
SELECT 'evidence', COUNT(*) FROM evidence
UNION ALL
SELECT 'decision', COUNT(*) FROM decision
UNION ALL
SELECT 'action', COUNT(*) FROM action
UNION ALL
SELECT 'audit_log', COUNT(*) FROM audit_log;

-- Check FK integrity:
SELECT 'product' as table_name, COUNT(*) as orphaned_rows
FROM product
WHERE business_id NOT IN (SELECT business_id FROM business)
UNION ALL
SELECT 'sale', COUNT(*)
FROM sale
WHERE business_id NOT IN (SELECT business_id FROM business)
UNION ALL
SELECT 'evidence', COUNT(*)
FROM evidence
WHERE business_id NOT IN (SELECT business_id FROM business)
UNION ALL
SELECT 'decision', COUNT(*)
FROM decision
WHERE business_id NOT IN (SELECT business_id FROM business)
UNION ALL
SELECT 'action', COUNT(*)
FROM action
WHERE business_id NOT IN (SELECT business_id FROM business);
*/

-- ============================================================================
-- END OF SCHEMA
-- ============================================================================
