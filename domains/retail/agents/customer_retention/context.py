"""Customer Retention context normalization."""
from dataclasses import dataclass,asdict
from typing import Any,Mapping
@dataclass(frozen=True)
class RetentionContext:
    business_id:str; customer_id:str; acquisition_channel:str|None
    profile_first_purchase:Any; profile_last_purchase:Any; profile_repeat_count:int|None; asserted_churn_status:str|None
    observed_orders:int; observed_revenue:float|None; observed_first_purchase:Any; observed_last_purchase:Any; data_as_of:Any
    behavioral_evidence_available:bool; recency_days:int|None; profile_recency_days:int|None; repeat_customer:bool|None
    observed_orders_per_day:float|None; observed_behavior_status:str|None; profile_behavior_status:str|None
    assertion_conflict:bool; conflict_reason:str|None; cohort_month:Any; inactive_90d:bool|None
    retention_evidence_status:str; retention_decision_readiness:str
    def to_dict(self): return asdict(self)
def _i(v): return None if v is None else int(v)
def _f(v): return None if v is None else float(v)
def build_context(r:Mapping[str,Any])->RetentionContext:
    if not r.get('business_id') or not r.get('customer_id'): raise ValueError('business_id and customer_id are required')
    return RetentionContext(str(r['business_id']),str(r['customer_id']),r.get('acquisition_channel'),r.get('profile_first_purchase'),r.get('profile_last_purchase'),_i(r.get('profile_repeat_count')),r.get('asserted_churn_status'),_i(r.get('observed_orders')) or 0,_f(r.get('observed_revenue')),r.get('observed_first_purchase'),r.get('observed_last_purchase'),r.get('data_as_of'),bool(r.get('behavioral_evidence_available')),_i(r.get('recency_days')),_i(r.get('profile_recency_days')),r.get('repeat_customer'),_f(r.get('observed_orders_per_day')),r.get('observed_behavior_status'),r.get('profile_behavior_status'),bool(r.get('assertion_conflict')),r.get('conflict_reason'),r.get('cohort_month'),r.get('inactive_90d'),str(r.get('retention_evidence_status') or ''),str(r.get('retention_decision_readiness') or ''))
