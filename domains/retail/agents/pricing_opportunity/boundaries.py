"""Recommendation boundary evaluation for Pricing Opportunity."""
def evaluate_boundaries(c,rules):
    checks=[{"boundary_id":"BND_PRC_001","description":"Observed sales and unit economics are required","passed":c.sales_evidence_status=="READY" and c.margin_evidence_status=="READY"},{"boundary_id":"BND_PRC_002","description":"Competitor-driven recommendations require fresh comparable evidence","passed":c.competitor_evidence_status=="READY"},{"boundary_id":"BND_PRC_003","description":"Agent cannot autonomously change product price","passed":True},{"boundary_id":"BND_PRC_004","description":"Agent cannot infer demand elasticity or causal lift from observational evidence","passed":True}]
    if c.recommendation_readiness=="CANNOT_DECIDE": return {"status":"CANNOT_DECIDE","reason":"Minimum sales or unit-economics evidence is unavailable.","checks":checks}
    if c.competitor_evidence_status!="READY": return {"status":"LIMITED_COMPETITOR_EVIDENCE","reason":c.competitor_evidence_status,"checks":checks}
    if c.inventory_evidence_status!="READY": return {"status":"LIMITED_INVENTORY_EVIDENCE","reason":c.inventory_evidence_status,"checks":checks}
    return {"status":"WITHIN_DIAGNOSTIC_BOUNDARY","reason":"Evidence supports pricing diagnostics; any price change remains governed.","checks":checks}
