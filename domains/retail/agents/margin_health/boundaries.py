"""Recommendation boundaries for Margin Health."""
from typing import Any
def evaluate_boundaries(context: Any, rules:list[dict[str,Any]]) -> dict[str,Any]:
    fired={r["rule_id"] for r in rules if r["fired"]}
    checks=[
      {"boundary_id":"BND_MAR_001","description":"Margin evidence must be decision-ready for trend conclusions","passed":context.margin_evidence_status=="READY"},
      {"boundary_id":"BND_MAR_002","description":"Partial-period totals cannot support total revenue/profit/volume comparison","passed":context.period_total_comparison_status=="READY"},
      {"boundary_id":"BND_MAR_003","description":"Margin Health cannot independently execute pricing, assortment or inventory changes","passed":True},
    ]
    if context.margin_evidence_status in ("CANNOT_DECIDE","INSUFFICIENT_MARGIN_EVIDENCE"):
      return {"status":"CANNOT_DECIDE","reason":"Required margin evidence is insufficient.","checks":checks}
    if context.margin_evidence_status=="MISSING_PRIOR_MONTH":
      return {"status":"POINT_IN_TIME_ONLY","reason":"Current margin can be observed, but margin trend cannot be inferred because the prior calendar month is missing.","checks":checks}
    if "MAR_006" in fired:
      return {"status":"CAUSE_NOT_ESTABLISHED","reason":"Discount pressure is correlated with margin compression but causality requires specialist pricing evidence.","checks":checks}
    return {"status":"WITHIN_DIAGNOSTIC_BOUNDARY","reason":"Margin condition and calendar-aware trend may be classified; specialized actions remain routed.","checks":checks}
