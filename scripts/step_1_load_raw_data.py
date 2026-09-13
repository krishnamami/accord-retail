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
        print("STEP 1: LOAD RAW DATA")
        print("="*70)
        cursor.execute("DELETE FROM raw.raw_upload;")
        sql = "INSERT INTO raw.raw_upload (business_id, source_system, upload_type, raw_data_json, filename, uploaded_at, uploaded_by, processing_status) SELECT b.business_id, 'form', 'business_snapshot', jsonb_build_object('business_id', b.business_id::text, 'name', b.name, 'revenue_monthly', b.revenue_monthly, 'channels', b.channels), 'business_' || b.business_id::text || '.json', NOW(), 'pipeline', 'pending' FROM runtime.business b;"
        cursor.execute(sql)
        conn.commit()
        cursor.execute("SELECT COUNT(*) FROM raw.raw_upload;")
        count = cursor.fetchone()[0]
        print(f"✅ Loaded {count} raw uploads")
        print(f"   └─ Table: raw.raw_upload")
        print(f"   └─ Records: {count}")
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"❌ Step 1 failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
