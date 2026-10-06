"""Pricing Opportunity context normalization."""
from dataclasses import dataclass,asdict
from typing import Any,Mapping
@dataclass(frozen=True)
class PricingContext:
    business_id:str; business_name:str|None; product_id:str; product_name:str|None; category:str|None
    list_price:float|None; cogs:float|None; units_sold:int|None; revenue:float|None; discount_amount:float|None
    sales_data_as_of:Any; data_as_of:Any; realized_unit_price:float|None; list_to_realized_discount_pct:float|None
    realized_gross_margin_pct:float|None; quantity_on_hand:int|None; reorder_point:int|None; inventory_observed_at:Any
    competitor_evidence_id:str|None; competitor_observed_at:Any; competitor_name:str|None; competitor_currency:str|None
    competitor_price:float|None; competitor_comparability_score:float|None; competitor_confidence:float|None
    competitor_comparable:bool|None; competitor_price_gap_amount:float|None; competitor_price_gap_pct:float|None
    sales_evidence_status:str; margin_evidence_status:str; inventory_evidence_status:str
    competitor_evidence_status:str; recommendation_readiness:str
    def to_dict(self): return asdict(self)
def _f(v): return None if v is None else float(v)
def _i(v): return None if v is None else int(v)
def build_context(r:Mapping[str,Any])->PricingContext:
    if not r.get("business_id") or not r.get("product_id"): raise ValueError("business_id and product_id are required")
    return PricingContext(str(r["business_id"]),r.get("business_name"),str(r["product_id"]),r.get("product_name"),r.get("category"),_f(r.get("list_price")),_f(r.get("cogs")),_i(r.get("units_sold")),_f(r.get("revenue")),_f(r.get("discount_amount")),r.get("sales_data_as_of"),r.get("data_as_of"),_f(r.get("realized_unit_price")),_f(r.get("list_to_realized_discount_pct")),_f(r.get("realized_gross_margin_pct")),_i(r.get("quantity_on_hand")),_i(r.get("reorder_point")),r.get("inventory_observed_at"),str(r["competitor_evidence_id"]) if r.get("competitor_evidence_id") else None,r.get("competitor_observed_at"),r.get("competitor_name"),r.get("competitor_currency"),_f(r.get("competitor_price")),_f(r.get("competitor_comparability_score")),_f(r.get("competitor_confidence")),r.get("competitor_comparable"),_f(r.get("competitor_price_gap_amount")),_f(r.get("competitor_price_gap_pct")),str(r.get("sales_evidence_status") or ""),str(r.get("margin_evidence_status") or ""),str(r.get("inventory_evidence_status") or ""),str(r.get("competitor_evidence_status") or ""),str(r.get("recommendation_readiness") or ""))
