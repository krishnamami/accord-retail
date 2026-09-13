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

EVIDENCE_TYPES = [
    ("churn_rate", "churn_rate"),
    ("repeat_purchase_rate", "repeat_rate"),
    ("product_margin", "product_margin"),
    ("inventory_turnover", "inventory_turnover"),
    ("customer_lifetime_value", "customer_lifetime_value"),
]

def main():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        print("\n" + "="*70)
        print("STEP 4: PROJECT TO EVIDENCE")
        print("="*70)
        cursor.execute("DELETE FROM runtime.evidence;")
        for evidence_type, metric_column in EVIDENCE_TYPES:
            sql = f"INSERT INTO runtime.evidence (evidence_id, business_id, evidence_type, about_type, about_id, asserted_by, source_system, state, observed_at, payload_json, traced_from_upload_id) SELECT gen_random_uuid(), pu.business_id, '{evidence_type}', 'business', pu.business_id, 'pipeline', 'processed_upload', 'present', NOW(), jsonb_build_object('value', pu.{metric_column}, 'confidence', pu.confidence_score), pu.upload_id FROM processed.processed_upload pu;"
            cursor.execute(sql)
        conn.commit()
        cursor.execute("SELECT COUNT(*) FROM runtime.evidence;")
        total = cursor.fetchone()[0]
        cursor.execute("SELECT evidence_type, COUNT(*) FROM runtime.evidence GROUP BY evidence_type;")
        types = cursor.fetchall()
        print(f"✅ Projected {total} evidence items")
        print(f"   └─ Table: runtime.evidence")
        print(f"   └─ Total Records: {total}")
        print(f"   └─ Evidence Types:")
        for etype, count in types:
            print(f"      • {etype}: {count}")
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"❌ Step 4 failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
