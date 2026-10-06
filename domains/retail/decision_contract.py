"""Common Decision OS contract for Accord Retail.

Adapters only normalize already-computed deterministic agent packages.
They do not recalculate, reinterpret, or override agent decisions.
"""
from __future__ import annotations

from typing import Any, Mapping

SUBJECT_KEYS = (
    ("product_id", "product"),
    ("customer_id", "customer"),
    ("business_id", "business"),
)


def _subject(package: Mapping[str, Any]) -> tuple[str, str]:
    for key, subject_type in SUBJECT_KEYS:
        value = package.get(key)
        if value:
            return subject_type, str(value)
    raise ValueError("Decision package has no supported subject identifier")


def to_common_decision(package: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize one frozen agent package to the common persistence contract."""
    subject_type, subject_id = _subject(package)
    agent = package.get("agent") or {}
    versions = package.get("versions") or {}
    audit = package.get("audit") or {}

    return {
        "business_id": str(package["business_id"]),
        "subject_type": subject_type,
        "subject_id": subject_id,
        "agent_id": agent.get("name"),
        "agent_version": agent.get("version"),
        "decision": package.get("decision"),
        "severity": package.get("severity"),
        "recommendation": package.get("recommendation"),
        "confidence": package.get("confidence"),
        "evidence": package.get("evidence") or [],
        "calculations": package.get("calculations") or {},
        "rules_evaluated": package.get("rules_evaluated") or [],
        "rules_fired": package.get("rules_fired") or [],
        "boundary": package.get("boundary") or {},
        "allowed_actions": package.get("allowed_actions") or [],
        "restricted_actions": package.get("restricted_actions") or [],
        "context_snapshot": package.get("context") or {},
        "kb_version": versions.get("kb_version"),
        "rule_version": versions.get("rule_version"),
        "metric_version": versions.get("metric_version"),
        "source_view": audit.get("source_view"),
        "data_as_of": audit.get("data_as_of"),
    }
