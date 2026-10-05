"""Permitted recommendation mapping for the Revenue Health agent."""
from __future__ import annotations

from typing import Any


def recommend(rules: list[dict[str, Any]], boundary: dict[str, Any]) -> dict[str, Any]:
    fired = {r["rule_id"] for r in rules if r["fired"]}
    if boundary["status"] == "CANNOT_DECIDE":
        return {"decision": "CANNOT_DECIDE", "severity": "UNKNOWN", "recommendation": "Acquire sufficient comparable-period revenue evidence before intervention.", "allowed_actions": ["REFRESH_DATA"], "restricted_actions": ["ASSERT_CAUSE", "CHANGE_PRICE", "CHANGE_INVENTORY", "TARGET_CUSTOMERS"]}
    if "REV_002" in fired:
        decision, severity = "REVENUE_RISK", "HIGH"
    elif "REV_001" in fired:
        decision, severity = "REVENUE_RISK", "MEDIUM"
    elif "REV_006" in fired:
        decision, severity = "REVENUE_OPPORTUNITY", "MEDIUM"
    else:
        decision, severity = "HEALTHY_OR_WATCH", "LOW"

    if boundary["status"] == "CAUSE_NOT_ESTABLISHED":
        text = "Investigate product, channel and price-mix drivers before assigning cause or taking specialized action."
    elif decision == "REVENUE_RISK":
        text = "Prioritize revenue diagnosis and route supported drivers to the appropriate governed agent."
    elif decision == "REVENUE_OPPORTUNITY":
        text = "Review the drivers of comparable-period growth and determine whether the pattern is repeatable."
    else:
        text = "Continue monitoring comparable-period revenue health."
    return {"decision": decision, "severity": severity, "recommendation": text, "allowed_actions": ["INVESTIGATE", "ROUTE_TO_SPECIALIST", "MONITOR"], "restricted_actions": ["ASSERT_UNSUPPORTED_CAUSE", "DIRECT_PRICE_CHANGE", "DIRECT_INVENTORY_CHANGE", "DIRECT_CUSTOMER_OFFER"]}
