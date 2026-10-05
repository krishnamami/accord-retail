"""Decision, recommendation and specialist routing for Margin Health."""
from typing import Any
def recommend(rules:list[dict[str,Any]], boundary:dict[str,Any])->dict[str,Any]:
    fired={r["rule_id"] for r in rules if r["fired"]}; routes=[]
    if "MAR_006" in fired: routes.append({"agent":"pricing_opportunity","reason":"Discount pressure accompanies margin compression; validate pricing evidence."})
    if "MAR_001" in fired: routes.append({"agent":"pricing_opportunity","reason":"Negative unit economics require governed pricing review before action."})
    if boundary["status"]=="CANNOT_DECIDE": return {"decision":"CANNOT_DECIDE","severity":"UNKNOWN","recommendation":"Acquire sufficient margin evidence.","specialist_routes":[],"allowed_actions":["REFRESH_DATA"],"restricted_actions":["CHANGE_PRICE","CHANGE_INVENTORY","DISCONTINUE_PRODUCT"]}
    if boundary["status"]=="POINT_IN_TIME_ONLY":
      decision="MARGIN_POINT_IN_TIME_WARNING" if "MAR_001" in fired or "MAR_002" in fired else "MARGIN_POINT_IN_TIME"
      severity="HIGH" if "MAR_001" in fired else ("MEDIUM" if "MAR_002" in fired else "LOW")
      text="Review current margin condition, but do not infer a trend until the missing prior-month evidence is available."
    elif "MAR_001" in fired or "MAR_004" in fired: decision,severity,text="MARGIN_RISK","HIGH","Prioritize margin diagnosis and route supported drivers to governed specialist agents."
    elif "MAR_002" in fired or "MAR_003" in fired: decision,severity,text="MARGIN_RISK","MEDIUM","Investigate margin compression and unit economics before taking corrective action."
    elif "MAR_005" in fired: decision,severity,text="MARGIN_OPPORTUNITY","MEDIUM","Review margin expansion drivers and determine whether they are repeatable."
    else: decision,severity,text="HEALTHY_OR_WATCH","LOW","Continue monitoring calendar-comparable margin health."
    return {"decision":decision,"severity":severity,"recommendation":text,"specialist_routes":routes,"allowed_actions":["INVESTIGATE","ROUTE_TO_SPECIALIST","MONITOR"],"restricted_actions":["ASSERT_UNSUPPORTED_CAUSE","DIRECT_PRICE_CHANGE","DIRECT_INVENTORY_CHANGE","DISCONTINUE_PRODUCT"]}
