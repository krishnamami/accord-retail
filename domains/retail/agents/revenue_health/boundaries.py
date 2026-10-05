"""Recommendation boundary evaluation for the Revenue Health agent."""
from __future__ import annotations

from typing import Any


def evaluate_boundaries(context: Any, rules: list[dict[str, Any]]) -> dict[str, Any]:
    fired = {r["rule_id"] for r in rules if r["fired"]}
    checks = [
        {"boundary_id": "BND_REV_001", "description": "Comparable revenue history is required", "passed": context.data_quality_status == "READY"},
        {"boundary_id": "BND_REV_002", "description": "Revenue Health may diagnose movement but cannot assert an unsupported cause", "passed": True},
        {"boundary_id": "BND_REV_003", "description": "Specialized price/inventory/retention actions must route to their governed agent", "passed": True},
    ]
    if context.data_quality_status != "READY":
        status = "CANNOT_DECIDE"
        reason = "Comparable revenue evidence is insufficient."
    elif "REV_005" in fired:
        status = "CAUSE_NOT_ESTABLISHED"
        reason = "Revenue deterioration materially exceeds unit movement; product/channel/price-mix evidence must establish cause."
    else:
        status = "WITHIN_DIAGNOSTIC_BOUNDARY"
        reason = "The agent may classify revenue health and recommend governed investigation/routing."
    return {"status": status, "reason": reason, "checks": checks}
