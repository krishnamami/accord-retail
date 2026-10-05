"""Revenue Health agent orchestration.

Flow: context -> calculations -> evidence -> rules -> boundaries -> recommendation
-> auditable decision package. No LLM is required to determine the decision.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

from .context import build_context
from .calculations import calculate
from .evidence import build_evidence
from .rules import evaluate_rules, RULE_VERSION
from .boundaries import evaluate_boundaries
from .recommendations import recommend

AGENT_NAME = "revenue_health"
AGENT_VERSION = "1.0.0"
METRIC_VERSION = "revenue-context-v2"


def run(row: Mapping[str, Any], *, kb_version: str | None = None) -> dict[str, Any]:
    context = build_context(row)
    calculations = calculate(context)
    evidence = build_evidence(context, calculations)
    rules = evaluate_rules(calculations)
    boundary = evaluate_boundaries(context, rules)
    recommendation = recommend(rules, boundary)
    fired = [r for r in rules if r["fired"]]

    return {
        "agent": {"name": AGENT_NAME, "version": AGENT_VERSION},
        "business_id": context.business_id,
        "business_name": context.business_name,
        "decision": recommendation["decision"],
        "severity": recommendation["severity"],
        "recommendation": recommendation["recommendation"],
        "confidence": 1.0 if context.data_quality_status == "READY" else 0.0,
        "context": context.to_dict(),
        "calculations": calculations,
        "evidence": evidence,
        "rules_evaluated": rules,
        "rules_fired": fired,
        "boundary": boundary,
        "allowed_actions": recommendation["allowed_actions"],
        "restricted_actions": recommendation["restricted_actions"],
        "versions": {"kb_version": kb_version, "rule_version": RULE_VERSION, "metric_version": METRIC_VERSION},
        "audit": {"decision_at": datetime.now(timezone.utc).isoformat(), "source_view": "agent.revenue_health_context", "comparison_basis": context.comparison_basis, "data_as_of": context.data_as_of},
    }
