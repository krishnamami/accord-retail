-- Product Opportunity Synthesis v1
-- Deterministic, append-only merchandising opportunity layer over current
-- Margin Health, Inventory Exposure and Pricing Opportunity decisions.

CREATE TABLE IF NOT EXISTS runtime.retail_product_opportunities (
    opportunity_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bundle_id UUID NOT NULL REFERENCES runtime.retail_decision_bundles(bundle_id),
    business_id UUID NOT NULL,
    product_id UUID NOT NULL,
    opportunity_type VARCHAR(50) NOT NULL,
    priority VARCHAR(20) NOT NULL,
    recommendation TEXT NOT NULL,
    synthesis_rule_id VARCHAR(30) NOT NULL,
    source_output_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    source_decisions JSONB NOT NULL DEFAULT '{}'::jsonb,
    evidence_status VARCHAR(30) NOT NULL,
    allowed_actions JSONB NOT NULL DEFAULT '[]'::jsonb,
    restricted_actions JSONB NOT NULL DEFAULT '[]'::jsonb,
    synthesis_version VARCHAR(20) NOT NULL DEFAULT '1.0.0',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT retail_product_opportunities_priority_ck
      CHECK (priority IN ('LOW','MEDIUM','HIGH','CRITICAL')),
    CONSTRAINT retail_product_opportunities_evidence_ck
      CHECK (evidence_status IN ('READY','LIMITED','CANNOT_DECIDE')),
    CONSTRAINT retail_product_opportunities_bundle_product_uq
      UNIQUE (bundle_id, product_id)
);

CREATE INDEX IF NOT EXISTS idx_retail_product_opportunities_business
  ON runtime.retail_product_opportunities (business_id, priority);

CREATE INDEX IF NOT EXISTS idx_retail_product_opportunities_product
  ON runtime.retail_product_opportunities (product_id);
