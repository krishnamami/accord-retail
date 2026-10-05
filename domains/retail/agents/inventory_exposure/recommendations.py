"""Decision, recommendation and specialist routing for Inventory Exposure."""
def recommend(rules,boundary):
    fired={r['rule_id'] for r in rules if r['fired']}; routes=[]
    if fired & {'INV_003','INV_004','INV_005','INV_006'}:
        routes.append({'agent':'pricing_opportunity','reason':'Excess/slow inventory may warrant governed pricing or promotion analysis; Inventory Exposure does not prescribe markdowns.'})
        routes.append({'agent':'margin_health','reason':'Evaluate unit economics before any inventory disposition or pricing action.'})
    if boundary['status']=='CANNOT_DECIDE': return {'decision':'CANNOT_DECIDE','severity':'UNKNOWN','recommendation':'Refresh inventory or demand evidence before intervention.','specialist_routes':[],'allowed_actions':['REFRESH_DATA'],'restricted_actions':['CHANGE_REORDER_POINT','CREATE_PURCHASE_ORDER','CHANGE_PRICE','DISCONTINUE_PRODUCT']}
    if 'INV_002' in fired: decision,severity,text='REPLENISHMENT_RISK','HIGH','Investigate replenishment exposure; validate demand continuity and purchasing constraints before action.'
    elif 'INV_001' in fired: decision,severity,text='REPLENISHMENT_RISK','MEDIUM','Review the product inventory position and replenishment need.'
    elif 'INV_005' in fired and 'INV_006' in fired: decision,severity,text='CAPITAL_EXPOSURE','HIGH','Prioritize review of inventory capital tied up in extreme supply exposure.'
    elif 'INV_005' in fired: decision,severity,text='CAPITAL_EXPOSURE','MEDIUM','Review inventory capital exposure and route pricing/margin analysis where appropriate.'
    elif 'INV_004' in fired: decision,severity,text='SLOW_MOVING_RISK','MEDIUM','Investigate low movement and excess supply without assuming the cause of weak demand.'
    elif 'INV_003' in fired or 'INV_006' in fired: decision,severity,text='EXCESS_INVENTORY_RISK','MEDIUM','Review excess supply and determine whether specialist pricing or margin analysis is warranted.'
    else: decision,severity,text='HEALTHY_OR_WATCH','LOW','Continue monitoring inventory position and demand velocity.'
    return {'decision':decision,'severity':severity,'recommendation':text,'specialist_routes':routes,'allowed_actions':['INVESTIGATE','ROUTE_TO_SPECIALIST','MONITOR'],'restricted_actions':['ASSERT_UNSUPPORTED_DEMAND_CAUSE','DIRECT_REORDER_POINT_CHANGE','DIRECT_PURCHASE_ORDER','DIRECT_PRICE_CHANGE','DISCONTINUE_PRODUCT']}
