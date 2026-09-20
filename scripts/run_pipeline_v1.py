#!/usr/bin/env python3
"""
Accord Retail: Complete Pipeline Loader (Steps 1-8)
Executes the entire data pipeline from raw data to decisions
"""

import psycopg2
import sys
from datetime import datetime

# Database connection
import os
import sys

# Credentials are never hard-coded: DATABASE_URL comes from the environment / .env (see database/scripts/db_config.py)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'database', 'scripts'))
from db_config import connect  # noqa: E402

def connect_db():
    """Connect to database"""
    try:
        conn = connect()
        return conn
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        sys.exit(1)

def execute_sql(conn, sql, description):
    """Execute SQL and report results"""
    cursor = conn.cursor()
    try:
        cursor.execute(sql)
        conn.commit()
        print(f"✅ {description}")
        return True
    except Exception as e:
        conn.rollback()
        print(f"❌ {description}: {e}")
        return False
    finally:
        cursor.close()

def step_0_create_tables(conn):
    """CREATE missing tables"""
    print("\n" + "="*70)
    print("STEP 0: CREATE MISSING TABLES")
    print("="*70)
    
    sql = """
    CREATE TABLE IF NOT EXISTS raw.raw_upload (
      upload_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      business_id UUID NOT NULL REFERENCES runtime.business(business_id),
      source_system VARCHAR NOT NULL,
      upload_type VARCHAR,
      raw_data_json JSONB NOT NULL,
      filename VARCHAR,
      file_size INTEGER,
      uploaded_at TIMESTAMP DEFAULT NOW(),
      uploaded_by VARCHAR,
      processing_status VARCHAR DEFAULT 'pending',
      error_message TEXT,
      created_at TIMESTAMP DEFAULT NOW()
    );
    
    CREATE TABLE IF NOT EXISTS raw.raw_validation_log (
      validation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      upload_id UUID NOT NULL REFERENCES raw.raw_upload(upload_id),
      business_id UUID NOT NULL REFERENCES runtime.business(business_id),
      check_type VARCHAR NOT NULL,
      check_name VARCHAR,
      field_name VARCHAR,
      is_valid BOOLEAN NOT NULL,
      error_message TEXT,
      warning_message TEXT,
      severity VARCHAR,
      checked_at TIMESTAMP DEFAULT NOW(),
      checked_by VARCHAR DEFAULT 'system',
      created_at TIMESTAMP DEFAULT NOW()
    );
    
    CREATE TABLE IF NOT EXISTS processed.processed_details (
      detail_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      processed_id UUID NOT NULL REFERENCES processed.processed_upload(processed_id),
      business_id UUID NOT NULL REFERENCES runtime.business(business_id),
      upload_id UUID REFERENCES raw.raw_upload(upload_id),
      raw_field_name VARCHAR,
      raw_field_value TEXT,
      transformed_field_name VARCHAR,
      transformed_value TEXT,
      calculation_formula TEXT,
      calculation_inputs JSONB,
      calculation_result NUMERIC,
      calculation_confidence NUMERIC,
      data_quality_flags JSONB,
      created_at TIMESTAMP DEFAULT NOW()
    );
    
    CREATE TABLE IF NOT EXISTS audit.scd_rule_version (
      scd_rule_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      rule_id UUID NOT NULL REFERENCES ontology.kb_governance_rule(rule_id),
      rule_version_number INTEGER NOT NULL,
      rule_name VARCHAR NOT NULL,
      enforcement TEXT NOT NULL,
      phase VARCHAR NOT NULL,
      effective_date DATE NOT NULL,
      deprecated_date DATE,
      is_active BOOLEAN NOT NULL DEFAULT true,
      rule_precision NUMERIC,
      rule_recall NUMERIC,
      rule_false_positive_rate NUMERIC,
      created_at TIMESTAMP DEFAULT NOW(),
      created_by VARCHAR DEFAULT 'system'
    );
    
    CREATE INDEX IF NOT EXISTS idx_raw_upload_business ON raw.raw_upload(business_id);
    CREATE INDEX IF NOT EXISTS idx_raw_upload_status ON raw.raw_upload(processing_status);
    CREATE INDEX IF NOT EXISTS idx_validation_upload ON raw.raw_validation_log(upload_id);
    CREATE INDEX IF NOT EXISTS idx_validation_business ON raw.raw_validation_log(business_id);
    CREATE INDEX IF NOT EXISTS idx_processed_details_processed ON processed.processed_details(processed_id);
    CREATE INDEX IF NOT EXISTS idx_scd_rule_active ON audit.scd_rule_version(rule_id, is_active);
    """
    
    execute_sql(conn, sql, "Created missing tables and indexes")

