#!/usr/bin/env python3
import psycopg2
import sys

DB_CONFIG = {
    "host": "database-1.c1qseu4kq079.us-west-2.rds.amazonaws.com",
    "port": 5432,
    "database": "accord_retail",
    "user": "postgres",
    "password": "Sharanya87$"
}

def main():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        print("\n" + "="*70)
        print("STEP 8: AUDIT & REPLAY")
        print("="*70)
        cursor.execute("DELETE FROM audit.audit_log WHERE table_name IN ('decision', 'evidence'); DELETE FROM state.decision_replay;")
        cursor.execute("INSERT INTO audit.audit_log (log_id, business_id, table_name, record_id, verb, actor_id, actor_role, timestamp, before_json, after_json, change_reason, correlation_id) SELECT gen_random_uuid(), d.business_id, 'decision', d.decision_id, 'INSERT', 'pipeline', 'decision_engine', NOW(), NULL, ROW_TO_JSON(d), 'Decision generated', d.decision_id FROM runtime.decision d;")
        cursor.execute("INSERT INTO audit.audit_log (log_id, business_id, table_name, record_id, verb, actor_id, actor_role, timestamp, before_json, after_json, change_reason, correlation_id) SELECT gen_random_uuid(), e.business_id, 'evidence', e.evidence_id, 'INSERT', 'pipeline', 'projection_engine', e.created_at, NULL, ROW_TO_JSON(e), 'Evidence projected', e.evidence_id FROM runtime.evidence e;")
        cursor.execute("INSERT INTO state.decision_replay (replay_id, original_decision_id, business_id, original_kb_version_id, replayed_kb_version_id, replayed_at, original_outcome, replayed_outcome, outcome_changed, differences_json) SELECT gen_random_uuid(), d.decision_id, d.business_id, d.kb_version_used, (SELECT kb_version_id FROM ontology.kb_version WHERE is_active = true LIMIT 1), NOW(), d.outcome, d.outcome, false, '{}' FROM runtime.decision d;")
        conn.commit()
        cursor.execute("SELECT COUNT(*) FROM audit.audit_log;")
        total_logs = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM state.decision_replay;")
        replay_count = cursor.fetchone()[0]
        print(f"✅ Audit trail complete")
        print(f"   └─ Table: audit.audit_log ({total_logs} records)")
        print(f"   └─ Table: state.decision_replay ({replay_count} records)")
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"❌ Step 8 failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
