"""Margin Health orchestration: context -> calculations -> evidence -> rules -> boundaries -> recommendation."""
from datetime import datetime,timezone
from typing import Any,Mapping
from .context import build_context
from .calculations import calculate
from .evidence import build_evidence
from .rules import evaluate_rules,RULE_VERSION
from .boundaries import evaluate_boundaries
from .recommendations import recommend
AGENT_NAME="margin_health"; AGENT_VERSION="1.0.0"; METRIC_VERSION="margin-context-v2"
def run(row:Mapping[str,Any],*,kb_version:str|None=None)->dict[str,Any]:
    c=build_context(row); calc=calculate(c); evidence=build_evidence(c,calc); rules=evaluate_rules(calc); boundary=evaluate_boundaries(c,rules); rec=recommend(rules,boundary); fired=[r for r in rules if r["fired"]]
    return {"agent":{"name":AGENT_NAME,"version":AGENT_VERSION},"business_id":c.business_id,"product_id":c.product_id,"product_name":c.product_name,"decision":rec["decision"],"severity":rec["severity"],"recommendation":rec["recommendation"],"confidence":1.0 if c.margin_evidence_status=="READY" else 0.5 if c.margin_evidence_status=="MISSING_PRIOR_MONTH" else 0.0,"context":c.to_dict(),"calculations":calc,"evidence":evidence,"rules_evaluated":rules,"rules_fired":fired,"boundary":boundary,"specialist_routes":rec["specialist_routes"],"allowed_actions":rec["allowed_actions"],"restricted_actions":rec["restricted_actions"],"versions":{"kb_version":kb_version,"rule_version":RULE_VERSION,"metric_version":METRIC_VERSION},"audit":{"decision_at":datetime.now(timezone.utc).isoformat(),"source_view":"agent.margin_health_context","comparison_basis":c.comparison_basis,"data_as_of":c.data_as_of}}