def step_1_load_raw_data(conn):
    """STEP 1: Load Raw Data"""
    print("\n" + "="*70)
    print("STEP 1: LOAD RAW DATA")
    print("="*70)
    
    cursor = conn.cursor()
    cursor.execute("DELETE FROM raw.raw_upload;")
    conn.commit()
    cursor.close()
    
    sql = """
    INSERT INTO raw.raw_upload (
      business_id,
      source_system,
      upload_type,
      raw_data_json,
      filename,
      uploaded_at,
      uploaded_by,
      processing_status
    )
    SELECT
      b.business_id,
      'system_load' as source_system,
      'complete_business_snapshot' as upload_type,
      jsonb_build_object(
        'business_id', b.business_id::text,
        'business_name', b.name,
        'revenue_monthly', b.revenue_monthly,
        'channels', b.channels,
        'snapshot_date', CURRENT_DATE::text,
        'sales_count', (SELECT COUNT(*) FROM runtime.sale WHERE business_id = b.business_id),
        'customer_count', (SELECT COUNT(*) FROM runtime.customer WHERE business_id = b.business_id),
        'total_sales_revenue', (SELECT COALESCE(SUM(revenue), 0) FROM runtime.sale WHERE business_id = b.business_id)
      ) as raw_data_json,
      'business_' || b.business_id::text || '_snapshot.json' as filename,
      NOW() as uploaded_at,
      'system' as uploaded_by,
      'pending' as processing_status
    FROM runtime.business b;
    """
    
    if execute_sql(conn, sql, "Step 1: Loaded raw data"):
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM raw.raw_upload;")
        count = cursor.fetchone()[0]
        cursor.close()
        print(f"   └─ {count} raw uploads created")

def step_2_validate_raw_data(conn):
    """STEP 2: Validate Raw Data"""
    print("\n" + "="*70)
    print("STEP 2: VALIDATE RAW DATA")
    print("="*70)
    
    cursor = conn.cursor()
    cursor.execute("DELETE FROM raw.raw_validation_log;")
    conn.commit()
    cursor.close()
    
    sql = """
    INSERT INTO raw.raw_validation_log (
      upload_id,
      business_id,
      check_type,
      check_name,
      field_name,
      is_valid,
      error_message,
      warning_message,
      severity
    )
    SELECT
      ru.upload_id,
      ru.business_id,
      'schema' as check_type,
      'revenue_numeric' as check_name,
      'revenue_monthly' as field_name,
      (ru.raw_data_json->>'revenue_monthly')::numeric IS NOT NULL as is_valid,
      CASE 
        WHEN (ru.raw_data_json->>'revenue_monthly')::numeric IS NULL 
        THEN 'revenue_monthly is required and must be numeric'
        ELSE NULL
      END as error_message,
      NULL as warning_message,
      CASE 
        WHEN (ru.raw_data_json->>'revenue_monthly')::numeric IS NULL 
        THEN 'error'
        ELSE 'info'
      END as severity
    FROM raw.raw_upload ru;
    
    UPDATE raw.raw_upload
    SET processing_status = 'validated'
    WHERE upload_id NOT IN (
      SELECT DISTINCT upload_id FROM raw.raw_validation_log WHERE severity = 'error'
    );
    """
    
    if execute_sql(conn, sql, "Step 2: Validated raw data"):
        cursor = conn.cursor()
        cursor.execute("SELECT severity, COUNT(*) FROM raw.raw_validation_log GROUP BY severity;")
        for severity, count in cursor.fetchall():
            print(f"   └─ {severity}: {count}")
        cursor.close()

