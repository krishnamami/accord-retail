"""Evidence construction and lineage for Margin Health."""
from typing import Any
from .context import MarginContext

def build_evidence(c: MarginContext, calc: dict[str,Any]) -> list[dict[str,Any]]:
    quality=c.margin_evidence_status; confidence=1.0 if quality=="READY" else 0.0
    vals=[("GROSS_MARGIN","Current gross margin %",c.gross_margin_pct),("PRIOR_GROSS_MARGIN","Prior calendar-month gross margin %",c.prior_margin_pct),("MARGIN_CHANGE","Margin change in percentage points",c.margin_change_points),("GROSS_PROFIT","Observed gross profit",c.gross_profit),("EFFECTIVE_DISCOUNT","Observed effective discount %",c.effective_discount_pct),("UNIT_ECONOMICS","Realized unit revenue",c.realized_unit_revenue),("UNIT_COST","Realized unit cost",c.realized_unit_cost)]
    return [{"evidence_type":t,"finding":f,"value":v,"product_id":c.product_id,"period_start":c.period_start,"comparison_period_start":c.comparison_period_start,"comparison_basis":c.comparison_basis,"quality_status":quality,"confidence":confidence,"source":"agent.margin_health_context"} for t,f,v in vals if v is not None]
