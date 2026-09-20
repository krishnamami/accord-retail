#!/usr/bin/env python3
"""
STEP 1: LOAD RAW DATA

Registers one 'form' business_snapshot upload per business in raw.raw_upload, built from the
runtime.business row (the current stand-in for owner-submitted data). Idempotent per business:
only pipeline-generated uploads for the selected businesses are replaced.
"""
import sys

from pipeline_lib import PIPELINE_ACTOR, add_cli, connect, resolve_business_ids


def run(conn, business_ids):
    cur = conn.cursor()
    cur.execute("DELETE FROM raw.raw_upload WHERE uploaded_by = %s AND business_id::text = ANY(%s)", (PIPELINE_ACTOR, business_ids))
    cur.execute("""
        INSERT INTO raw.raw_upload (business_id, source_system, upload_type, raw_data_json, filename, uploaded_at, uploaded_by, processing_status)
        SELECT b.business_id, 'form', 'business_snapshot',
               jsonb_build_object('business_id', b.business_id::text, 'name', b.name, 'revenue_monthly', b.revenue_monthly, 'channels', b.channels),
               'business_' || b.business_id::text || '.json', NOW(), %s, 'pending'
        FROM runtime.business b WHERE b.business_id::text = ANY(%s)""", (PIPELINE_ACTOR, business_ids))
    inserted = cur.rowcount
    conn.commit()
    cur.close()
    return inserted


def main():
    args = add_cli().parse_args()
    print("\n" + "=" * 70 + "\nSTEP 1: LOAD RAW DATA\n" + "=" * 70)
    try:
        conn = connect()
        ids = resolve_business_ids(conn, args.business_id)
        n = run(conn, ids)
        print(f"✅ Loaded {n} raw uploads for {len(ids)} business(es)\n   └─ Table: raw.raw_upload")
        conn.close()
    except Exception as e:
        print(f"❌ Step 1 failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
