"""Governed Customer Retention rules. Thresholds are explicit v1 policy pending KB externalization."""
RULE_VERSION='customer-retention-v1'
def evaluate_rules(c):
    rec=c.get('recency_days'); orders=c.get('observed_orders') or 0; conflict=bool(c.get('assertion_conflict'))
    defs=[('RET_001','Recent observed activity',rec is not None and rec<=60,{'recency_days_lte':60}),('RET_002','Retention watch window',rec is not None and 61<=rec<=90,{'recency_days_gte':61,'recency_days_lte':90}),('RET_003','Dormant behavioral window',rec is not None and 91<=rec<=180,{'recency_days_gte':91,'recency_days_lte':180}),('RET_004','Churn-risk behavioral window',rec is not None and rec>180,{'recency_days_gt':180}),('RET_005','Repeat observed customer',orders>=2,{'observed_orders_gte':2}),('RET_006','Profile assertion conflicts with observed behavior',conflict,{'assertion_conflict':True})]
    return [{'rule_id':i,'rule_version':RULE_VERSION,'description':d,'evaluated':True,'fired':bool(f),'thresholds':t} for i,d,f,t in defs]
