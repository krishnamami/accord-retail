#!/usr/bin/env python3
"""
Shared logic for pipeline steps 1-5 (RAW -> VALIDATE -> TRANSFORM -> EVIDENCE -> CONTEXT).

Design rules enforced here:
  * Every metric is computed at its correct relational grain. Sales are never joined
    to inventory (there is no sale<->inventory relationship; both hang off product).
  * Formulas come from the KB (ontology.kb_evidence_type.calculation). No new definitions.
  * Missing inputs produce evidence with state='absent', never a fabricated number.
  * Confidence is 0.0-1.0 and only set where the KB defines confidence_factors.
  * Every evidence payload follows the KB contract:
        {value, unit, confidence_0_to_1, source_record_id, ...provenance}

Time windows (documented because the KB names "this month"/"last month" without
fixing them): the observation period is [first sale_date, last sale_date] for the
business; "this month" is the latest COMPLETE calendar month inside that period;
"last month" is the month before it.
"""
import argparse
import calendar
import datetime as dt
import decimal
import json
import os
import sys
from typing import Any

from psycopg2.extras import RealDictCursor

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "database", "scripts"))
from db_config import connect  # noqa: E402

PIPELINE_ACTOR = "pipeline"          # processed_by / uploaded_by / generated_by
KB_ASSERTED_BY = "calculation"       # KB Evidence.asserted_by enum value for derived evidence
KB_SOURCE_SYSTEM = "postgres_calc"   # KB Evidence.source_system enum value for derived evidence

# Evidence types the pipeline can legitimately derive from runtime.* tables today.
DERIVABLE_TYPES = [
    "revenue_monthly", "revenue_trend", "revenue_concentration", "channel_mix",
    "churn_rate", "repeat_purchase_rate", "customer_lifetime_value",
    "product_margin", "product_revenue_pct", "margin_trend", "slow_moving_inventory_pct",
]
# KB types whose grain is the product ("per product"), never aggregated to the business.
PRODUCT_GRAIN_ONLY_TYPES = {"product_revenue_pct"}
# KB types with no source in the current schema (form / manual / user supplied) or no usable formula.
ABSENT_REASONS = {
    "customer_acquisition_cost": ("MISSING_SOURCE", ["marketing_spend", "new_customers_acquired"],
                                  "No marketing-spend or acquisition-spend data exists in any table; KB source is form/csv/manual."),
    "ltv_to_cac_ratio": ("MISSING_SOURCE", ["customer_acquisition_cost"],
                         "Depends on customer_acquisition_cost, which is absent."),
    "inventory_turnover": ("MISSING_SOURCE", ["avg_inventory_value"],
                           "KB formula is cogs_annual / avg_inventory_value. runtime.inventory holds a single snapshot "
                           "(one last_updated timestamp), so an average inventory value over the period cannot be derived."),
    "customer_cohort_retention": ("MISSING_FORMULA", ["cohort definition"],
                                  "KB calculation is a shape ({email, organic, paid_ads, referral}) not a formula, and the "
                                  "data's acquisition_channel values (online, retail) do not match those cohorts."),
    "stockout_frequency": ("MISSING_SOURCE", ["stockout events"], "Owner-supplied via form; no source table."),
    "cart_abandonment_rate": ("MISSING_SOURCE", ["abandoned_carts", "initiated_checkouts"], "Owner-supplied via form; no source table."),
    "competitor_price_comparison": ("MISSING_SOURCE", ["competitor prices"], "User-supplied; no source table."),
    "industry_churn_benchmark": ("MISSING_SOURCE", ["industry benchmark"], "Form-supplied; no source table."),
    "industry_margin_benchmark": ("MISSING_SOURCE", ["industry benchmark"], "Form-supplied; no source table."),
}
# Tolerance for two sources of the same evidence to be considered in agreement (relative).
CONTRADICTION_TOLERANCE = 0.01
SLOW_MOVING_DAYS = 90            # from the KB calculation text: days_since_last_sold > 90
INVENTORY_VALUATION_BASIS = "cogs"  # inventory carried at cost; stated in the payload


