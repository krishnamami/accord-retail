"""Governed Inventory Exposure rules. Explicit v1 thresholds pending KB externalization."""
RULE_VERSION='inventory-exposure-v1'
def evaluate_rules(c):
    gap=c.get('reorder_gap_units'); dos=c.get('days_of_supply'); value=c.get('inventory_value'); u90=c.get('units_90d')
    defs=[('INV_001','At or below reorder point',gap is not None and gap<=0,{'reorder_gap_units_lte':0}),('INV_002','Material reorder shortfall',gap is not None and gap<=-25,{'reorder_gap_units_lte':-25}),('INV_003','Excess supply',dos is not None and dos>=180,{'days_of_supply_gte':180}),('INV_004','Slow-moving excess inventory',dos is not None and dos>=180 and u90 is not None and u90<=30,{'days_of_supply_gte':180,'units_90d_lte':30}),('INV_005','Capital exposure',dos is not None and dos>=180 and value is not None and value>=25000,{'days_of_supply_gte':180,'inventory_value_gte':25000}),('INV_006','Extreme supply exposure',dos is not None and dos>=365,{'days_of_supply_gte':365})]
    return [{'rule_id':i,'rule_version':RULE_VERSION,'description':d,'evaluated':True,'fired':bool(f),'thresholds':t} for i,d,f,t in defs]
