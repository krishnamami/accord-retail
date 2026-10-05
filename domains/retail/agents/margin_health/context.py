"""Margin Health context normalization from agent.margin_health_context."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any, Mapping

@dataclass(frozen=True)
class MarginContext:
    business_id: str; product_id: str; product_name: str; category: str | None
    cogs: float | None; list_price: float | None; period_start: Any; comparison_period_start: Any
    comparison_basis: str | None; data_as_of: Any; period_data_through: Any; is_current_period: bool
    observed_days: int | None; units_sold: float | None; revenue: float | None; cogs_total: float | None
    discount_amount: float | None; gross_profit: float | None; gross_margin_pct: float | None
    realized_unit_revenue: float | None; realized_unit_cost: float | None; effective_discount_pct: float | None
    prior_margin_pct: float | None; margin_change_points: float | None; prior_revenue: float | None
    prior_gross_profit: float | None; prior_units_sold: float | None; prior_effective_discount_pct: float | None
    margin_evidence_status: str | None; period_total_comparison_status: str | None
    def to_dict(self): return asdict(self)

def _f(v): return None if v is None else float(v)
def build_context(row: Mapping[str, Any]) -> MarginContext:
    if not row.get("business_id") or not row.get("product_id"): raise ValueError("business_id and product_id are required")
    return MarginContext(
        str(row["business_id"]),str(row["product_id"]),str(row.get("product_name") or ""),row.get("category"),
        _f(row.get("cogs")),_f(row.get("list_price")),row.get("period_start"),row.get("comparison_period_start"),row.get("comparison_basis"),
        row.get("data_as_of"),row.get("period_data_through"),bool(row.get("is_current_period")),int(row["observed_days"]) if row.get("observed_days") is not None else None,
        _f(row.get("units_sold")),_f(row.get("revenue")),_f(row.get("cogs_total")),_f(row.get("discount_amount")),_f(row.get("gross_profit")),
        _f(row.get("gross_margin_pct")),_f(row.get("realized_unit_revenue")),_f(row.get("realized_unit_cost")),_f(row.get("effective_discount_pct")),
        _f(row.get("prior_margin_pct")),_f(row.get("margin_change_points")),_f(row.get("prior_revenue")),_f(row.get("prior_gross_profit")),
        _f(row.get("prior_units_sold")),_f(row.get("prior_effective_discount_pct")),row.get("margin_evidence_status"),row.get("period_total_comparison_status"))