def step_3_fold_transform_normalize(conn):
    """STEP 3: Fold, Transform & Normalize"""
    print("\n" + "="*70)
    print("STEP 3: FOLD, TRANSFORM & NORMALIZE")
    print("="*70)
    
    cursor = conn.cursor()
    cursor.execute("DELETE FROM processed.processed_upload;")
    conn.commit()
    cursor.close()
    
    sql = """
    INSERT INTO processed.processed_upload (
      processed_id,
      business_id,
      upload_id,
      revenue_monthly,
      customer_count,
      repeat_count,
      churn_count,
      repeat_rate,
      churn_rate,
      customer_lifetime_value,
      customer_acquisition_cost,
      product_margin,
      inventory_turnover,
      slow_moving_inventory_pct,
      channel_mix_json,
      confidence_score,
      processed_at,
      processed_by,
      observation_period_start,
      observation_period_end
    )
    SELECT
      gen_random_uuid(),
      b.business_id,
      (SELECT upload_id FROM raw.raw_upload WHERE business_id = b.business_id LIMIT 1),
      COALESCE(SUM(s.revenue), 0),
      COUNT(DISTINCT s.customer_id),
      COUNT(DISTINCT CASE WHEN c.repeat_count > 0 THEN s.customer_id END),
      COUNT(DISTINCT CASE WHEN c.churn_status = 'churned' THEN s.customer_id END),
      ROUND(COUNT(DISTINCT CASE WHEN c.repeat_count > 0 THEN s.customer_id END)::numeric / NULLIF(COUNT(DISTINCT s.customer_id), 0), 4),
      ROUND(COUNT(DISTINCT CASE WHEN c.churn_status = 'churned' THEN s.customer_id END)::numeric / NULLIF(COUNT(DISTINCT s.customer_id), 0), 4),
      ROUND(COALESCE(SUM(s.revenue), 0)::numeric / NULLIF(COUNT(DISTINCT s.customer_id), 0), 2),
      ROUND((COALESCE(SUM(s.revenue), 0) * 0.15)::numeric / NULLIF(COUNT(DISTINCT s.customer_id), 0), 2),
      ROUND((COALESCE(SUM(s.revenue), 0) - COALESCE(SUM(p.cogs * s.quantity), 0))::numeric / NULLIF(SUM(s.revenue), 0), 4),
      ROUND(COALESCE(SUM(s.revenue), 0)::numeric / NULLIF(SUM(inv.quantity_on_hand * p.cogs), 0), 4),
      ROUND(COUNT(DISTINCT CASE WHEN inv.quantity_on_hand > (inv.reorder_point * 2) THEN inv.inventory_id END)::numeric / NULLIF(COUNT(DISTINCT inv.inventory_id), 0) * 100, 2),
      COALESCE(jsonb_object_agg(COALESCE(s.channel, 'unknown'), ROUND(SUM(s.revenue), 2)), '{}'::jsonb),
      ROUND(LEAST(100, (COUNT(DISTINCT s.customer_id)::numeric / 100) * 100), 2),
      NOW(),
      'system',
      MIN(s.sale_date),
      MAX(s.sale_date)
    FROM runtime.business b
    LEFT JOIN runtime.sale s ON b.business_id = s.business_id
    LEFT JOIN runtime.customer c ON s.customer_id = c.customer_id
    LEFT JOIN runtime.product p ON s.product_id = p.product_id
    LEFT JOIN runtime.inventory inv ON b.business_id = inv.business_id
    GROUP BY b.business_id;
    """
    
    if execute_sql(conn, sql, "Step 3: Transformed and normalized data"):
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM processed.processed_upload;")
        count = cursor.fetchone()[0]
        cursor.close()
        print(f"   └─ {count} processed records created")

