#!/usr/bin/env python3
"""
STEP 4: PROJECT TO EVIDENCE

Projects every KB evidence type (ontology.kb_evidence_type) into runtime.evidence for each business:
  present       - derivable from runtime.* with the KB formula
  absent        - required source or formula does not exist (value is NULL, reason recorded)
  contradicted  - two sources disagree (G-03), currently revenue_monthly: form vs SUM(sales)

Values are recomputed from runtime.* (pipeline_lib.compute_metrics) and cross-checked against the
processed_upload row they are traced to. asserted_by / source_system use the KB enums
('calculation' / 'postgres_calc'); payload follows {value, unit, confidence_0_to_1, source_record_id}.
"""
import math
import sys

from psycopg2.extras import RealDictCursor

from pipeline_lib import (PIPELINE_ACTOR, KB_ASSERTED_BY, add_cli, compute_metrics, connect, derive_evidence, dumps,
                          load_kb_evidence_types, resolve_business_ids)


def _close(a, b, tol=0.005):
    return a is None and b is None or (a is not None and b is not None and math.isclose(float(a), float(b), abs_tol=tol))


def run(conn, business_ids):
    kb = load_kb_evidence_types(conn)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    # replace the pipeline's own evidence for these businesses (legacy rows used asserted_by='pipeline')
    cur.execute("DELETE FROM runtime.evidence WHERE business_id::text = ANY(%s) AND asserted_by IN (%s, %s)",
                (business_ids, KB_ASSERTED_BY, PIPELINE_ACTOR))
    counts = {"present": 0, "absent": 0, "contradicted": 0}
    for business_id in business_ids:
        cur.execute("""SELECT processed_id, upload_id, revenue_monthly, product_margin, churn_rate, repeat_rate
                       FROM processed.processed_upload WHERE processed_by = %s AND business_id = %s
                       ORDER BY processed_at DESC LIMIT 1""", (PIPELINE_ACTOR, business_id))
        pu = cur.fetchone()
        if not pu:
            print(f"   ⚠️  {business_id}: no processed_upload row; skipped")
            continue
        m = compute_metrics(conn, business_id)
        # evidence must agree with the processed layer it is traced to
        for col, key in (("revenue_monthly", "revenue_monthly"), ("product_margin", "product_margin"),
                         ("churn_rate", "churn_rate"), ("repeat_rate", "repeat_purchase_rate")):
            if not _close(pu[col], m.get(key)):
                raise RuntimeError(f"{business_id}: {col} processed={pu[col]} recomputed={m.get(key)}; rerun step 3")
        records = derive_evidence(m, kb, pu["processed_id"], pu["upload_id"])
        cur.executemany("""INSERT INTO runtime.evidence (business_id, evidence_type, about_type, about_id, asserted_by, source_system,
                                                         state, observed_at, payload_json, traced_from_upload_id)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), %s::jsonb, %s)""",
                        [(r["business_id"], r["evidence_type"], r["about_type"], r["about_id"], r["asserted_by"], r["source_system"],
                          r["state"], dumps(r["payload_json"]), r["traced_from_upload_id"]) for r in records])
        for r in records:
            counts[r["state"]] += 1
        biz = [r for r in records if r["about_type"] == "business"]
        print(f"   {m['business_name']:<24} {len(records)} rows "
              f"(business-level: {sum(r['state']=='present' for r in biz)} present, {sum(r['state']=='absent' for r in biz)} absent, "
              f"{sum(r['state']=='contradicted' for r in biz)} contradicted)")
    conn.commit()
    cur.execute("REFRESH MATERIALIZED VIEW runtime.evidence_latest")
    conn.commit()
    cur.close()
    return counts


def main():
    args = add_cli().parse_args()
    print("\n" + "=" * 70 + "\nSTEP 4: PROJECT TO EVIDENCE\n" + "=" * 70)
    try:
        conn = connect()
        ids = resolve_business_ids(conn, args.business_id)
        c = run(conn, ids)
        print(f"✅ Projected evidence: {c['present']} present, {c['absent']} absent, {c['contradicted']} contradicted"
              f"\n   └─ Table: runtime.evidence (materialized view runtime.evidence_latest refreshed)")
        conn.close()
    except Exception as e:
        print(f"❌ Step 4 failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
