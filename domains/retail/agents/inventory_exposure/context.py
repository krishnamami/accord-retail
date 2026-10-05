"""Inventory Exposure context normalization."""
from dataclasses import dataclass,asdict
from typing import Any,Mapping
@dataclass(frozen=True)
class InventoryContext:
    business_id:str; business_name:str; product_id:str; product_name:str; category:str|None
    quantity_on_hand:int|None; reorder_point:int|None; last_updated:Any; cogs:float|None; list_price:float|None
    data_as_of:Any; latest_sale_date:Any; inventory_value:float|None; units_30d:float|None; units_90d:float|None
    daily_sales_velocity_90d:float|None; days_of_supply:float|None; reorder_gap_units:int|None; at_or_below_reorder:bool
    velocity_band:str|None; supply_band:str|None; excess_supply_candidate:bool; slow_moving_candidate:bool
    capital_exposure_candidate:bool; inventory_freshness_status:str|None; inventory_evidence_status:str|None
    def to_dict(self): return asdict(self)
def _f(v): return None if v is None else float(v)
def _i(v): return None if v is None else int(v)
def build_context(r:Mapping[str,Any])->InventoryContext:
    if not r.get('business_id') or not r.get('product_id'): raise ValueError('business_id and product_id are required')
    return InventoryContext(str(r['business_id']),str(r.get('business_name') or ''),str(r['product_id']),str(r.get('product_name') or ''),r.get('category'),_i(r.get('quantity_on_hand')),_i(r.get('reorder_point')),r.get('last_updated'),_f(r.get('cogs')),_f(r.get('list_price')),r.get('data_as_of'),r.get('latest_sale_date'),_f(r.get('inventory_value')),_f(r.get('units_30d')),_f(r.get('units_90d')),_f(r.get('daily_sales_velocity_90d')),_f(r.get('days_of_supply')),_i(r.get('reorder_gap_units')),bool(r.get('at_or_below_reorder')),r.get('velocity_band'),r.get('supply_band'),bool(r.get('excess_supply_candidate')),bool(r.get('slow_moving_candidate')),bool(r.get('capital_exposure_candidate')),r.get('inventory_freshness_status'),r.get('inventory_evidence_status'))