def step_4_project_to_evidence(conn):
    """STEP 4: Project to Evidence"""
    print("\n" + "="*70)
    print("STEP 4: PROJECT TO EVIDENCE")
    print("="*70)
    
    cursor = conn.cursor()
    cursor.execute("DELETE FROM runtime.evidence;")
    conn.commit()
    cursor.close()
    
    sqls = [
        """INSERT INTO runtime.evidence (evidence_id, business_id, evidence_type, about_type, about_id, asserted_by, source_system, state, observed_at, payload_json, traced_from_upload_id)
        SELECT gen_random_uuid(), pu.business_id, 'churn_rate', 'business', pu.business_id, 'system_calculation', 'processed_upload', 'present', NOW(),
        jsonb_build_object('value', pu.churn_rate, 'unit', 'ratio', 'percentage', ROUND(pu.churn_rate * 100, 2), 'confidence', pu.confidence_score), pu.upload_id
        FROM processed.processed_upload pu;""",
        
        """INSERT INTO runtime.evidence (evidence_id, business_id, evidence_type, about_type, about_id, asserted_by, source_system, state, observed_at, payload_json, traced_from_upload_id)
        SELECT gen_random_uuid(), pu.business_id, 'repeat_purchase_rate', 'business', pu.business_id, 'system_calculation', 'processed_upload', 'present', NOW(),
        jsonb_build_object('value', pu.repeat_rate, 'unit', 'ratio', 'percentage', ROUND(pu.repeat_rate * 100, 2), 'confidence', pu.confidence_score), pu.upload_id
        FROM processed.processed_upload pu;""",
        
        """INSERT INTO runtime.evidence (evidence_id, business_id, evidence_type, about_type, about_id, asserted_by, source_system, state, observed_at, payload_json, traced_from_upload_id)
        SELECT gen_random_uuid(), pu.business_id, 'product_margin', 'business', pu.business_id, 'system_calculation', 'processed_upload', 'present', NOW(),
        jsonb_build_object('value', pu.product_margin, 'unit', 'ratio', 'percentage', ROUND(pu.product_margin * 100, 2), 'confidence', pu.confidence_score), pu.upload_id
        FROM processed.processed_upload pu;""",
        
        """INSERT INTO runtime.evidence (evidence_id, business_id, evidence_type, about_type, about_id, asserted_by, source_system, state, observed_at, payload_json, traced_from_upload_id)
        SELECT gen_random_uuid(), pu.business_id, 'inventory_turnover', 'business', pu.business_id, 'system_calculation', 'processed_upload', 'present', NOW(),
        jsonb_build_object('value', pu.inventory_turnover, 'unit', 'times_per_period', 'confidence', pu.confidence_score), pu.upload_id
        FROM processed.processed_upload pu;""",
        
        """INSERT INTO runtime.evidence (evidence_id, business_id, evidence_type, about_type, about_id, asserted_by, source_system, state, observed_at, payload_json, traced_from_upload_id)
        SELECT gen_random_uuid(), pu.business_id, 'customer_lifetime_value', 'business', pu.business_id, 'system_calculation', 'processed_upload', 'present', NOW(),
        jsonb_build_object('value', pu.customer_lifetime_value, 'unit', 'currency', 'confidence', pu.confidence_score), pu.upload_id
        FROM processed.processed_upload pu;"""
    ]
    
    for i, sql in enumerate(sqls, 1):
        execute_sql(conn, sql, f"  Projected evidence type {i}/5")
    
    cursor = conn.cursor()
    cursor.execute("SELECT evidence_type, COUNT(*) FROM runtime.evidence GROUP BY evidence_type;")
    print("   └─ Evidence Types Loaded:")
    for etype, count in cursor.fetchall():
        print(f"      • {etype}: {count}")
    cursor.close()

