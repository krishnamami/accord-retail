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
        print("STEP 2: VALIDATE RAW DATA")
        print("="*70)
        cursor.execute("DELETE FROM raw.raw_validation_log;")
        sql = "INSERT INTO raw.raw_validation_log (upload_id, business_id, check_type, check_name, is_valid, severity) SELECT ru.upload_id, ru.business_id, 'schema', 'required_fields', (ru.raw_data_json->>'business_id') IS NOT NULL, CASE WHEN (ru.raw_data_json->>'business_id') IS NULL THEN 'error' ELSE 'info' END FROM raw.raw_upload ru;"
        cursor.execute(sql)
        cursor.execute("UPDATE raw.raw_upload SET processing_status = 'processed';")
        conn.commit()
        cursor.execute("SELECT COUNT(*) FROM raw.raw_validation_log;")
        total = cursor.fetchone()[0]
        print(f"✅ Validated {total} records")
        print(f"   └─ Table: raw.raw_validation_log")
        print(f"   └─ Records: {total}")
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"❌ Step 2 failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