# --------------------------------------------------------------------------- helpers
def num(x):
    """Decimal/None -> float/None for JSON and arithmetic."""
    if x is None:
        return None
    if isinstance(x, decimal.Decimal):
        return float(x)
    return x


def validate_confidence(value):
    """KB scale is 0.0-1.0. None is allowed (KB defines no confidence factor for the type)."""
    if value is None:
        return None
    v = float(value)
    if not (0.0 <= v <= 1.0):
        raise ValueError(f"confidence {v} outside KB scale [0.0, 1.0]")
    return round(v, 2)


def month_bounds(d: dt.date):
    start = d.replace(day=1)
    end = (start + dt.timedelta(days=32)).replace(day=1)  # exclusive
    return start, end


def latest_complete_month(last_sale: dt.date):
    """Latest calendar month whose last day <= last_sale."""
    last_day = calendar.monthrange(last_sale.year, last_sale.month)[1]
    if last_sale.day == last_day:
        return month_bounds(last_sale)
    prev = last_sale.replace(day=1) - dt.timedelta(days=1)
    return month_bounds(prev)


def previous_month(month_start: dt.date):
    return month_bounds(month_start - dt.timedelta(days=1))


def add_cli(parser: argparse.ArgumentParser | None = None) -> argparse.ArgumentParser:
    parser = parser or argparse.ArgumentParser()
    parser.add_argument("--business-id", action="append", default=None,
                        help="Restrict to this business_id (repeatable). Default: all businesses.")
    return parser


def resolve_business_ids(conn, requested):
    cur = conn.cursor()
    if requested:
        cur.execute("SELECT business_id::text FROM runtime.business WHERE business_id::text = ANY(%s) ORDER BY name", (requested,))
    else:
        cur.execute("SELECT business_id::text FROM runtime.business ORDER BY name")
    ids = [r[0] for r in cur.fetchall()]
    cur.close()
    if requested and len(ids) != len(set(requested)):
        missing = set(requested) - set(ids)
        raise SystemExit(f"Unknown business_id(s): {sorted(missing)}")
    return ids