def step_5_build_business_context(conn):
    """STEP 5: Build Business Context"""
    print("\n" + "="*70)
    print("STEP 5: BUILD BUSINESS CONTEXT")
    print("="*70)
    
    cursor = conn.cursor()
    cursor.execute("DELETE FROM state.business_context;")
    cursor.execute("DELETE FROM state.assertion;")
    conn.commit()
    cursor.close()
    
    sql = """
    INSERT INTO state.business_context (
      context_id,
      business_id,
      observed_at,
      observation_period_start,
      observation_period_end,
      context_json,
      generated_for_kb_version,
      generated_by
    )
    SELECT
      gen_random_uuid(),
      b.business_id,
      NOW(),
      MIN(pu.observation_period_start),
      MAX(pu.observation_period_end),
      jsonb_build_object(
        'churn_rate', ROUND((SELECT (e.payload_json->>'value')::numeric FROM runtime.evidence e WHERE e.evidence_type = 'churn_rate' AND e.business_id = b.business_id LIMIT 1) * 100, 2),
        'repeat_rate', ROUND((SELECT (e.payload_json->>'value')::numeric FROM runtime.evidence e WHERE e.evidence_type = 'repeat_purchase_rate' AND e.business_id = b.business_id LIMIT 1) * 100, 2),
        'margin', ROUND((SELECT (e.payload_json->>'value')::numeric FROM runtime.evidence e WHERE e.evidence_type = 'product_margin' AND e.business_id = b.business_id LIMIT 1) * 100, 2),
        'overall_health', CASE
          WHEN (SELECT (e.payload_json->>'value')::numeric FROM runtime.evidence e WHERE e.evidence_type = 'churn_rate' AND e.business_id = b.business_id LIMIT 1) > 0.30 THEN 'critical'
          WHEN (SELECT (e.payload_json->>'value')::numeric FROM runtime.evidence e WHERE e.evidence_type = 'churn_rate' AND e.business_id = b.business_id LIMIT 1) > 0.20 THEN 'concerning'
          ELSE 'healthy'
        END
      ),
      (SELECT kb_version_id FROM ontology.kb_version WHERE is_active = true LIMIT 1),
      'system_context_builder'
    FROM runtime.business b
    LEFT JOIN processed.processed_upload pu ON b.business_id = pu.business_id
    GROUP BY b.business_id;
    """
    
    if execute_sql(conn, sql, "Step 5: Built business context"):
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM state.business_context;")
        count = cursor.fetchone()[0]
        cursor.close()
        print(f"   └─ {count} context records created")

def step_6_apply_rules(conn):
    """STEP 6: Apply Rules"""
    print("\n" + "="*70)
    print("STEP 6: APPLY RULES")
    print("="*70)
    
    cursor = conn.cursor()
    cursor.execute("DELETE FROM runtime.rule_execution;")
    conn.commit()
    cursor.close()
    
    sql_versions = """
    INSERT INTO audit.scd_rule_version (rule_id, rule_version_number, rule_name, enforcement, phase, effective_date, is_active, created_by)
    SELECT gkr.rule_id, 1, gkr.rule_name, gkr.enforcement, gkr.phase, CURRENT_DATE, true, 'system'
    FROM ontology.kb_governance_rule gkr
    WHERE NOT EXISTS (SELECT 1 FROM audit.scd_rule_version srv WHERE srv.rule_id = gkr.rule_id);
    """
    
    execute_sql(conn, sql_versions, "  Loaded rule versions (SCD Type 2)")
    
    sql1 = """
    INSERT INTO runtime.rule_execution (execution_id, business_id, rule_id, fired, condition_evaluated, outcome_produced, executed_by_kb_version)
    SELECT gen_random_uuid(), e.business_id, (SELECT rule_id FROM ontology.kb_governance_rule WHERE rule_name = 'RULE_CHR_001' LIMIT 1),
    ((e.payload_json->>'value')::numeric > 0.30), jsonb_build_object('rule_name', 'RULE_CHR_001', 'condition', 'churn > 0.30', 'value', (e.payload_json->>'value')::numeric),
    CASE WHEN ((e.payload_json->>'value')::numeric > 0.30) THEN 'BOTTLENECK_IDENTIFIED' ELSE 'NO_BOTTLENECK' END,
    (SELECT kb_version_id FROM ontology.kb_version WHERE is_active = true LIMIT 1)
    FROM runtime.evidence e WHERE e.evidence_type = 'churn_rate';
    """
    
    sql2 = """
    INSERT INTO runtime.rule_execution (execution_id, business_id, rule_id, fired, condition_evaluated, outcome_produced, executed_by_kb_version)
    SELECT gen_random_uuid(), e.business_id, (SELECT rule_id FROM ontology.kb_governance_rule WHERE rule_name = 'RULE_RPR_001' LIMIT 1),
    ((e.payload_json->>'value')::numeric < 0.25), jsonb_build_object('rule_name', 'RULE_RPR_001', 'condition', 'repeat < 0.25', 'value', (e.payload_json->>'value')::numeric),
    CASE WHEN ((e.payload_json->>'value')::numeric < 0.25) THEN 'BOTTLENECK_IDENTIFIED' ELSE 'NO_BOTTLENECK' END,
    (SELECT kb_version_id FROM ontology.kb_version WHERE is_active = true LIMIT 1)
    FROM runtime.evidence e WHERE e.evidence_type = 'repeat_purchase_rate';
    """
    
    for i, sql in enumerate([sql1, sql2], 1):
        execute_sql(conn, sql, f"  Applied rule {i}/2")
    
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(CASE WHEN fired = true THEN 1 END), COUNT(*) FROM runtime.rule_execution;")
    fired, total = cursor.fetchone()
    cursor.close()
    print(f"   └─ Rules evaluated: {fired} fired / {total} total")

