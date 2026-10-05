"""Revenue Health context normalization.

The database view owns joins and period comparability. This module validates and
normalizes a row from ``agent.revenue_health_context`` without inventing facts.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Mapping


@dataclass(frozen=True)
class RevenueContext:
    business_id: str
    business_name: str
    period_start: Any
    data_as_of: Any
    comparison_basis: str | None
    comparable_days: int | None
    revenue: float | None
    prior_comparable_revenue: float | None
    revenue_change_pct: float | None
    units_sold: float | None
    prior_comparable_units: float | None
    unit_change_pct: float | None
    purchasing_customers: int | None
    prior_comparable_customers: int | None
    purchasing_customer_change_pct: float | None
    realized_revenue_per_unit: float | None
    revenue_by_channel: Any
    product_contribution: Any
    data_quality_status: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _num(value: Any) -> float | None:
    return None if value is None else float(value)


def build_context(row: Mapping[str, Any]) -> RevenueContext:
    """Build the governed agent context from a database row."""
    if not row.get("business_id"):
        raise ValueError("business_id is required")
    return RevenueContext(
        business_id=str(row["business_id"]),
        business_name=str(row.get("business_name") or ""),
        period_start=row.get("period_start"),
        data_as_of=row.get("data_as_of"),
        comparison_basis=row.get("comparison_basis"),
        comparable_days=int(row["comparable_days"]) if row.get("comparable_days") is not None else None,
        revenue=_num(row.get("revenue")),
        prior_comparable_revenue=_num(row.get("prior_comparable_revenue")),
        revenue_change_pct=_num(row.get("revenue_change_pct")),
        units_sold=_num(row.get("units_sold")),
        prior_comparable_units=_num(row.get("prior_comparable_units")),
        unit_change_pct=_num(row.get("unit_change_pct")),
        purchasing_customers=int(row["purchasing_customers"]) if row.get("purchasing_customers") is not None else None,
        prior_comparable_customers=int(row["prior_comparable_customers"]) if row.get("prior_comparable_customers") is not None else None,
        purchasing_customer_change_pct=_num(row.get("purchasing_customer_change_pct")),
        realized_revenue_per_unit=_num(row.get("realized_revenue_per_unit")),
        revenue_by_channel=row.get("revenue_by_channel"),
        product_contribution=row.get("product_contribution"),
        data_quality_status=row.get("data_quality_status"),
    )
