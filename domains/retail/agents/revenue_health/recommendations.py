"""Permitted recommendation mapping for the Revenue Health agent.

Revenue Health owns top-line diagnosis. It may surface driver warnings and route
work, but it must not execute specialist pricing, inventory, margin, or customer
actions.
"""
from __future__ import annotations

from typing import Any


def _routes(fired: set[str]) -> list[dict[str, str]]:
    routes: list[dict[str, str]] = []
    if "REV_004" in fired:
        routes.append({"agent": "customer_retention", "reason": "Purchasing-customer participation declined materially."})
    if "REV_003" in fired:
        routes.append({"agent": "inventory_exposure", "reason": "Unit volume declined materially; validate inventory availability/exposure before assigning cause."})
    if "REV_005" in fired:
        routes.append({"agent": "pricing_opportunity", "reason": "Revenue deterioration materially exceeds unit movement; inspect realized price/product/channel mix."})
        routes.append({"agent": "margin_health", "reason": "Revenue/volume divergence may affect or reflect unit economics; validate margin evidence."})
    return routes


def recommend(rules: list[dict[str, Any]], boundary: dict[str, Any]) -> dict[str, Any]:
    fired = {r["rule_id"] for r in rules if r["fired"]}
    routes = _routes(fired)

    if boundary["status"] == "CANNOT_DECIDE":
        return {
            "decision": "CANNOT_DECIDE",
            "severity": "UNKNOWN",
            "recommendation": "Acquire sufficient comparable-period revenue evidence before intervention.",
            "specialist_routes": [],
            "allowed_actions": ["REFRESH_DATA"],
            "restricted_actions": ["ASSERT_CAUSE", "CHANGE_PRICE", "CHANGE_INVENTORY", "TARGET_CUSTOMERS"],
        }

    # Top-line revenue risk takes precedence when the revenue threshold itself fires.
    if "REV_002" in fired:
        decision, severity = "REVENUE_RISK", "HIGH"
    elif "REV_001" in fired:
        decision, severity = "REVENUE_RISK", "MEDIUM"
    # Driver deterioration without material top-line decline is still actionable.
    elif "REV_003" in fired or "REV_004" in fired or "REV_005" in fired:
        decision, severity = "REVENUE_DRIVER_WARNING", "MEDIUM"
    elif "REV_006" in fired:
        decision, severity = "REVENUE_OPPORTUNITY", "MEDIUM"
    else:
        decision, severity = "HEALTHY_OR_WATCH", "LOW"

    if boundary["status"] == "CAUSE_NOT_ESTABLISHED":
        text = "Investigate product, channel and price-mix drivers before assigning cause or taking specialized action."
    elif decision == "REVENUE_RISK":
        text = "Prioritize revenue diagnosis and route observed driver signals to the appropriate governed specialist agents."
    elif decision == "REVENUE_DRIVER_WARNING":
        text = "Top-line revenue is not yet at the material-risk threshold, but a supporting driver deteriorated; route the signal for specialist diagnosis."
    elif decision == "REVENUE_OPPORTUNITY":
        text = "Review the drivers of comparable-period growth and determine whether the pattern is repeatable."
    else:
        text = "Continue monitoring comparable-period revenue health."

    return {
        "decision": decision,
        "severity": severity,
        "recommendation": text,
        "specialist_routes": routes,
        "allowed_actions": ["INVESTIGATE", "ROUTE_TO_SPECIALIST", "MONITOR"],
        "restricted_actions": ["ASSERT_UNSUPPORTED_CAUSE", "DIRECT_PRICE_CHANGE", "DIRECT_INVENTORY_CHANGE", "DIRECT_CUSTOMER_OFFER"],
    }
