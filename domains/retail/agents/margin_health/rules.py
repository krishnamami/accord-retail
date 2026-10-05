"""Governed rules for Margin Health. Thresholds are explicit v1 defaults pending KB externalization."""
from typing import Any
RULE_VERSION="margin-health-v1"
def evaluate_rules(c: dict[str,Any]) -> list[dict[str,Any]]:
    m=c.get("gross_margin_pct"); d=c.get("margin_change_points"); dc=c.get("discount_change_points")
    defs=[
      ("MAR_001","Negative gross margin",m is not None and m<0,{"gross_margin_pct_lt":0}),
      ("MAR_002","Low gross margin",m is not None and 0<=m<20,{"gross_margin_pct_lt":20}),
      ("MAR_003","Material margin compression",d is not None and d<=-10,{"margin_change_points_lte":-10}),
      ("MAR_004","Severe margin compression",d is not None and d<=-25,{"margin_change_points_lte":-25}),
      ("MAR_005","Material margin expansion",d is not None and d>=10,{"margin_change_points_gte":10}),
      ("MAR_006","Discount pressure signal",d is not None and d<0 and dc is not None and dc>=5,{"margin_declining":True,"discount_change_points_gte":5}),
    ]
    return [{"rule_id":i,"rule_version":RULE_VERSION,"description":desc,"evaluated":True,"fired":bool(f),"thresholds":th} for i,desc,f,th in defs]
