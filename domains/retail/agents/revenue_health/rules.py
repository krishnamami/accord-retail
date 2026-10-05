"""Governed business-rule evaluation for the Revenue Health agent.

Thresholds are explicit defaults for the first implementation. They should move
to KB-backed/versioned configuration before production deployment.
"""
from __future__ import annotations

from typing import Any

RULE_VERSION = "revenue-health-v1"


def evaluate_rules(calc: dict[str, Any]) -> list[dict[str, Any]]:
    r = calc.get("revenue_change_pct")
    u = calc.get("unit_change_pct")
    c = calc.get("purchasing_customer_change_pct")
    ru_gap = calc.get("revenue_vs_units_gap_pct_points")

    definitions = [
        ("REV_001", "Material revenue decline", r is not None and r <= -10.0, {"revenue_change_pct_lte": -10.0}),
        ("REV_002", "Severe revenue decline", r is not None and r <= -25.0, {"revenue_change_pct_lte": -25.0}),
        ("REV_003", "Material unit-volume decline", u is not None and u <= -10.0, {"unit_change_pct_lte": -10.0}),
        ("REV_004", "Purchasing-customer decline", c is not None and c <= -10.0, {"customer_change_pct_lte": -10.0}),
        ("REV_005", "Revenue decline materially exceeds unit decline", r is not None and r < 0 and ru_gap is not None and ru_gap <= -10.0, {"revenue_minus_units_gap_lte": -10.0}),
        ("REV_006", "Material revenue growth", r is not None and r >= 10.0, {"revenue_change_pct_gte": 10.0}),
        ("REV_007", "Broad-based growth", r is not None and r >= 10.0 and u is not None and u > 0 and c is not None and c > 0, {"revenue_growth_gte": 10.0, "units_gt": 0, "customers_gt": 0}),
    ]
    return [
        {"rule_id": rid, "rule_version": RULE_VERSION, "description": desc, "evaluated": True, "fired": bool(fired), "thresholds": thresholds}
        for rid, desc, fired, thresholds in definitions
    ]
