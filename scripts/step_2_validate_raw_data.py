#!/usr/bin/env python3
"""
STEP 2: VALIDATE RAW DATA

Runs schema and referential checks for each pending pipeline upload and records every check in
raw.raw_validation_log. An upload with any 'error' check is marked 'failed' and is not processed
further; warnings are recorded and carried into processed.data_quality_issues by step 3.
"""
import sys

from psycopg2.extras import RealDictCursor

from pipeline_lib import PIPELINE_ACTOR, add_cli, connect, resolve_business_ids

CHECKS = [
    # (check_type, check_name, severity_if_failed, sql returning one row {ok bool, detail text})
    ("schema", "required_fields", "error",
     """SELECT (u.raw_data_json ? 'business_id') AND (u.raw_data_json ? 'name') AS ok,
               'raw_data_json keys: ' || (SELECT string_agg(k, ',') FROM jsonb_object_keys(u.raw_data_json) k) AS detail
        FROM raw.raw_upload u WHERE u.upload_id = %(upload_id)s"""),
    ("referential", "business_exists", "error",
     """SELECT EXISTS (SELECT 1 FROM runtime.business WHERE business_id = %(business_id)s) AS ok, NULL AS detail"""),
    ("completeness", "sales_present", "error",
     """SELECT COUNT(*) > 0 AS ok, COUNT(*) || ' sale rows' AS detail FROM runtime.sale WHERE business_id = %(business_id)s"""),
    ("referential", "sales_have_product", "warning",
     """SELECT COUNT(*) FILTER (WHERE product_id IS NULL) = 0 AS ok,
               COUNT(*) FILTER (WHERE product_id IS NULL) || ' sales without product_id' AS detail
        FROM runtime.sale WHERE business_id = %(business_id)s"""),
    ("referential", "sale_products_belong_to_business", "error",
     """SELECT COUNT(*) = 0 AS ok, COUNT(*) || ' sales reference a product of another business' AS detail
        FROM runtime.sale s JOIN runtime.product p ON p.product_id = s.product_id
        WHERE s.business_id = %(business_id)s AND p.business_id <> s.business_id"""),
    ("completeness", "products_have_cogs", "warning",
     """SELECT COUNT(*) FILTER (WHERE cogs IS NULL OR cogs <= 0) = 0 AS ok,
               COUNT(*) FILTER (WHERE cogs IS NULL OR cogs <= 0) || ' products without positive cogs' AS detail
        FROM runtime.product WHERE business_id = %(business_id)s"""),
    ("range", "sale_values_nonnegative", "error",
     """SELECT COUNT(*) FILTER (WHERE revenue < 0 OR quantity <= 0) = 0 AS ok,
               COUNT(*) FILTER (WHERE revenue < 0 OR quantity <= 0) || ' sales with negative revenue or non-positive quantity' AS detail
        FROM runtime.sale WHERE business_id = %(business_id)s"""),
    ("consistency", "revenue_scales_with_quantity", "warning",
     """SELECT COALESCE(corr(revenue, quantity), 0) >= 0.1 AS ok,
               'corr(revenue, quantity) = ' || ROUND(COALESCE(corr(revenue, quantity), 0)::numeric, 3) AS detail
        FROM runtime.sale WHERE business_id = %(business_id)s"""),
    ("consistency", "cogs_not_exceeding_revenue", "warning",
     """SELECT SUM(p.cogs * s.quantity) <= SUM(s.revenue) AS ok,
               'revenue=' || ROUND(SUM(s.revenue), 2) || ' cogs=' || ROUND(SUM(p.cogs * s.quantity), 2) AS detail
        FROM runtime.sale s JOIN runtime.product p ON p.product_id = s.product_id WHERE s.business_id = %(business_id)s"""),
    ("consistency", "customer_repeat_count_backed_by_sales", "warning",
     """SELECT COUNT(*) = 0 AS ok, COUNT(*) || ' customers with repeat_count > 0 and no sales' AS detail
        FROM runtime.customer c WHERE c.business_id = %(business_id)s AND c.repeat_count > 0
          AND NOT EXISTS (SELECT 1 FROM runtime.sale s WHERE s.customer_id = c.customer_id)"""),
]


def run(conn, business_ids):
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""SELECT upload_id, business_id FROM raw.raw_upload
                   WHERE uploaded_by = %s AND business_id::text = ANY(%s) ORDER BY uploaded_at DESC""", (PIPELINE_ACTOR, business_ids))
    uploads = cur.fetchall()
    cur.execute("DELETE FROM raw.raw_validation_log WHERE upload_id = ANY(%s::uuid[])", ([str(u["upload_id"]) for u in uploads],))
    totals = {"checks": 0, "errors": 0, "warnings": 0}
    for u in uploads:
        params = {"upload_id": str(u["upload_id"]), "business_id": str(u["business_id"])}
        failed = False
        for check_type, name, severity, sql in CHECKS:
            cur.execute(sql, params)
            r = cur.fetchone()
            ok = bool(r["ok"])
            sev = "info" if ok else severity
            cur.execute("""INSERT INTO raw.raw_validation_log (upload_id, business_id, check_type, check_name, is_valid, error_message, warning_message, severity, checked_by)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                        (params["upload_id"], params["business_id"], check_type, name, ok,
                         r["detail"] if (not ok and severity == "error") else None,
                         r["detail"] if (not ok and severity == "warning") else None, sev, PIPELINE_ACTOR))
            totals["checks"] += 1
            if not ok and severity == "error":
                failed = True
                totals["errors"] += 1
            elif not ok:
                totals["warnings"] += 1
        cur.execute("UPDATE raw.raw_upload SET processing_status = %s, error_message = %s WHERE upload_id = %s",
                    ("failed" if failed else "processed", "validation errors, see raw.raw_validation_log" if failed else None, params["upload_id"]))
    conn.commit()
    cur.close()
    return len(uploads), totals


def main():
    args = add_cli().parse_args()
    print("\n" + "=" * 70 + "\nSTEP 2: VALIDATE RAW DATA\n" + "=" * 70)
    try:
        conn = connect()
        ids = resolve_business_ids(conn, args.business_id)
        n, t = run(conn, ids)
        print(f"✅ Validated {n} uploads: {t['checks']} checks, {t['errors']} errors, {t['warnings']} warnings\n   └─ Table: raw.raw_validation_log")
        conn.close()
    except Exception as e:
        print(f"❌ Step 2 failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
