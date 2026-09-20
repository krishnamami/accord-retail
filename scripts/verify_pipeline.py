#!/usr/bin/env python3
"""
Independent reconciliation of the evidence pipeline for one business (read-only).

Recomputes every metric directly from runtime.sale / product / customer / inventory with plain SQL
that does NOT go through pipeline_lib, then compares against processed_upload, runtime.evidence and
state.business_context, and prints a provenance trace for product_margin.

Usage:
    python scripts/verify_pipeline.py --business-id <uuid> [--json out.json]
"""
import argparse
import json
import math
import sys

from psycopg2.extras import RealDictCursor

from pipeline_lib import KB_ASSERTED_BY, PIPELINE_ACTOR, connect, json_default, latest_complete_month, previous_month

TOL = 0.01  # rounding only


def close(a, b):
    if a is None or b is None:
        return a is None and b is None
    return math.isclose(float(a), float(b), abs_tol=TOL)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--business-id", required=True)
    ap.add_argument("--json", help="write the full comparison to this file")
    args = ap.parse_args()
    B = args.business_id
    conn = connect(options="-c default_transaction_read_only=on")
    conn.set_session(readonly=True)
    cur = conn.cursor(cursor_factory=RealDictCursor)

    def q(sql, p=()):
        cur.execute(sql, p)
        return [dict(r) for r in cur.fetchall()]

    # ---------------- independent raw calculation
    raw = q("""SELECT b.name, b.revenue_monthly AS form_revenue_monthly,
                      (SELECT COUNT(*) FROM runtime.sale WHERE business_id=b.business_id) AS sale_rows,
                      (SELECT SUM(revenue) FROM runtime.sale WHERE business_id=b.business_id) AS revenue_total,
                      (SELECT SUM(quantity) FROM runtime.sale WHERE business_id=b.business_id) AS units_sold,
                      (SELECT SUM(p.cogs*s.quantity) FROM runtime.sale s JOIN runtime.product p USING(product_id) WHERE s.business_id=b.business_id) AS cogs_total,
                      (SELECT COUNT(DISTINCT customer_id) FROM runtime.sale WHERE business_id=b.business_id) AS purchasing_customers,
                      (SELECT MIN(sale_date) FROM runtime.sale WHERE business_id=b.business_id) AS period_start,
                      (SELECT MAX(sale_date) FROM runtime.sale WHERE business_id=b.business_id) AS period_end,
                      (SELECT COUNT(*) FROM runtime.customer WHERE business_id=b.business_id) AS customers_total,
                      (SELECT COUNT(*) FROM runtime.customer WHERE business_id=b.business_id AND repeat_count>=2) AS customers_repeat_ge2,
                      (SELECT COUNT(DISTINCT last_updated) FROM runtime.inventory WHERE business_id=b.business_id) AS inventory_snapshots
               FROM runtime.business b WHERE b.business_id=%s""", (B,))[0]
    this_s, this_e = latest_complete_month(raw["period_end"])
    last_s, last_e = previous_month(this_s)
    mon = {r["m"]: r for r in q("""SELECT date_trunc('month', sale_date)::date AS m, SUM(revenue) rev, SUM(p.cogs*s.quantity) cogs, COUNT(DISTINCT customer_id) buyers
                                    FROM runtime.sale s JOIN runtime.product p USING(product_id) WHERE s.business_id=%s GROUP BY 1""", (B,))}
    chan = {r["channel"]: float(r["rev"]) for r in q("SELECT channel, SUM(revenue) rev FROM runtime.sale WHERE business_id=%s GROUP BY 1", (B,))}
    rt, ct = float(raw["revenue_total"]), float(raw["cogs_total"])
    tm, lm = mon.get(this_s, {}), mon.get(last_s, {})
    ind = {
        "revenue_total": rt, "cogs_total": ct, "gross_profit": rt - ct, "units_sold": int(raw["units_sold"]), "sale_rows": int(raw["sale_rows"]),
        "revenue_by_channel": chan,
        "revenue_monthly": float(tm["rev"]) if tm else None, "window_this_month": f"{this_s}..{this_e} (exclusive)",
        "revenue_trend": (float(tm["rev"]) - float(lm["rev"])) / float(lm["rev"]) * 100 if tm and lm else None,
        "product_margin": (rt - ct) / rt * 100,
        "margin_trend": ((float(tm["rev"]) - float(tm["cogs"])) / float(tm["rev"]) - (float(lm["rev"]) - float(lm["cogs"])) / float(lm["rev"])) * 100 if tm and lm else None,
        "churn_rate": (lm["buyers"] - tm["buyers"]) / lm["buyers"] if tm and lm else None,
        "repeat_purchase_rate": raw["customers_repeat_ge2"] / raw["customers_total"],
        "customer_lifetime_value": rt / raw["purchasing_customers"],
        "channel_mix": {k: v / rt * 100 for k, v in chan.items()},
        "customer_count": int(raw["purchasing_customers"]),
        "customer_acquisition_cost": None, "inventory_turnover": None,
    }

    # ---------------- pipeline outputs
    pu = q("""SELECT * FROM processed.processed_upload WHERE business_id=%s AND processed_by=%s ORDER BY processed_at DESC LIMIT 1""", (B, PIPELINE_ACTOR))
    pu = pu[0] if pu else {}
    ev = {r["evidence_type"]: r for r in q("""SELECT DISTINCT ON (evidence_type) evidence_id, evidence_type, state, payload_json, traced_from_upload_id, asserted_by, source_system
                                              FROM runtime.evidence WHERE business_id=%s AND about_type='business' AND asserted_by=%s
                                              ORDER BY evidence_type, observed_at DESC""", (B, KB_ASSERTED_BY))}
    ctx = q("SELECT context_id, context_json FROM state.business_context WHERE business_id=%s AND generated_by=%s ORDER BY observed_at DESC LIMIT 1", (B, PIPELINE_ACTOR))
    ctx = ctx[0] if ctx else {}
    cvals = (ctx.get("context_json") or {}).get("values", {})
    cev = (ctx.get("context_json") or {}).get("evidence", {})

    # ---------------- comparison table
    rows = []

    def row(metric, independent, processed, evidence_type=None, note=""):
        e = ev.get(evidence_type) if evidence_type else None
        e_state = e["state"] if e else "—"
        e_val = (e["payload_json"] or {}).get("value") if e else None
        c_val = cvals.get(evidence_type) if evidence_type else None
        c_state = cev.get(evidence_type, {}).get("state") if evidence_type else None
        if independent is None:
            ok = (processed is None) and (e_state in ("absent", "—")) and (c_val is None)
        else:
            ok = (processed is None or close(independent, processed)) and (e is None or close(independent, e_val)) \
                 and (evidence_type is None or (c_state != "present") or close(independent, c_val))
        rows.append({"metric": metric, "independent": independent, "processed": processed, "evidence_state": e_state,
                     "evidence_value": e_val, "evidence_id": str(e["evidence_id"]) if e else None,
                     "context_value": c_val, "status": "PASS" if ok else "FAIL", "note": note})

    row("revenue_total (period)", ind["revenue_total"], _metric(q, pu, "revenue_total", "period", "all"), note=f"{raw['period_start']}..{raw['period_end']}")
    for ch, v in sorted(chan.items()):
        row(f"revenue channel={ch}", v, _metric(q, pu, "revenue", "channel", ch))
    row("revenue_monthly", ind["revenue_monthly"], pu.get("revenue_monthly"), "revenue_monthly", note=ind["window_this_month"])
    row("revenue_trend", ind["revenue_trend"], None, "revenue_trend")
    row("cogs_total (period)", ind["cogs_total"], _metric(q, pu, "cogs_total", "period", "all"))
    row("product_margin", ind["product_margin"], pu.get("product_margin"), "product_margin", note="(revenue-cogs)/revenue*100")
    row("margin_trend", ind["margin_trend"], None, "margin_trend")
    row("churn_rate", ind["churn_rate"], pu.get("churn_rate"), "churn_rate")
    row("repeat_purchase_rate", ind["repeat_purchase_rate"], pu.get("repeat_rate"), "repeat_purchase_rate")
    row("customer_lifetime_value", ind["customer_lifetime_value"], pu.get("customer_lifetime_value"), "customer_lifetime_value")
    row("customer_count", ind["customer_count"], pu.get("customer_count"), note="no KB definition; purchasing customers in period")
    row("customer_acquisition_cost", None, pu.get("customer_acquisition_cost"), "customer_acquisition_cost", note="no source -> ABSENT")
    row("inventory_turnover", None, pu.get("inventory_turnover"), "inventory_turnover", note=f"{raw['inventory_snapshots']} snapshot(s) -> ABSENT")
    row("confidence_score (upload)", None, pu.get("confidence_score"), note="no KB upload-level definition -> NULL")

    print(f"\n{'=' * 100}\nVERIFY: {raw['name']} ({B})\n{'=' * 100}")
    print(f"{'METRIC':<30}{'INDEPENDENT (raw)':>20}{'PROCESSED':>18}{'EVIDENCE':>22}{'CONTEXT':>16}  STATUS")
    for r in rows:
        f = lambda v: "ABSENT/NULL" if v is None else (f"{v:,.4f}" if isinstance(v, float) else str(v))
        print(f"{r['metric']:<30}{f(r['independent']):>20}{f(None if r['processed'] is None else float(r['processed'])):>18}"
              f"{(r['evidence_state'] + ' ' + f(r['evidence_value'])) if r['evidence_state'] != '—' else '—':>22}{f(r['context_value']):>16}  {r['status']}  {r['note']}")
    fails = [r for r in rows if r["status"] == "FAIL"]
    print(f"\nRESULT: {'PASS' if not fails else 'FAIL'} ({len(rows) - len(fails)}/{len(rows)} checks)")

    # ---------------- evidence states & provenance
    states = {}
    for t, e in ev.items():
        states.setdefault(e["state"], []).append(t)
    print("\nEVIDENCE STATES:", {k: len(v) for k, v in states.items()})
    for k in ("present", "absent", "contradicted"):
        if k in states:
            print(f"  {k:<12}: {', '.join(sorted(states[k]))}")
    bad_prov = [t for t, e in ev.items() if not e["traced_from_upload_id"] or not (e["payload_json"] or {}).get("source_record_id")
                or e["asserted_by"] not in ("form", "shopify_api", "calculation", "user") or e["source_system"] not in ("csv", "shopify", "manual", "postgres_calc")]
    print("PROVENANCE:", "all business-level evidence carries upload_id + source_record_id + KB-enum source" if not bad_prov else f"MISSING on {bad_prov}")

    # ---------------- product_margin provenance trace
    pm = ev.get("product_margin")
    sample = q("""SELECT s.sale_id, s.product_id, s.quantity, s.revenue, p.cogs, p.cogs*s.quantity AS line_cogs
                  FROM runtime.sale s JOIN runtime.product p USING(product_id) WHERE s.business_id=%s ORDER BY s.sale_date DESC, s.sale_id LIMIT 3""", (B,))
    trace = {
        "raw": {"sale_rows": ind["sale_rows"], "sample_sales": sample, "products": q("SELECT COUNT(*) n FROM runtime.product WHERE business_id=%s", (B,))[0]["n"]},
        "transformation": {"revenue": "SUM(sale.revenue)", "cogs": "SUM(product.cogs * sale.quantity) joined 1:1 on sale.product_id",
                           "gross_profit": "revenue - cogs", "product_margin": "(revenue - cogs) / revenue * 100",
                           "values": {"revenue": rt, "cogs": ct, "gross_profit": rt - ct, "product_margin_pct": ind["product_margin"]}},
        "processed": {"processed_id": str(pu.get("processed_id")), "upload_id": str(pu.get("upload_id")), "product_margin": None if pu.get("product_margin") is None else float(pu["product_margin"])},
        "evidence": {"evidence_id": str(pm["evidence_id"]) if pm else None, "state": pm["state"] if pm else None,
                     "payload": pm["payload_json"] if pm else None, "traced_from_upload_id": str(pm["traced_from_upload_id"]) if pm else None},
        "business_context": {"context_id": str(ctx.get("context_id")), "product_margin": cvals.get("product_margin"),
                             "evidence_id_in_context": cev.get("product_margin", {}).get("evidence_id")},
    }
    print("\nPROVENANCE TRACE — product_margin")
    print(json.dumps(trace, default=json_default, indent=1))
    if args.json:
        json.dump({"business": raw["name"], "business_id": B, "independent": ind, "rows": rows, "states": states,
                   "provenance_ok": not bad_prov, "trace": trace, "data_quality_issues": pu.get("data_quality_issues")},
                  open(args.json, "w", encoding="utf-8"), default=json_default, indent=1)
    conn.rollback()
    conn.close()
    sys.exit(0 if not fails else 1)


def _metric(q, pu, metric_type, dim_type, dim_value):
    if not pu:
        return None
    r = q("SELECT value FROM processed.processed_metrics WHERE processed_id=%s AND metric_type=%s AND dimension_type=%s AND dimension_value=%s",
          (pu["processed_id"], metric_type, dim_type, dim_value))
    return float(r[0]["value"]) if r else None


if __name__ == "__main__":
    main()
