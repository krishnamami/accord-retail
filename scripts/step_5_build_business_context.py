#!/usr/bin/env python3
"""
STEP 5: BUILD BUSINESS CONTEXT

Composes state.business_context from the latest business-level evidence rows (not from
processed_upload directly), so every number in the context carries its evidence_id, state and
confidence. Absent and contradicted evidence is listed explicitly so downstream decisions can
return CANNOT_DECIDE instead of reading a fabricated value.

state.assertion is not written: the assertion layer is not implemented and nothing is invented here.
"""
import sys

from psycopg2.extras import RealDictCursor

from pipeline_lib import PIPELINE_ACTOR, KB_ASSERTED_BY, active_kb_version_id, add_cli, connect, dumps, resolve_business_ids


def run(conn, business_ids):
    kb_version_id = active_kb_version_id(conn)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("DELETE FROM state.business_context WHERE generated_by = %s AND business_id::text = ANY(%s)", (PIPELINE_ACTOR, business_ids))
    built = 0
    for business_id in business_ids:
        cur.execute("""SELECT processed_id, upload_id, observation_period_start, observation_period_end, data_quality_issues,
                              channel_mix_json FROM processed.processed_upload
                       WHERE processed_by = %s AND business_id = %s ORDER BY processed_at DESC LIMIT 1""", (PIPELINE_ACTOR, business_id))
        pu = cur.fetchone()
        if not pu:
            print(f"   ⚠️  {business_id}: no processed_upload; skipped")
            continue
        # latest business-level evidence per type, traced to this processed row
        cur.execute("""SELECT DISTINCT ON (evidence_type) evidence_id, evidence_type, state, payload_json, observed_at
                       FROM runtime.evidence
                       WHERE business_id = %s AND about_type = 'business' AND asserted_by = %s
                         AND payload_json->>'source_record_id' = %s
                       ORDER BY evidence_type, observed_at DESC""", (business_id, KB_ASSERTED_BY, str(pu["processed_id"])))
        rows = cur.fetchall()
        if not rows:
            print(f"   ⚠️  {business_id}: no evidence for processed_id {pu['processed_id']}; skipped")
            continue
        cur.execute("SELECT name FROM runtime.business WHERE business_id = %s", (business_id,))
        name = cur.fetchone()["name"]
        evidence = {}
        for r in rows:
            p = r["payload_json"]
            evidence[r["evidence_type"]] = {"evidence_id": str(r["evidence_id"]), "state": r["state"], "value": p.get("value"),
                                            "unit": p.get("unit"), "confidence_0_to_1": p.get("confidence_0_to_1"),
                                            "observed_at": r["observed_at"]}
        context = {
            "business_id": business_id, "name": name,
            "observation_period": {"start": pu["observation_period_start"], "end": pu["observation_period_end"]},
            "this_month": (pu["channel_mix_json"] or {}).get("this_month"),
            "source": {"processed_id": str(pu["processed_id"]), "upload_id": str(pu["upload_id"]) if pu["upload_id"] else None},
            "values": {t: e["value"] for t, e in evidence.items() if e["state"] == "present"},
            "evidence": evidence,
            "present": sorted(t for t, e in evidence.items() if e["state"] == "present"),
            "absent": sorted(t for t, e in evidence.items() if e["state"] == "absent"),
            "contradicted": sorted(t for t, e in evidence.items() if e["state"] == "contradicted"),
            "data_quality_issues": pu["data_quality_issues"] or [],
        }
        cur.execute("""INSERT INTO state.business_context (business_id, observed_at, observation_period_start, observation_period_end,
                                                            active_assertions, context_json, generated_for_kb_version, generated_by)
                       VALUES (%s, NOW(), %s, %s, NULL, %s::jsonb, %s, %s) RETURNING context_id""",
                    (business_id, pu["observation_period_start"], pu["observation_period_end"], dumps(context), kb_version_id, PIPELINE_ACTOR))
        ctx_id = cur.fetchone()["context_id"]
        built += 1
        print(f"   {name:<24} context {ctx_id} present={len(context['present'])} absent={len(context['absent'])} contradicted={len(context['contradicted'])}")
    conn.commit()
    cur.close()
    return built


def main():
    args = add_cli().parse_args()
    print("\n" + "=" * 70 + "\nSTEP 5: BUILD BUSINESS CONTEXT\n" + "=" * 70)
    try:
        conn = connect()
        ids = resolve_business_ids(conn, args.business_id)
        n = run(conn, ids)
        print(f"✅ Built {n} business contexts\n   └─ Table: state.business_context")
        conn.close()
    except Exception as e:
        print(f"❌ Step 5 failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