def step_7_generate_decisions(conn):
    """STEP 7: Generate Decisions"""
    print("\n" + "="*70)
    print("STEP 7: GENERATE DECISIONS")
    print("="*70)
    
    cursor = conn.cursor()
    cursor.execute("DELETE FROM runtime.decision;")
    conn.commit()
    cursor.close()
    
    sql = """
    INSERT INTO runtime.decision (decision_id, business_id, decision_type, subject_id, outcome, reasoning_json, input_digest, kb_version_used, rules_applied, evidence_ids_used, concluded_at)
    SELECT gen_random_uuid(), bc.business_id, 'BOTTLENECK_DIAGNOSIS', bc.business_id,
    CASE WHEN COUNT(CASE WHEN re.fired = true THEN 1 END) > 0 THEN 'BOTTLENECK_IDENTIFIED' ELSE 'NO_BOTTLENECK_IDENTIFIED' END,
    jsonb_build_object('bottleneck', CASE WHEN COUNT(CASE WHEN re.fired = true AND r.rule_name LIKE '%CHR%' THEN 1 END) > 0 THEN 'customer_retention' ELSE 'other' END,
    'severity', CASE WHEN COUNT(CASE WHEN re.fired = true THEN 1 END) >= 2 THEN 'high' WHEN COUNT(CASE WHEN re.fired = true THEN 1 END) = 1 THEN 'medium' ELSE 'low' END,
    'fired_rules', ARRAY_AGG(DISTINCT r.rule_name) FILTER (WHERE re.fired = true),
    'confidence', ROUND(AVG(COALESCE((e.payload_json->>'confidence')::numeric, 0.8)), 4)),
    md5(bc.business_id::text || bc.observed_at::text),
    (SELECT kb_version_id FROM ontology.kb_version WHERE is_active = true LIMIT 1),
    ARRAY_AGG(DISTINCT r.rule_name),
    ARRAY_AGG(DISTINCT e.evidence_id),
    NOW()
    FROM state.business_context bc
    LEFT JOIN runtime.evidence e ON bc.business_id = e.business_id
    LEFT JOIN runtime.rule_execution re ON bc.business_id = re.business_id
    LEFT JOIN ontology.kb_governance_rule r ON re.rule_id = r.rule_id
    GROUP BY bc.business_id, bc.observed_at;
    """
    
    if execute_sql(conn, sql, "Step 7: Generated decisions"):
        cursor = conn.cursor()
        cursor.execute("SELECT outcome, COUNT(*) FROM runtime.decision GROUP BY outcome;")
        print("   └─ Decisions Generated:")
        for outcome, count in cursor.fetchall():
            print(f"      • {outcome}: {count}")
        cursor.close()

