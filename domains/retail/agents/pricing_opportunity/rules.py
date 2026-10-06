"""Governed business-rule evaluation for Pricing Opportunity."""
RULE_VERSION="pricing-opportunity-v1"
def evaluate_rules(c):
    gap=c.get("competitor_price_gap_pct"); margin=c.get("realized_gross_margin_pct"); discount=c.get("list_to_realized_discount_pct")
    defs=[("PRC_001","Competitor materially above realized price",gap is not None and gap>=10,{"competitor_gap_pct_gte":10}),("PRC_002","Competitor materially below realized price",gap is not None and gap<=-10,{"competitor_gap_pct_lte":-10}),("PRC_003","Heavy realized discounting",discount is not None and discount>=15,{"discount_pct_gte":15}),("PRC_004","Low realized gross margin",margin is not None and margin<20,{"gross_margin_pct_lt":20}),("PRC_005","Healthy realized margin",margin is not None and margin>=30,{"gross_margin_pct_gte":30})]
    return [{"rule_id":i,"rule_version":RULE_VERSION,"description":d,"evaluated":True,"fired":bool(f),"thresholds":t} for i,d,f,t in defs]
