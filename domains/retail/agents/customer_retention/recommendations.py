"""Decision and permitted recommendation mapping for Customer Retention."""
def recommend(rules,boundary):
    fired={r['rule_id'] for r in rules if r['fired']}
    restricted=['ASSERT_REASON_FOR_DISENGAGEMENT','AUTO_SEND_OUTREACH','AUTO_ISSUE_DISCOUNT','AUTO_CREATE_PROMOTION','OVERRIDE_CUSTOMER_PROFILE']
    if boundary['status']=='CANNOT_DECIDE': return {'decision':'CANNOT_DECIDE','severity':'UNKNOWN','recommendation':'Obtain observed transaction evidence before making a behavioral retention recommendation.','allowed_actions':['REFRESH_OR_LINK_CUSTOMER_TRANSACTION_DATA'],'restricted_actions':restricted}
    if 'RET_006' in fired: return {'decision':'ASSERTION_CONFLICT','severity':'MEDIUM','recommendation':'Preserve the source assertion and observed behavior as separate evidence; review the profile conflict while using observed behavior for diagnostic context only.','allowed_actions':['INVESTIGATE_PROFILE_CONFLICT','MONITOR','ROUTE_FOR_REVIEW'],'restricted_actions':restricted}
    if 'RET_004' in fired: decision,severity,text='CHURN_RISK','HIGH','Prioritize this customer for governed retention review based on prolonged observed inactivity.'
    elif 'RET_003' in fired: decision,severity,text='DORMANT_RISK','MEDIUM','Review the customer for a governed retention intervention; do not infer the cause of inactivity.'
    elif 'RET_002' in fired: decision,severity,text='RETENTION_WATCH','LOW','Monitor the customer as observed recency approaches the dormant threshold.'
    else: decision,severity,text='ACTIVE_HEALTHY','LOW','No behavioral retention intervention is indicated from current observed recency.'
    return {'decision':decision,'severity':severity,'recommendation':text,'allowed_actions':['MONITOR','INVESTIGATE','ROUTE_FOR_GOVERNED_RETENTION_REVIEW'],'restricted_actions':restricted}
