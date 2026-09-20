#!/usr/bin/env python3
import psycopg2
import sys

import os
import sys

# Credentials are never hard-coded: DATABASE_URL comes from the environment / .env (see database/scripts/db_config.py)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'database', 'scripts'))
from db_config import connect  # noqa: E402

def main():
    try:
        conn = connect()
        cursor = conn.cursor()
        print("\n" + "="*70)
        print("STEP 6: APPLY RULES")
        print("="*70)
        cursor.execute("DELETE FROM runtime.rule_execution;")
        cursor.execute("INSERT INTO audit.scd_rule_version (rule_id, rule_version_number, rule_name, enforcement, phase, effective_date, is_active, created_by) SELECT gkr.rule_id, 1, gkr.rule_name, gkr.enforcement, gkr.phase, CURRENT_DATE, true, 'pipeline' FROM ontology.kb_governance_rule gkr WHERE NOT EXISTS (SELECT 1 FROM audit.scd_rule_version srv WHERE srv.rule_id = gkr.rule_id);")
        cursor.execute("INSERT INTO runtime.rule_execution (execution_id, business_id, decision_id, rule_id, fired, condition_evaluated, outcome_produced, executed_at, executed_by_kb_version) SELECT gen_random_uuid(), e.business_id, (SELECT decision_id FROM runtime.decision WHERE business_id = e.business_id LIMIT 1), (SELECT rule_id FROM ontology.kb_governance_rule WHERE rule_name = 'RULE_CHR_001' LIMIT 1), ((e.payload_json->>'value')::numeric > 0.30), jsonb_build_object('rule', 'CHR_001', 'condition', 'churn > 0.30'), 'IDENTIFIED', NOW(), (SELECT kb_version_id FROM ontology.kb_version WHERE is_active = true LIMIT 1) FROM runtime.evidence e WHERE e.evidence_type = 'churn_rate';")
        cursor.execute("INSERT INTO runtime.rule_execution (execution_id, business_id, decision_id, rule_id, fired, condition_evaluated, outcome_produced, executed_at, executed_by_kb_version) SELECT gen_random_uuid(), e.business_id, (SELECT decision_id FROM runtime.decision WHERE business_id = e.business_id LIMIT 1), (SELECT rule_id FROM ontology.kb_governance_rule WHERE rule_name = 'RULE_RPR_001' LIMIT 1), ((e.payload_json->>'value')::numeric < 0.25), jsonb_build_object('rule', 'RPR_001', 'condition', 'repeat < 0.25'), 'IDENTIFIED', NOW(), (SELECT kb_version_id FROM ontology.kb_version WHERE is_active = true LIMIT 1) FROM runtime.evidence e WHERE e.evidence_type = 'repeat_purchase_rate';")
        conn.commit()
        cursor.execute("SELECT COUNT(*) FROM runtime.rule_execution;")
        total = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(CASE WHEN fired = true THEN 1 END), COUNT(*) FROM runtime.rule_execution;")
        fired, eval_total = cursor.fetchone()
        print(f"✅ Applied rules: {total} executions")
        print(f"   └─ Table: runtime.rule_execution")
        print(f"   └─ Total Evaluations: {eval_total}")
        print(f"   └─ Rules Fired: {fired}")
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"❌ Step 6 failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
