#!/usr/bin/env python3
"""Run all frozen Retail domain agents and persist one common Decision OS contract.

This is deterministic orchestration. It does not call an LLM and does not
reinterpret agent outputs. Each agent remains the owner of its decision logic.
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter, defaultdict
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from domains.retail.agents.revenue_health.agent import run as run_revenue
from domains.retail.agents.margin_health.agent import run as run_margin
from domains.retail.agents.inventory_exposure.agent import run as run_inventory
from domains.retail.agents.customer_retention.agent import run as run_retention
from domains.retail.agents.pricing_opportunity.agent import run as run_pricing
from domains.retail.decision_contract import to_common_decision

AGENTS = (
    ("revenue_health", "agent.revenue_health_context", run_revenue),
    ("margin_health", "agent.margin_health_context", run_margin),
    ("inventory_exposure", "agent.inventory_exposure_context", run_inventory),
    ("customer_retention", "agent.customer_retention_context", run_retention),
    ("pricing_opportunity", "agent.pricing_opportunity_context", run_pricing),
)


def _json_default(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, (Decimal, UUID)):
        return str(value)
    return str(value)


def _json(value):
    return json.dumps(value, default=_json_default)


def _rows(conn, view_name):
    with conn.cursor() as cur:
        cur.execute(f"SELECT * FROM {view_name}")
        cols = [d.name if hasattr(d, "name") else d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def _insert_output(cur, item, bundle_id):
    cur.execute(
        """
        INSERT INTO runtime.retail_decision_outputs (
          business_id, subject_type, subject_id, agent_id, agent_version,
          decision, severity, recommendation, confidence, evidence,
          calculations, rules_evaluated, rules_fired, boundary,
          allowed_actions, restricted_actions, context_snapshot,
          kb_version, rule_version, metric_version, source_view,
          data_as_of, bundle_id
        )
        VALUES (
          %(business_id)s, %(subject_type)s, %(subject_id)s, %(agent_id)s,
          %(agent_version)s, %(decision)s, %(severity)s, %(recommendation)s,
          %(confidence)s, %(evidence)s::jsonb, %(calculations)s::jsonb,
          %(rules_evaluated)s::jsonb, %(rules_fired)s::jsonb,
          %(boundary)s::jsonb, %(allowed_actions)s::jsonb,
          %(restricted_actions)s::jsonb, %(context_snapshot)s::jsonb,
          %(kb_version)s, %(rule_version)s, %(metric_version)s,
          %(source_view)s, %(data_as_of)s, %(bundle_id)s
        )
        """,
        {
            **item,
            "evidence": _json(item["evidence"]),
            "calculations": _json(item["calculations"]),
            "rules_evaluated": _json(item["rules_evaluated"]),
            "rules_fired": _json(item["rules_fired"]),
            "boundary": _json(item["boundary"]),
            "allowed_actions": _json(item["allowed_actions"]),
            "restricted_actions": _json(item["restricted_actions"]),
            "context_snapshot": _json(item["context_snapshot"]),
            "bundle_id": str(bundle_id),
        },
    )


def main():
    import psycopg

    url = os.environ.get("DATABASE_URL")
    if not url:
        print("ERROR: DATABASE_URL is required", file=sys.stderr)
        return 2

    packages = []
    counts = {}

    with psycopg.connect(url) as conn:
        for agent_id, view_name, runner in AGENTS:
            rows = _rows(conn, view_name)
            agent_packages = [runner(row) for row in rows]
            packages.extend(agent_packages)
            counts[agent_id] = len(agent_packages)

        by_business = defaultdict(list)
        for package in packages:
            by_business[str(package["business_id"])].append(package)

        with conn.cursor() as cur:
            for business_id, business_packages in by_business.items():
                bundle_id = uuid4()

                # Only one current bundle per business. History is retained.
                cur.execute(
                    """
                    UPDATE runtime.retail_decision_bundles
                    SET is_current = FALSE
                    WHERE business_id = %s AND is_current = TRUE
                    """,
                    (business_id,),
                )

                common = [to_common_decision(p) for p in business_packages]
                rules_snapshot = {
                    item["agent_id"]: {
                        "agent_version": item["agent_version"],
                        "kb_version": item["kb_version"],
                        "rule_version": item["rule_version"],
                        "metric_version": item["metric_version"],
                    }
                    for item in common
                }

                all_signals = [
                    {
                        "agent_id": item["agent_id"],
                        "subject_type": item["subject_type"],
                        "subject_id": item["subject_id"],
                        "decision": item["decision"],
                        "severity": item["severity"],
                        "rules_fired": [
                            rule.get("rule_id") for rule in item["rules_fired"]
                            if isinstance(rule, dict)
                        ],
                        "boundary_status": item["boundary"].get("status"),
                    }
                    for item in common
                ]

                cur.execute(
                    """
                    INSERT INTO runtime.retail_decision_bundles (
                      bundle_id, business_id, context_snapshot, rules_snapshot,
                      agent_outputs, all_signals, is_current, version
                    )
                    VALUES (%s, %s, %s::jsonb, %s::jsonb, %s::jsonb,
                            %s::jsonb, TRUE,
                            COALESCE((
                              SELECT MAX(version)+1
                              FROM runtime.retail_decision_bundles
                              WHERE business_id=%s
                            ),1))
                    """,
                    (
                        str(bundle_id), business_id,
                        _json({"business_id": business_id, "agent_count": len(AGENTS)}),
                        _json(rules_snapshot), _json(common), _json(all_signals),
                        business_id,
                    ),
                )

                for item in common:
                    _insert_output(cur, item, bundle_id)

        conn.commit()

    print("\nRetail Decision OS orchestration complete")
    print(f"Businesses bundled: {len(by_business)}")
    print(f"Decision outputs written: {len(packages)}")
    print("\nOutputs by agent:")
    for agent_id, count in counts.items():
        print(f"  {agent_id}: {count}")

    print("\nDecision counts:")
    for decision, count in sorted(Counter(p["decision"] for p in packages).items()):
        print(f"  {decision}: {count}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
