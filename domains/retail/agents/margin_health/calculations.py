"""Deterministic calculations for Margin Health."""
from typing import Any
from .context import MarginContext

def calculate(c: MarginContext) -> dict[str, Any]:
    discount_change = None if c.effective_discount_pct is None or c.prior_effective_discount_pct is None else round(c.effective_discount_pct-c.prior_effective_discount_pct,2)
    return {
      "gross_margin_pct":c.gross_margin_pct,"prior_margin_pct":c.prior_margin_pct,"margin_change_points":c.margin_change_points,
      "gross_profit":c.gross_profit,"effective_discount_pct":c.effective_discount_pct,"prior_effective_discount_pct":c.prior_effective_discount_pct,
      "discount_change_points":discount_change,"realized_unit_revenue":c.realized_unit_revenue,"realized_unit_cost":c.realized_unit_cost,
      "trace":[
        {"metric":"gross_margin_pct","formula":"100*(revenue-cogs_total)/revenue","result":c.gross_margin_pct},
        {"metric":"margin_change_points","formula":"gross_margin_pct-prior_margin_pct","result":c.margin_change_points},
        {"metric":"discount_change_points","formula":"effective_discount_pct-prior_effective_discount_pct","result":discount_change}
      ]}
