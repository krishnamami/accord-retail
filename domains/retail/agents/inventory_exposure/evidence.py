"""Evidence construction and lineage for Inventory Exposure."""
from .context import InventoryContext
def build_evidence(c:InventoryContext,calc):
    confidence=1.0 if c.inventory_evidence_status=='READY' else 0.0
    vals=[('INVENTORY_POSITION','Quantity on hand',c.quantity_on_hand),('REORDER_POINT','Configured reorder point',c.reorder_point),('REORDER_GAP','Units above/below reorder point',c.reorder_gap_units),('DEMAND_30D','Units sold in trailing 30 days',c.units_30d),('DEMAND_90D','Units sold in trailing 90 days',c.units_90d),('SALES_VELOCITY','Daily sales velocity over 90 days',c.daily_sales_velocity_90d),('DAYS_OF_SUPPLY','Estimated days of supply',c.days_of_supply),('INVENTORY_VALUE','Inventory value at COGS',c.inventory_value)]
    return [{'evidence_type':t,'finding':f,'value':v,'business_id':c.business_id,'product_id':c.product_id,'data_as_of':c.data_as_of,'latest_sale_date':c.latest_sale_date,'quality_status':c.inventory_evidence_status,'confidence':confidence,'source':'agent.inventory_exposure_context'} for t,f,v in vals if v is not None]
