#!/usr/bin/env python3
"""
STEP 3: FOLD, TRANSFORM & NORMALIZE

Computes derived metrics per business at the correct grain (see pipeline_lib.compute_metrics)
and writes one processed.processed_upload row plus dimensional rows in processed.processed_metrics.

Fix history: the previous version LEFT JOINed runtime.inventory on business_id only, which
multiplied every sale row by the number of inventory rows (x50). Sales and inventory are now
aggregated separately and only meet at the product grain.

Columns with no KB definition are NOT populated with invented values:
  customer_acquisition_cost -> NULL (no marketing-spend source)
  inventory_turnover        -> NULL (single inventory snapshot; average inventory value not derivable)
  confidence_score          -> NULL (KB defines confidence per evidence type, not per upload)
"""
import sys

from psycopg2.extras import RealDictCursor

from pipeline_lib import PIPELINE_ACTOR, add_cli, compute_metrics, connect, dumps, resolve_business_ids, validate_confidence


def run(conn, business_ids):
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("DELETE FROM processed.processed_upload WHERE processed_by = %s AND business_id::text = ANY(%s)", (PIPELINE_ACTOR, business_ids))
    written = 0
    for business_id in business_ids:
        cur.execute("""SELECT upload_id, processing_status FROM raw.raw_upload WHERE uploaded_by = %s AND business_id = %s
                       ORDER BY uploaded_at DESC LIMIT 1""", (PIPELINE_ACTOR, business_id))
        up = cur.fetchone()
        if not up or up["processing_status"] != "processed":
            print(f"   ⚠️  {business_id}: no validated upload (status={up['processing_status'] if up else 'none'}); skipped")
            continue
        m = compute_metrics(conn, business_id)
        if not m.get("sale_rows"):
            print(f"   ⚠️  {business_id}: no sales; skipped")
            continue
        # carry validation warnings into data_quality_issues
        cur.execute("""SELECT check_name || ': ' || warning_message AS issue FROM raw.raw_validation_log
                       WHERE upload_id = %s AND severity = 'warning' ORDER BY check_name""", (up["upload_id"],))
        issues = sorted(set(m["data_quality_issues"] + [r["issue"] for r in cur.fetchall()]))
        confidence_score = validate_confidence(None)  # no upload-level confidence definition in the KB

        cur.execute("""
            INSERT INTO processed.processed_upload (
                business_id, upload_id, revenue_monthly, customer_count, repeat_count, churn_count, repeat_rate, churn_rate,
                customer_lifetime_value, customer_acquisition_cost, product_margin, inventory_turnover, slow_moving_inventory_pct,
                channel_mix_json, data_quality_issues, confidence_score, processed_at, processed_by,
                observation_period_start, observation_period_end)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, NOW(), %s, %s, %s)
            RETURNING processed_id""",
            (business_id, up["upload_id"], m["revenue_monthly"], m["customer_count"], m["customers_repeat_ge2"],
             None if m["churn_rate"] is None else int(m["customers_last_month"] - m["customers_this_month"]),
             m["repeat_purchase_rate"], m["churn_rate"], m["customer_lifetime_value"],
             None,                       # customer_acquisition_cost: no source -> NULL
             m["product_margin"],        # percentage per KB: (revenue - cogs) / revenue * 100
             None,                       # inventory_turnover: not derivable -> NULL
             m["slow_moving_inventory_pct"],
             dumps({"pct_by_channel": m["channel_mix"], "revenue_by_channel": m["revenue_by_channel"],
                    "this_month": str(m["this_month"]["start"]), "last_month": str(m["last_month"]["start"])}),
             issues, confidence_score, PIPELINE_ACTOR, m["period_start"], m["period_end"]))
        processed_id = cur.fetchone()["processed_id"]

        # dimensional metrics (product / channel / month grain) with their periods
        rows = []
        ps, pe = m["period_start"], m["period_end"]
        rows.append(("revenue_total", "period", "all", m["revenue_total"], "USD", ps, pe))
        rows.append(("cogs_total", "period", "all", m["cogs_total"], "USD", ps, pe))
        rows.append(("units_sold", "period", "all", m["units_sold"], "units", ps, pe))
        rows.append(("purchasing_customers", "period", "all", m["purchasing_customers"], "customers", ps, pe))
        for ch, rev in m["revenue_by_channel"].items():
            rows.append(("revenue", "channel", ch, rev, "USD", ps, pe))
        for mo, d in m["monthly"].items():
            rows.append(("revenue", "month", mo.strftime("%Y-%m"), d["revenue"], "USD", mo, None))
            rows.append(("cogs", "month", mo.strftime("%Y-%m"), d["cogs"], "USD", mo, None))
            rows.append(("purchasing_customers", "month", mo.strftime("%Y-%m"), d["purchasing_customers"], "customers", mo, None))
        for p in m["products"]:
            rows.append(("revenue", "product", p["product_id"], p["revenue"], "USD", ps, pe))
            rows.append(("cogs", "product", p["product_id"], p["cogs_total"], "USD", ps, pe))
            rows.append(("units_sold", "product", p["product_id"], p["units"], "units", ps, pe))
            if p["product_margin"] is not None:
                rows.append(("product_margin", "product", p["product_id"], p["product_margin"], "percentage", ps, pe))
            rows.append(("product_revenue_pct", "product", p["product_id"], p["product_revenue_pct"], "percentage", ps, pe))
        cur.executemany("""INSERT INTO processed.processed_metrics (processed_id, business_id, metric_type, dimension_type, dimension_value, value, unit, period_start, period_end)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                        [(processed_id, business_id, *r) for r in rows])
        written += 1
        print(f"   {m['business_name']:<24} revenue_total={m['revenue_total']:,.2f} revenue_{m['this_month']['start']:%Y-%m}={m['revenue_monthly']:,.2f} "
              f"margin={m['product_margin']:.2f}% churn={m['churn_rate']:.4f} repeat={m['repeat_purchase_rate']:.4f} issues={len(issues)}")
    conn.commit()
    cur.close()
    return written


def main():
    args = add_cli().parse_args()
    print("\n" + "=" * 70 + "\nSTEP 3: FOLD, TRANSFORM & NORMALIZE\n" + "=" * 70)
    try:
        conn = connect()
        ids = resolve_business_ids(conn, args.business_id)
        n = run(conn, ids)
        print(f"✅ Transformed {n} business records\n   └─ Tables: processed.processed_upload, processed.processed_metrics")
        conn.close()
    except Exception as e:
        print(f"❌ Step 3 failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
