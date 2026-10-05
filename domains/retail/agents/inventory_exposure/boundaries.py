"""Recommendation boundaries for Inventory Exposure."""
def evaluate_boundaries(c,rules):
    checks=[{'boundary_id':'BND_INV_001','description':'Inventory and demand evidence must be ready','passed':c.inventory_evidence_status=='READY'},{'boundary_id':'BND_INV_002','description':'Inventory Exposure cannot independently change reorder points, purchasing, pricing or assortment','passed':True},{'boundary_id':'BND_INV_003','description':'Long supply does not by itself establish the cause of weak demand','passed':True}]
    if c.inventory_evidence_status!='READY': return {'status':'CANNOT_DECIDE','reason':'Inventory evidence is stale or insufficient.','checks':checks}
    return {'status':'WITHIN_DIAGNOSTIC_BOUNDARY','reason':'Inventory position, movement and financial exposure may be classified; operational actions remain governed or routed.','checks':checks}