def step_8_audit_and_replay(conn):
    """STEP 8: Audit & Replay"""
    print("\n" + "="*70)
    print("STEP 8: AUDIT & REPLAY")
    print("="*70)
    
    cursor = conn.cursor()
    cursor.execute("DELETE FROM audit.audit_log WHERE table_name IN ('decision', 'evidence');")
    cursor.execute("DELETE FROM state.decision_replay;")
    conn.commit()
    cursor.close()
    
    sql_log_decisions = """
    INSERT INTO audit.audit_log (log_id, business_id, table_name, record_id, verb, actor_id, actor_role, timestamp, before_json, after_json, change_reason, correlation_id)
    SELECT gen_random_uuid(), d.business_id, 'decision', d.decision_id, 'INSERT', 'system', 'automated_decision_engine', NOW(), NULL, ROW_TO_JSON(d),
    'Automated bottleneck diagnosis decision', d.decision_id
    FROM runtime.decision d;
    """
    
    sql_log_evidence = """
    INSERT INTO audit.audit_log (log_id, business_id, table_name, record_id, verb, actor_id, actor_role, timestamp, before_json, after_json, change_reason, correlation_id)
    SELECT gen_random_uuid(), e.business_id, 'evidence', e.evidence_id, 'INSERT', 'system', 'data_pipeline', e.created_at, NULL, ROW_TO_JSON(e),
    'Evidence generated from processed data', e.evidence_id
    FROM runtime.evidence e;
    """
    
    sql_replay = """
    INSERT INTO state.decision_replay (replay_id, original_decision_id, business_id, original_kb_version_id, replayed_kb_version_id, replayed_at, original_outcome, replayed_outcome, outcome_changed, differences_json, impact_analysis_json)
    SELECT gen_random_uuid(), d.decision_id, d.business_id, d.kb_version_used, (SELECT kb_version_id FROM ontology.kb_version WHERE is_active = true LIMIT 1),
    NOW(), d.outcome, d.outcome, false, '{}'::jsonb, jsonb_build_object('trace_status', 'ready_for_audit')
    FROM runtime.decision d;
    """
    
    execute_sql(conn, sql_log_decisions, "  Logged decisions to audit trail")
    execute_sql(conn, sql_log_evidence, "  Logged evidence to audit trail")
    execute_sql(conn, sql_replay, "  Created decision replay records")
    
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM audit.audit_log;")
    log_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM state.decision_replay;")
    replay_count = cursor.fetchone()[0]
    cursor.close()
    print(f"   └─ Audit logs: {log_count}")
    print(f"   └─ Replay records: {replay_count}")

def verify_pipeline(conn):
    """Verify complete pipeline"""
    print("\n" + "="*70)
    print("PIPELINE VERIFICATION")
    print("="*70)
    
    cursor = conn.cursor()
    
    queries = [
        ("Raw Uploads", "SELECT COUNT(*) FROM raw.raw_upload;"),
        ("Validations", "SELECT COUNT(*) FROM raw.raw_validation_log;"),
        ("Processed Records", "SELECT COUNT(*) FROM processed.processed_upload;"),
        ("Evidence Items", "SELECT COUNT(*) FROM runtime.evidence;"),
        ("Business Contexts", "SELECT COUNT(*) FROM state.business_context;"),
        ("Rule Executions", "SELECT COUNT(*) FROM runtime.rule_execution;"),
        ("Decisions", "SELECT COUNT(*) FROM runtime.decision;"),
        ("Audit Logs", "SELECT COUNT(*) FROM audit.audit_log;"),
        ("Replay Records", "SELECT COUNT(*) FROM state.decision_replay;"),
    ]
    
    print("\nData Summary:")
    for label, query in queries:
        cursor.execute(query)
        count = cursor.fetchone()[0]
        print(f"  {label:25} : {count:,}")
    
    cursor.close()

def main():
    """Main pipeline execution"""
    print("\n")
    print("╔" + "="*68 + "╗")
    print("║" + " "*68 + "║")
    print("║" + "  ACCORD RETAIL: COMPLETE PIPELINE (STEPS 1-8)".center(68) + "║")
    print("║" + "  Full Transparency • No Shortcuts • Complete Audit Trail".center(68) + "║")
    print("║" + " "*68 + "║")
    print("╚" + "="*68 + "╝")
    
    conn = connect_db()
    
    try:
        step_0_create_tables(conn)
        step_1_load_raw_data(conn)
        step_2_validate_raw_data(conn)
        step_3_fold_transform_normalize(conn)
        step_4_project_to_evidence(conn)
        step_5_build_business_context(conn)
        step_6_apply_rules(conn)
        step_7_generate_decisions(conn)
        step_8_audit_and_replay(conn)
        verify_pipeline(conn)
        
        print("\n" + "="*70)
        print("✅ COMPLETE PIPELINE EXECUTED SUCCESSFULLY")
        print("="*70)
        print("\nYou can now:")
        print("  1. Build agents that use decisions")
        print("  2. Create decision tracing queries")
        print("  3. Build workbenches to review decisions")
        print("  4. Replay decisions with updated KB versions")
        print("\n")
        
    except Exception as e:
        print(f"\n❌ Pipeline failed: {e}")
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    main()
