"""Deterministic calculations for the Revenue Health agent."""
from __future__ import annotations

from typing import Any
from .context import RevenueContext


def calculate(context: RevenueContext) -> dict[str, Any]:
    """Expose deterministic facts plus traceable derived diagnostics."""
    rev = context.revenue_change_pct
    units = context.unit_change_pct
    customers = context.purchasing_customer_change_pct

    revenue_vs_units_gap = None if rev is None or units is None else round(rev - units, 2)
    revenue_vs_customer_gap = None if rev is None or customers is None else round(rev - customers, 2)

    return {
        "revenue_change_pct": rev,
        "unit_change_pct": units,
        "purchasing_customer_change_pct": customers,
        "revenue_vs_units_gap_pct_points": revenue_vs_units_gap,
        "revenue_vs_customer_gap_pct_points": revenue_vs_customer_gap,
        "realized_revenue_per_unit": context.realized_revenue_per_unit,
        "comparison_basis": context.comparison_basis,
        "comparable_days": context.comparable_days,
        "trace": [
            {"metric": "revenue_change_pct", "formula": "100*(revenue-prior_comparable_revenue)/prior_comparable_revenue", "result": rev},
            {"metric": "unit_change_pct", "formula": "100*(units-prior_comparable_units)/prior_comparable_units", "result": units},
            {"metric": "purchasing_customer_change_pct", "formula": "100*(customers-prior_comparable_customers)/prior_comparable_customers", "result": customers},
            {"metric": "revenue_vs_units_gap_pct_points", "formula": "revenue_change_pct-unit_change_pct", "result": revenue_vs_units_gap},
            {"metric": "revenue_vs_customer_gap_pct_points", "formula": "revenue_change_pct-purchasing_customer_change_pct", "result": revenue_vs_customer_gap},
        ],
    }
