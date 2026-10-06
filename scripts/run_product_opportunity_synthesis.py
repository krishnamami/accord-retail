"""Deterministic Product Opportunity Synthesis v1.

Consumes persisted atomic Decision OS outputs only. It does not call agents,
recalculate their metrics, or use an LLM. Margin Health may have multiple
product-period outputs, so the latest data_as_of output in the current bundle
is selected before synthesis.
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter

RULES = [
    {
        "id": "SYN_001",
        "when": lambda m, i, p: m == "MARGIN_RISK" and i in {"EXCESS_INVENTORY_RISK", "SLOW_MOVING_RISK", "CAPITAL_EXPOSURE"},
        "type": "MARGIN_RECOVERY",
        "priority": "HIGH",
        "recommendation": "Prioritize merchandising review: margin risk coincides with excess or slow-moving inventory. Review pricing, discounting and inventory disposition with human approval.",
    },
    {
        "id": "SYN_002",
        "when": lambda m, i, p: p == "PRICE_UP_OPPORTUNITY" and m not in {"MARGIN_RISK", "CANNOT_DECIDE"},
        "type": "PRICE_REVIEW",
        "priority": "MEDIUM",
        "recommendation": "Review a governed price-increase test; pricing evidence indicates headroom and the latest margin signal does not indicate margin risk.",
    },
    {
        "id": "SYN_003",
        "when": lambda m, i, p: i == "REPLENISHMENT_RISK",
        "type": "REPLENISHMENT_ACTION",
        "priority": "HIGH",
        "recommendation": "Prioritize replenishment review and validate demand continuity and purchasing constraints before any inventory action.",
    },
    {
        "id": "SYN_004",
        "when": lambda m, i, p: i in {"EXCESS_INVENTORY_RISK", "SLOW_MOVING_RISK", "CAPITAL_EXPOSURE"},
        "type": "EXCESS_INVENTORY_ACTION",
        "priority": "MEDIUM",
        "recommendation": "Review excess inventory exposure with current margin and pricing evidence before markdown, transfer or disposition decisions.",
    },
    {
        "id": "SYN_005",
        "when": lambda m, i, p: p == "MARGIN_PROTECTION",
        "type": "MARGIN_PROTECTION",
        "priority": "HIGH",
        "recommendation": "Protect margin: review pricing and discount leakage before considering any price reduction.",
    },
    {
        "id": "SYN_006",
        "when": lambda m, i, p: p == "COMPETITIVE_PRICE_RISK",
        "type": "COMPETITIVE_PRICE_REVIEW",
        "priority": "MEDIUM",
        "recommendation": "Review competitive positioning and model scenarios before any governed price change.",
    },
    {
        "id": "SYN_007",
        "when": lambda m, i, p: p == "DISCOUNT_LEAKAGE",
        "type": "DISCOUNT_REVIEW",
        "priority": "MEDIUM",
        "recommendation": "Investigate realized discounting before changing list price.",
    },
]


def choose_opportunity(margin, inventory, pricing):
    """Choose the highest-priority supported merchandising action.

    Evidence limitations are scoped to the action that requires that evidence.
    A limited pricing signal does not suppress a supported inventory action.
    """
    decisions = [x["decision"] for x in (margin, inventory, pricing) if x]
    if not decisions:
        return None

    m = margin["decision"] if margin else None
    i = inventory["decision"] if inventory else None
    p = pricing["decision"] if pricing else None

    # Cross-agent condition first: supported margin risk plus excess/capital exposure.
    if m == "MARGIN_RISK" and i in {"EXCESS_INVENTORY_RISK", "SLOW_MOVING_RISK", "CAPITAL_EXPOSURE"}:
        rule = RULES[0]
        return {**rule, "rule_id": rule["id"], "evidence_status": "READY"}

    # Operational inventory risk takes precedence over optional pricing upside.
    if i == "REPLENISHMENT_RISK":
        rule = next(r for r in RULES if r["id"] == "SYN_003")
        return {**rule, "rule_id": rule["id"], "evidence_status": "READY"}

    if i in {"EXCESS_INVENTORY_RISK", "SLOW_MOVING_RISK", "CAPITAL_EXPOSURE"}:
        rule = next(r for r in RULES if r["id"] == "SYN_004")
        return {**rule, "rule_id": rule["id"], "evidence_status": "READY"}

    # Pricing actions require usable pricing evidence.
    if p == "MARGIN_PROTECTION":
        rule = next(r for r in RULES if r["id"] == "SYN_005")
        return {**rule, "rule_id": rule["id"], "evidence_status": "READY"}

    if p == "COMPETITIVE_PRICE_RISK":
        rule = next(r for r in RULES if r["id"] == "SYN_006")
        return {**rule, "rule_id": rule["id"], "evidence_status": "READY"}

    if p == "DISCOUNT_LEAKAGE":
        rule = next(r for r in RULES if r["id"] == "SYN_007")
        return {**rule, "rule_id": rule["id"], "evidence_status": "READY"}

    if p == "PRICE_UP_OPPORTUNITY" and m not in {"MARGIN_RISK", "CANNOT_DECIDE"}:
        rule = next(r for r in RULES if r["id"] == "SYN_002")
        return {**rule, "rule_id": rule["id"], "evidence_status": "READY"}

    # Evidence gaps are returned only when no independently supported action
    # above can be recommended.
    if "CANNOT_DECIDE" in decisions:
        return {
            "rule_id": "SYN_000",
            "type": "EVIDENCE_GAP",
            "priority": "LOW",
            "recommendation": "Refresh missing decision evidence before taking an evidence-dependent merchandising action.",
            "evidence_status": "CANNOT_DECIDE",
        }

    if "LIMITED_EVIDENCE" in decisions:
        return {
            "rule_id": "SYN_008",
            "type": "EVIDENCE_GAP",
            "priority": "LOW",
            "recommendation": "Refresh limited evidence before taking an action that depends on that evidence.",
            "evidence_status": "LIMITED",
        }

    return {
        "rule_id": "SYN_009",
        "type": "MONITOR",
        "priority": "LOW",
        "recommendation": "No cross-agent merchandising intervention is indicated by the current deterministic evidence.",
        "evidence_status": "READY",
    }

def main():
    import psycopg
    from psycopg.rows import dict_row

    url = os.environ.get("DATABASE_URL")
    if not url:
        print("ERROR: DATABASE_URL is required", file=sys.stderr)
        return 2

    with psycopg.connect(url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                WITH current_outputs AS (
                  SELECT d.*
                  FROM runtime.retail_decision_outputs d
                  JOIN runtime.retail_decision_bundles b ON b.bundle_id=d.bundle_id
                  WHERE b.is_current=TRUE
                    AND d.subject_type='product'
                    AND d.agent_id IN ('margin_health','inventory_exposure','pricing_opportunity')
                ),
                ranked AS (
                  SELECT *,
                    ROW_NUMBER() OVER (
                      PARTITION BY bundle_id, subject_id, agent_id
                      ORDER BY data_as_of DESC NULLS LAST, created_at DESC, output_id DESC
                    ) AS rn
                  FROM current_outputs
                )
                SELECT * FROM ranked WHERE rn=1
                ORDER BY business_id, subject_id, agent_id
                """
            )
            rows = cur.fetchall()

            by_product = {}
            for row in rows:
                key = (row["bundle_id"], row["business_id"], row["subject_id"])
                by_product.setdefault(key, {})[row["agent_id"]] = row

            counts = Counter()
            for (bundle_id, business_id, product_id), agents in by_product.items():
                margin = agents.get("margin_health")
                inventory = agents.get("inventory_exposure")
                pricing = agents.get("pricing_opportunity")
                result = choose_opportunity(margin, inventory, pricing)
                if result is None:
                    continue

                sources = [x for x in (margin, inventory, pricing) if x]
                source_output_ids = [str(x["output_id"]) for x in sources]
                source_decisions = {
                    x["agent_id"]: {
                        "output_id": str(x["output_id"]),
                        "decision": x["decision"],
                        "severity": x["severity"],
                        "data_as_of": x["data_as_of"].isoformat() if x["data_as_of"] else None,
                    }
                    for x in sources
                }

                cur.execute(
                    """
                    INSERT INTO runtime.retail_product_opportunities (
                      bundle_id,business_id,product_id,opportunity_type,priority,
                      recommendation,synthesis_rule_id,source_output_ids,
                      source_decisions,evidence_status,allowed_actions,
                      restricted_actions
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s,%s::jsonb,%s::jsonb)
                    ON CONFLICT (bundle_id,product_id) DO UPDATE SET
                      opportunity_type=EXCLUDED.opportunity_type,
                      priority=EXCLUDED.priority,
                      recommendation=EXCLUDED.recommendation,
                      synthesis_rule_id=EXCLUDED.synthesis_rule_id,
                      source_output_ids=EXCLUDED.source_output_ids,
                      source_decisions=EXCLUDED.source_decisions,
                      evidence_status=EXCLUDED.evidence_status,
                      allowed_actions=EXCLUDED.allowed_actions,
                      restricted_actions=EXCLUDED.restricted_actions,
                      synthesis_version='1.0.0',
                      created_at=NOW()
                    """,
                    (
                        bundle_id,business_id,product_id,result["type"],result["priority"],
                        result["recommendation"],result["rule_id"],
                        json.dumps(source_output_ids),json.dumps(source_decisions),
                        result["evidence_status"],
                        json.dumps(["INVESTIGATE","MODEL_SCENARIO","ROUTE_FOR_HUMAN_REVIEW","MONITOR"]),
                        json.dumps(["AUTO_CHANGE_PRICE","AUTO_CREATE_PURCHASE_ORDER","AUTO_DISCONTINUE_PRODUCT","ASSERT_UNSUPPORTED_CAUSE"]),
                    ),
                )
                counts[result["type"]] += 1
        conn.commit()

    print("Product Opportunity Synthesis v1 complete")
    print(f"Products synthesized: {sum(counts.values())}")
    for name, count in sorted(counts.items()):
        print(f"  {name}: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
