"""Evidence construction and lineage for the Revenue Health agent."""
from __future__ import annotations

from typing import Any
from .context import RevenueContext


def build_evidence(context: RevenueContext, calculations: dict[str, Any]) -> list[dict[str, Any]]:
    """Convert observed/calculated facts into explicit evidence records."""
    status = context.data_quality_status
    confidence = 1.0 if status == "READY" else 0.0
    evidence: list[dict[str, Any]] = []

    def add(evidence_type: str, finding: str, value: Any) -> None:
        if value is not None:
            evidence.append({
                "evidence_type": evidence_type,
                "finding": finding,
                "value": value,
                "period_start": context.period_start,
                "data_as_of": context.data_as_of,
                "comparison_basis": context.comparison_basis,
                "quality_status": status,
                "confidence": confidence,
                "source": "agent.revenue_health_context",
            })

    add("REVENUE_TREND", "Comparable-period revenue change", calculations.get("revenue_change_pct"))
    add("UNITS_SOLD_TREND", "Comparable-period unit change", calculations.get("unit_change_pct"))
    add("PURCHASING_CUSTOMERS_TREND", "Comparable-period purchasing-customer change", calculations.get("purchasing_customer_change_pct"))
    add("REVENUE_PER_UNIT", "Current realized revenue per unit", calculations.get("realized_revenue_per_unit"))

    if context.revenue_by_channel is not None:
        evidence.append({"evidence_type": "CHANNEL_MIX", "finding": "Revenue by channel", "value": context.revenue_by_channel, "data_as_of": context.data_as_of, "quality_status": status, "confidence": confidence, "source": "agent.revenue_health_context"})
    if context.product_contribution is not None:
        evidence.append({"evidence_type": "PRODUCT_REVENUE_CONTRIBUTION", "finding": "Product revenue contribution", "value": context.product_contribution, "data_as_of": context.data_as_of, "quality_status": status, "confidence": confidence, "source": "agent.revenue_health_context"})
    return evidence
