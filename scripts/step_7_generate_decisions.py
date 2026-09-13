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
        print("STEP 7: GENERATE DECISIONS")
        print("="*70)
        cursor.execute("DELETE FROM runtime.decision;")
        sql = "INSERT INTO runtime.decision (decision_id, business_id, decision_type, subject_id, outcome, reasoning_json, input_digest, kb_version_used, concluded_at) SELECT gen_random_uuid(), bc.business_id, 'BOTTLENECK_DIAGNOSIS', bc.business_id, 'IDENTIFIED', jsonb_build_object('context_id', bc.context_id::text, 'business_snapshot', bc.context_json), md5(bc.business_id::text || bc.observed_at::text), (SELECT kb_version_id FROM ontology.kb_version WHERE is_active = true LIMIT 1), NOW() FROM state.business_context bc;"
        cursor.execute(sql)
        conn.commit()
        cursor.execute("SELECT COUNT(*) FROM runtime.decision;")
        count = cursor.fetchone()[0]
        print(f"✅ Generated {count} decisions")
        print(f"   └─ Table: runtime.decision")
        print(f"   └─ Total Records: {count}")
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"❌ Step 7 failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
