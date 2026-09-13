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
        print("STEP 5: BUILD BUSINESS CONTEXT")
        print("="*70)
        cursor.execute("DELETE FROM state.business_context; DELETE FROM state.assertion;")
        sql = "INSERT INTO state.business_context (context_id, business_id, observed_at, observation_period_start, observation_period_end, context_json, generated_for_kb_version, generated_by) SELECT gen_random_uuid(), b.business_id, NOW(), CURRENT_DATE - INTERVAL '30 days', CURRENT_DATE, jsonb_build_object('business_id', b.business_id::text, 'name', b.name, 'revenue', pu.revenue_monthly, 'customers', pu.customer_count, 'churn_rate', pu.churn_rate, 'repeat_rate', pu.repeat_rate, 'margin', pu.product_margin, 'confidence', pu.confidence_score), (SELECT kb_version_id FROM ontology.kb_version WHERE is_active = true LIMIT 1), 'pipeline' FROM runtime.business b LEFT JOIN processed.processed_upload pu ON b.business_id = pu.business_id;"
        cursor.execute(sql)
        conn.commit()
        cursor.execute("SELECT COUNT(*) FROM state.business_context;")
        count = cursor.fetchone()[0]
        print(f"✅ Built {count} business contexts")
        print(f"   └─ Table: state.business_context")
        print(f"   └─ Records: {count}")
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"❌ Step 5 failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
