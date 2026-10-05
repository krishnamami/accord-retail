"""Evidence construction and lineage for Customer Retention."""
from .context import RetentionContext
def build_evidence(c:RetentionContext,calc):
    vals=[('OBSERVED_ORDERS','Observed transaction count',c.observed_orders,'transaction'),('OBSERVED_REVENUE','Observed historical revenue',c.observed_revenue,'transaction'),('OBSERVED_LAST_PURCHASE','Observed last purchase',c.observed_last_purchase,'transaction'),('OBSERVED_RECENCY','Days since observed purchase',c.recency_days,'derived'),('OBSERVED_BEHAVIOR','Behavioral retention status',c.observed_behavior_status,'derived'),('PROFILE_ASSERTION','Source-system churn assertion',c.asserted_churn_status,'profile'),('ASSERTION_CONFLICT','Profile assertion conflicts with observed behavior',c.assertion_conflict,'derived')]
    confidence=1.0 if c.retention_evidence_status=='READY' else 0.0
    return [{'evidence_type':t,'finding':f,'value':v,'evidence_class':cls,'business_id':c.business_id,'customer_id':c.customer_id,'data_as_of':c.data_as_of,'quality_status':c.retention_evidence_status,'confidence':confidence,'source':'agent.customer_retention_context'} for t,f,v,cls in vals if v is not None]