def load_kb_evidence_types(conn) -> dict:
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""SELECT name, category, unit, calculation, confidence_factors, role_in_diagnosis, asserted_by, source_system
                   FROM ontology.kb_evidence_type""")
    rows = {r["name"]: dict(r) for r in cur.fetchall()}
    cur.close()
    return rows


def active_kb_version_id(conn):
    cur = conn.cursor()
    cur.execute("SELECT kb_version_id FROM ontology.kb_version WHERE is_active = true ORDER BY released_at DESC LIMIT 1")
    row = cur.fetchone()
    cur.close()
    return row[0] if row else None


# --------------------------------------------------------------------------- metrics
def compute_metrics(conn, business_id: str) -> dict[str, Any]:
    """
    All derived metrics for one business, each at its own grain, from runtime.* only.
    Returns plain Python values (floats/ints/dates) so callers can persist or test them.
    """
    cur = conn.cursor(cursor_factory=RealDictCursor)
    m: dict[str, Any] = {"business_id": business_id, "data_quality_issues": []}

    cur.execute("SELECT name, revenue_monthly FROM runtime.business WHERE business_id = %s", (business_id,))
    biz = cur.fetchone()
    m["business_name"] = biz["name"]
    m["form_revenue_monthly"] = num(biz["revenue_monthly"])

    # ---- sales grain: one row per sale, product joined 1:1 on product_id (sale.product_id -> product.product_id)
    cur.execute("""
        SELECT COUNT(*)                          AS sale_rows,
               COUNT(*) FILTER (WHERE s.product_id IS NULL) AS sales_without_product,
               COALESCE(SUM(s.quantity), 0)     AS units_sold,
               COALESCE(SUM(s.revenue), 0)      AS revenue_total,
               COALESCE(SUM(p.cogs * s.quantity), 0) AS cogs_total,
               COUNT(DISTINCT s.customer_id)    AS purchasing_customers,
               MIN(s.sale_date)                 AS period_start,
               MAX(s.sale_date)                 AS period_end
        FROM runtime.sale s
        LEFT JOIN runtime.product p ON p.product_id = s.product_id
        WHERE s.business_id = %s""", (business_id,))
    r = cur.fetchone()
    m.update({k: num(v) for k, v in r.items()})
    if not m["sale_rows"]:
        m["data_quality_issues"].append("no_sales")
        cur.close()
        return m
    if m["sales_without_product"]:
        m["data_quality_issues"].append(f"{m['sales_without_product']} sales have no product_id; their COGS is unknown")

    # ---- monthly series (sales grain, grouped by calendar month)
    cur.execute("""
        SELECT date_trunc('month', s.sale_date)::date AS month_start,
               COUNT(*) AS sale_rows, SUM(s.revenue) AS revenue, SUM(p.cogs * s.quantity) AS cogs,
               COUNT(DISTINCT s.customer_id) AS purchasing_customers
        FROM runtime.sale s LEFT JOIN runtime.product p ON p.product_id = s.product_id
        WHERE s.business_id = %s GROUP BY 1 ORDER BY 1""", (business_id,))
    monthly = {row["month_start"]: {k: num(v) for k, v in row.items()} for row in cur.fetchall()}
    m["monthly"] = monthly

    this_start, this_end = latest_complete_month(m["period_end"])
    last_start, last_end = previous_month(this_start)
    m["this_month"] = {"start": this_start, "end_exclusive": this_end, "complete": this_start >= m["period_start"]}
    m["last_month"] = {"start": last_start, "end_exclusive": last_end, "complete": last_start >= m["period_start"]}
    tm = monthly.get(this_start, {})
    lm = monthly.get(last_start, {})

    # revenue_monthly = SUM(sales.revenue) WHERE sale_date >= month_start AND sale_date < month_end
    m["revenue_monthly"] = tm.get("revenue")
    m["revenue_last_month"] = lm.get("revenue")
    # revenue_trend = (revenue_this_month - revenue_last_month) / revenue_last_month * 100
    m["revenue_trend"] = (None if not m["revenue_last_month"] or m["revenue_monthly"] is None
                          else (m["revenue_monthly"] - m["revenue_last_month"]) / m["revenue_last_month"] * 100)

    # churn_rate = (customers_last_month - customers_this_month) / customers_last_month
    m["customers_this_month"] = tm.get("purchasing_customers")
    m["customers_last_month"] = lm.get("purchasing_customers")
    m["churn_rate"] = (None if not m["customers_last_month"] or m["customers_this_month"] is None
                       else (m["customers_last_month"] - m["customers_this_month"]) / m["customers_last_month"])

    # product_margin = (revenue - cogs) / revenue * 100   (COGS applied once per unit sold: cogs * quantity)
    def margin_pct(rev, cogs):
        return None if not rev or cogs is None else (rev - cogs) / rev * 100
    m["product_margin"] = margin_pct(m["revenue_total"], m["cogs_total"])
    m["gross_profit_total"] = m["revenue_total"] - m["cogs_total"]
    m["margin_this_month"] = margin_pct(tm.get("revenue"), tm.get("cogs"))
    m["margin_last_month"] = margin_pct(lm.get("revenue"), lm.get("cogs"))
    # margin_trend = margin_this_month - margin_last_month (percentage points)
    m["margin_trend"] = (None if m["margin_this_month"] is None or m["margin_last_month"] is None
                         else m["margin_this_month"] - m["margin_last_month"])
    if m["cogs_total"] > m["revenue_total"]:
        m["data_quality_issues"].append(
            "COGS (product.cogs * sale.quantity) exceeds sale.revenue for the period: gross margin is negative")

    # sale.revenue vs quantity consistency (does revenue scale with units?)
    cur.execute("""SELECT corr(s.revenue, s.quantity) AS c_qty, corr(s.revenue, p.list_price - s.discount_applied) AS c_price
                   FROM runtime.sale s JOIN runtime.product p ON p.product_id = s.product_id WHERE s.business_id = %s""", (business_id,))
    c = cur.fetchone()
    m["corr_revenue_quantity"] = num(c["c_qty"])
    m["corr_revenue_price"] = num(c["c_price"])
    if m["corr_revenue_quantity"] is not None and abs(m["corr_revenue_quantity"]) < 0.1:
        m["data_quality_issues"].append(
            f"sale.revenue does not scale with sale.quantity (corr={m['corr_revenue_quantity']:.3f}); "
            "line revenue and units sold are inconsistent in the source data")

    # customer_lifetime_value = AVG(sum_of_customer_purchases) over purchasing customers
    cur.execute("""SELECT AVG(t.total) AS clv FROM (SELECT customer_id, SUM(revenue) AS total FROM runtime.sale
                   WHERE business_id = %s AND customer_id IS NOT NULL GROUP BY customer_id) t""", (business_id,))
    m["customer_lifetime_value"] = num(cur.fetchone()["clv"])

    # ---- customer grain (runtime.customer): repeat_purchase_rate =
    #      COUNT(DISTINCT customer_id WHERE repeat_count >= 2) / COUNT(DISTINCT customer_id)
    cur.execute("""SELECT COUNT(DISTINCT customer_id) AS customers_total,
                          COUNT(DISTINCT customer_id) FILTER (WHERE repeat_count >= 2) AS customers_repeat_ge2,
                          COUNT(*) FILTER (WHERE repeat_count > 0 AND customer_id NOT IN
                                (SELECT customer_id FROM runtime.sale WHERE business_id = %s AND customer_id IS NOT NULL)) AS repeat_without_sales
                   FROM runtime.customer WHERE business_id = %s""", (business_id, business_id))
    c = cur.fetchone()
    m["customers_total"] = c["customers_total"]
    m["customers_repeat_ge2"] = c["customers_repeat_ge2"]
    m["repeat_purchase_rate"] = (c["customers_repeat_ge2"] / c["customers_total"]) if c["customers_total"] else None
    if c["repeat_without_sales"]:
        m["data_quality_issues"].append(
            f"{c['repeat_without_sales']} customers have repeat_count > 0 but no rows in runtime.sale; "
            "customer.repeat_count is not derivable from sales")
    # customer_count: no KB definition exists for this processed_upload column. The pre-existing
    # meaning (distinct customers with a sale in the observation period) is kept, not redefined.
    m["customer_count"] = int(m["purchasing_customers"])

    # ---- channel grain
    cur.execute("""SELECT channel, SUM(revenue) AS revenue FROM runtime.sale WHERE business_id = %s GROUP BY channel ORDER BY channel""",
                (business_id,))
    m["revenue_by_channel"] = {row["channel"]: num(row["revenue"]) for row in cur.fetchall()}
    # channel_mix = {online: %, retail: %, marketplace: %}
    m["channel_mix"] = {ch: rev / m["revenue_total"] * 100 for ch, rev in m["revenue_by_channel"].items()} if m["revenue_total"] else {}

    # ---- product grain
    cur.execute("""SELECT p.product_id::text AS product_id, p.name, p.cogs, p.list_price,
                          COUNT(s.sale_id) AS sale_rows, COALESCE(SUM(s.quantity), 0) AS units,
                          COALESCE(SUM(s.revenue), 0) AS revenue, COALESCE(SUM(p.cogs * s.quantity), 0) AS cogs_total,
                          MAX(s.sale_date) AS last_sold
                   FROM runtime.product p LEFT JOIN runtime.sale s ON s.product_id = p.product_id AND s.business_id = p.business_id
                   WHERE p.business_id = %s GROUP BY p.product_id, p.name, p.cogs, p.list_price ORDER BY revenue DESC""", (business_id,))
    products = []
    for row in cur.fetchall():
        d = {k: num(v) for k, v in row.items()}
        d["product_margin"] = margin_pct(d["revenue"], d["cogs_total"])          # (revenue - cogs) / revenue * 100
        d["product_revenue_pct"] = d["revenue"] / m["revenue_total"] * 100 if m["revenue_total"] else None  # revenue_by_product / total * 100
        products.append(d)
    m["products"] = products
    # revenue_concentration = SUM(top_3_products_revenue) / total_revenue * 100
    top3 = sum(p["revenue"] for p in products[:3])
    m["revenue_concentration"] = top3 / m["revenue_total"] * 100 if m["revenue_total"] else None
    # sanity: product-grain totals must equal sales-grain totals (no fan-out, nothing dropped)
    m["product_grain_revenue_total"] = sum(p["revenue"] for p in products)
    m["product_grain_cogs_total"] = sum(p["cogs_total"] for p in products)

    # ---- inventory grain: one row per (business, product) snapshot
    cur.execute("""SELECT COUNT(*) AS inventory_rows, COUNT(DISTINCT i.last_updated) AS inventory_snapshots,
                          SUM(i.quantity_on_hand * p.cogs) AS inventory_value_at_cost,
                          SUM(i.quantity_on_hand * p.cogs) FILTER (WHERE ls.last_sold IS NULL OR ls.last_sold < %s::date - %s) AS slow_moving_value_at_cost,
                          COUNT(*) FILTER (WHERE ls.last_sold IS NULL OR ls.last_sold < %s::date - %s) AS slow_moving_skus
                   FROM runtime.inventory i JOIN runtime.product p ON p.product_id = i.product_id
                   LEFT JOIN (SELECT product_id, MAX(sale_date) AS last_sold FROM runtime.sale WHERE business_id = %s GROUP BY product_id) ls
                          ON ls.product_id = i.product_id
                   WHERE i.business_id = %s""",
                (m["period_end"], SLOW_MOVING_DAYS, m["period_end"], SLOW_MOVING_DAYS, business_id, business_id))
    inv = {k: num(v) for k, v in cur.fetchone().items()}
    m.update(inv)
    # slow_moving_inventory_pct = SUM(value WHERE days_since_last_sold > 90) / total_inventory_value (valued at cost)
    m["slow_moving_inventory_pct"] = (None if not inv["inventory_value_at_cost"]
                                      else (inv["slow_moving_value_at_cost"] or 0) / inv["inventory_value_at_cost"] * 100)
    # inventory_turnover = cogs_annual / avg_inventory_value -> needs >= 2 snapshots; keep the inputs we DO have
    m["cogs_annual"] = m["cogs_total"] if (m["period_end"] - m["period_start"]).days >= 364 else None
    m["inventory_turnover"] = None  # never approximated from a single snapshot (see ABSENT_REASONS)

    # ---- form-asserted revenue_monthly vs calculated (G-03 contradiction check)
    if m["form_revenue_monthly"] is not None and m["revenue_monthly"] is not None:
        rel = abs(m["form_revenue_monthly"] - m["revenue_monthly"]) / max(abs(m["revenue_monthly"]), 1e-9)
        m["revenue_monthly_sources_agree"] = rel <= CONTRADICTION_TOLERANCE
        if not m["revenue_monthly_sources_agree"]:
            m["data_quality_issues"].append(
                f"revenue_monthly asserted by form ({m['form_revenue_monthly']:.2f}) disagrees with SUM(sales.revenue) "
                f"for {this_start:%Y-%m} ({m['revenue_monthly']:.2f}); the form value carries no month")
    else:
        m["revenue_monthly_sources_agree"] = None

    cur.close()
    return m


# --------------------------------------------------------------------------- evidence
def _confidence_revenue_monthly(m, factors):
    """KB confidence_factors: full_month_data 1.0 / partial_month 0.7 / thin_data 0.3.
    thin_data has no criterion in the KB, so it is never applied here."""
    if not factors:
        return None
    return factors.get("full_month_data") if m["this_month"]["complete"] else factors.get("partial_month")


def _confidence_churn(m, factors):
    """KB confidence_factors keyed on the customer count in the base month."""
    if not factors or m.get("customers_last_month") is None:
        return None
    n = m["customers_last_month"]
    key = "10_plus_customers" if n >= 10 else "5_to_9_customers" if n >= 5 else "under_5_customers"
    return factors.get(key)


def derive_evidence(m: dict, kb: dict, processed_id, upload_id) -> list[dict]:
    """
    Translate computed metrics into KB-typed evidence records. One record per KB evidence type
    (plus per-product records for the two per-product types). Missing inputs -> state 'absent'.
    """
    tm = m.get("this_month") or {}
    lm = m.get("last_month") or {}
    window_month = {"month_start": str(tm.get("start")), "month_end_exclusive": str(tm.get("end_exclusive"))} if tm else None
    window_period = {"period_start": str(m.get("period_start")), "period_end": str(m.get("period_end"))}
    ev: list[dict] = []

    def rec(etype, value, state="present", about_type="business", about_id=None, confidence=None, **extra):
        kbt = kb[etype]
        payload = {
            "value": None if value is None else (round(value, 4) if isinstance(value, float) else value),
            "unit": kbt["unit"],
            "confidence_0_to_1": validate_confidence(confidence),
            "source_record_id": str(processed_id),
            "formula": kbt["calculation"],
        }
        payload.update(extra)
        ev.append({"business_id": m["business_id"], "evidence_type": etype, "about_type": about_type,
                   "about_id": about_id or m["business_id"], "state": state,
                   "asserted_by": KB_ASSERTED_BY, "source_system": KB_SOURCE_SYSTEM,
                   "payload_json": payload, "traced_from_upload_id": str(upload_id) if upload_id else None})

    def absent(etype, reason_code, missing, reason, **extra):
        rec(etype, None, state="absent", reason_code=reason_code, missing_inputs=missing, reason=reason,
            expected_sources={"asserted_by": kb[etype]["asserted_by"], "source_system": kb[etype]["source_system"]}, **extra)

    if not m.get("sale_rows"):
        for t in DERIVABLE_TYPES:
            absent(t, "MISSING_SOURCE", ["runtime.sale"], "No sales rows for this business")
    else:
        # revenue_monthly: calculated from sales; the form snapshot asserts a second value -> may be contradicted (G-03)
        state = "present"
        extra = {"window": window_month, "inputs": {"sale_rows_in_month": (m["monthly"].get(tm["start"]) or {}).get("sale_rows")}}
        if m.get("form_revenue_monthly") is not None:
            extra["other_assertion"] = {"asserted_by": "form", "source_system": "manual", "value": m["form_revenue_monthly"],
                                        "upload_id": str(upload_id), "month": None}
            if m.get("revenue_monthly_sources_agree") is False:
                state = "contradicted"
                extra["conflict"] = (f"form asserts {m['form_revenue_monthly']:.2f}; calculation gives {m['revenue_monthly']:.2f} "
                                     f"for {tm['start']:%Y-%m} (tolerance {CONTRADICTION_TOLERANCE:.0%})")
        rec("revenue_monthly", m["revenue_monthly"], state=state,
            confidence=_confidence_revenue_monthly(m, kb["revenue_monthly"]["confidence_factors"]), **extra)

        if m.get("revenue_trend") is None:
            absent("revenue_trend", "MISSING_SOURCE", ["revenue_last_month"], "No complete prior month in the observation period")
        else:
            rec("revenue_trend", m["revenue_trend"], window={"this": window_month, "last": {"month_start": str(lm["start"])}},
                inputs={"revenue_this_month": m["revenue_monthly"], "revenue_last_month": m["revenue_last_month"]})

        rec("revenue_concentration", m["revenue_concentration"], window=window_period,
            inputs={"top_3_products": [{"product_id": p["product_id"], "revenue": p["revenue"]} for p in m["products"][:3]],
                    "total_revenue": m["revenue_total"]})
        rec("channel_mix", {k: round(v, 4) for k, v in m["channel_mix"].items()}, window=window_period,
            inputs={"revenue_by_channel": m["revenue_by_channel"], "total_revenue": m["revenue_total"]})

        if m.get("churn_rate") is None:
            absent("churn_rate", "MISSING_SOURCE", ["customers_last_month"], "No complete prior month in the observation period")
        else:
            rec("churn_rate", m["churn_rate"], confidence=_confidence_churn(m, kb["churn_rate"]["confidence_factors"]),
                window={"this": window_month, "last": {"month_start": str(lm["start"])}},
                inputs={"customers_last_month": m["customers_last_month"], "customers_this_month": m["customers_this_month"]})

        rec("repeat_purchase_rate", m["repeat_purchase_rate"],
            inputs={"customers_repeat_ge2": m["customers_repeat_ge2"], "customers_total": m["customers_total"],
                    "population": "runtime.customer rows for the business"})
        rec("customer_lifetime_value", m["customer_lifetime_value"], window=window_period,
            inputs={"purchasing_customers": m["purchasing_customers"], "revenue_total": m["revenue_total"]})

        rec("product_margin", m["product_margin"], window=window_period,
            inputs={"revenue": m["revenue_total"], "cogs": m["cogs_total"], "gross_profit": m["gross_profit_total"],
                    "units_sold": m["units_sold"], "sale_rows": m["sale_rows"], "cogs_basis": "product.cogs * sale.quantity"})
        for p in m["products"]:
            if p["revenue"]:
                rec("product_margin", p["product_margin"], about_type="product", about_id=p["product_id"], window=window_period,
                    inputs={"revenue": p["revenue"], "cogs": p["cogs_total"], "units_sold": p["units"], "unit_cogs": p["cogs"]})
            rec("product_revenue_pct", p["product_revenue_pct"], about_type="product", about_id=p["product_id"], window=window_period,
                inputs={"revenue_by_product": p["revenue"], "total_revenue": m["revenue_total"]})

        if m.get("margin_trend") is None:
            absent("margin_trend", "MISSING_SOURCE", ["margin_last_month"], "No complete prior month in the observation period")
        else:
            rec("margin_trend", m["margin_trend"], window={"this": window_month, "last": {"month_start": str(lm["start"])}},
                inputs={"margin_this_month": m["margin_this_month"], "margin_last_month": m["margin_last_month"]})

        if m.get("slow_moving_inventory_pct") is None:
            absent("slow_moving_inventory_pct", "MISSING_SOURCE", ["runtime.inventory"], "No inventory rows for this business")
        else:
            rec("slow_moving_inventory_pct", m["slow_moving_inventory_pct"],
                inputs={"slow_moving_value": m["slow_moving_value_at_cost"] or 0, "total_inventory_value": m["inventory_value_at_cost"],
                        "slow_moving_skus": m["slow_moving_skus"], "days_threshold": SLOW_MOVING_DAYS,
                        "reference_date": str(m["period_end"]), "valuation_basis": INVENTORY_VALUATION_BASIS})

    for etype, (code, missing, reason) in ABSENT_REASONS.items():
        extra = {}
        if etype == "inventory_turnover":
            extra["inputs_available"] = {"cogs_annual": m.get("cogs_annual"), "inventory_snapshots": m.get("inventory_snapshots"),
                                         "single_snapshot_value_at_cost": m.get("inventory_value_at_cost")}
        absent(etype, code, missing, reason, **extra)

    # every KB type must be represented: once at business grain, or (product_revenue_pct) at product grain
    business_level = [e["evidence_type"] for e in ev if e["about_type"] == "business"]
    product_level = {e["evidence_type"] for e in ev if e["about_type"] == "product"}
    missing_types = set(kb) - set(business_level) - (product_level & PRODUCT_GRAIN_ONLY_TYPES)
    if missing_types:
        raise RuntimeError(f"evidence projection incomplete, KB types not covered: {sorted(missing_types)}")
    dupes = {t for t in business_level if business_level.count(t) > 1}
    if dupes:
        raise RuntimeError(f"evidence projection produced duplicate business-level types: {sorted(dupes)}")
    return ev


def json_default(o):
    if isinstance(o, decimal.Decimal):
        return float(o)
    if isinstance(o, (dt.date, dt.datetime)):
        return o.isoformat()
    return str(o)


def dumps(obj) -> str:
    return json.dumps(obj, default=json_default)
