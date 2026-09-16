#!/usr/bin/env python3
import psycopg2
from psycopg2.extras import DictCursor
from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Verdict(Enum):
    RECOMMENDED = "RECOMMENDED"
    NOT_RECOMMENDED = "NOT_RECOMMENDED"
    CONDITIONAL = "CONDITIONAL"
    REQUIRES_APPROVAL = "REQUIRES_APPROVAL"

@dataclass
class ActionScoringRule:
    rule_id: str
    rule_name: str
    action_type: str
    bottleneck_type: str
    score_metric: str
    threshold: float
    operator: str
    verdict: str
    confidence: float
    priority: int
    version_number: int

@dataclass
class Action:
    action_name: str
    action_type: str
    bottleneck_type: str
    roi: Optional[float] = None
    payback_weeks: Optional[int] = None
    investment_usd: Optional[float] = None
    risk_level: Optional[int] = None
    customer_impact_pct: Optional[float] = None
    
    def get_metric_value(self, metric_name: str) -> Optional[float]:
        if metric_name == 'roi':
            return self.roi
        elif metric_name == 'payback_weeks':
            return self.payback_weeks
        elif metric_name == 'investment_usd':
            return self.investment_usd
        elif metric_name == 'risk_level':
            return self.risk_level
        elif metric_name == 'customer_impact_pct':
            return self.customer_impact_pct
        return None

@dataclass
class ScoringResult:
    action_name: str
    verdicts: List[str]
    final_verdict: str
    confidence: float
    rules_applied: List[ActionScoringRule]
    reasoning: Dict
    
    def __post_init__(self):
        priority_order = [Verdict.RECOMMENDED.value, Verdict.CONDITIONAL.value, Verdict.REQUIRES_APPROVAL.value, Verdict.NOT_RECOMMENDED.value]
        for v in priority_order:
            if v in self.verdicts:
                self.final_verdict = v
                break

class ActionRuleEngine:
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.conn = None
        self.rules_cache = {}
    
    def connect(self) -> psycopg2.extensions.connection:
        if self.conn is None:
            self.conn = psycopg2.connect(self.database_url)
        return self.conn
    
    def close(self):
        if self.conn:
            self.conn.close()
    
    def get_active_rules(self, action_type: str, bottleneck_type: str) -> List[ActionScoringRule]:
        cache_key = (action_type, bottleneck_type)
        if cache_key in self.rules_cache:
            return self.rules_cache[cache_key]
        
        conn = self.connect()
        cursor = conn.cursor(cursor_factory=DictCursor)
        
        try:
            cursor.execute("""
                SELECT r.rule_id, r.rule_name, r.action_type, r.bottleneck_type,
                       r.score_metric, r.threshold, r.operator, r.verdict,
                       r.confidence, r.priority, v.rule_version_number
                FROM ontology.kb_action_scoring_rule r
                JOIN audit.scd_action_scoring_rule_version v ON r.rule_id = v.rule_id
                WHERE v.is_active = true
                  AND ((r.action_type = %s AND r.bottleneck_type = %s)
                       OR (r.action_type = 'ANY' AND r.bottleneck_type = 'ANY')
                       OR (r.action_type = 'ANY' AND r.bottleneck_type = %s)
                       OR (r.action_type = %s AND r.bottleneck_type = 'ANY'))
                ORDER BY r.priority ASC
            """, (action_type, bottleneck_type, bottleneck_type, action_type))
            
            rules = [ActionScoringRule(rule_id=str(row['rule_id']), rule_name=row['rule_name'], action_type=row['action_type'],
                                       bottleneck_type=row['bottleneck_type'], score_metric=row['score_metric'],
                                       threshold=float(row['threshold']), operator=row['operator'], verdict=row['verdict'],
                                       confidence=float(row['confidence']), priority=row['priority'],
                                       version_number=row['rule_version_number']) for row in cursor.fetchall()]
            
            self.rules_cache[cache_key] = rules
            logger.info(f"Loaded {len(rules)} active rules for {action_type}/{bottleneck_type}")
            return rules
        finally:
            cursor.close()
    
    def evaluate_operator(self, actual: float, threshold: float, operator: str) -> bool:
        if operator == '>': return actual > threshold
        elif operator == '<': return actual < threshold
        elif operator == '>=': return actual >= threshold
        elif operator == '<=': return actual <= threshold
        elif operator == '=': return actual == threshold
        elif operator == '!=': return actual != threshold
        else: raise ValueError(f"Unknown operator: {operator}")
    
    def score_action(self, action: Action, decision_id: Optional[str] = None, business_id: Optional[str] = None) -> ScoringResult:
        rules = self.get_active_rules(action.action_type, action.bottleneck_type)
        if not rules:
            return ScoringResult(action_name=action.action_name, verdicts=["CONDITIONAL"], final_verdict="CONDITIONAL", confidence=0.5, rules_applied=[], reasoning={"note": "No scoring rules found"})
        
        verdicts, confidences, rules_fired, rule_details = [], [], [], []
        for rule in rules:
            metric_value = action.get_metric_value(rule.score_metric)
            if metric_value is None: continue
            rule_matched = self.evaluate_operator(metric_value, rule.threshold, rule.operator)
            if rule_matched:
                verdicts.append(rule.verdict)
                confidences.append(rule.confidence)
                rules_fired.append(rule)
                rule_details.append({"rule_name": rule.rule_name, "metric": rule.score_metric, "actual_value": metric_value,
                                     "threshold": rule.threshold, "operator": rule.operator, "verdict": rule.verdict,
                                     "confidence": rule.confidence, "priority": rule.priority})
                self._log_rule_application(decision_id, business_id, rule, action, metric_value, True, rule.verdict, rule.confidence)
        
        if not verdicts:
            verdicts = ["NOT_RECOMMENDED"]
            confidences = [0.5]
        
        result = ScoringResult(action_name=action.action_name, verdicts=verdicts, final_verdict="", 
                              confidence=sum(confidences) / len(confidences) if confidences else 0.5,
                              rules_applied=rules_fired,
                              reasoning={"rules_applied": rule_details, "num_rules_fired": len(rules_fired),
                                        "num_rules_total": len(rules), "final_confidence": sum(confidences) / len(confidences) if confidences else 0.5})
        result.__post_init__()
        logger.info(f"Scored action '{action.action_name}': verdict={result.final_verdict}, confidence={result.confidence:.2f}")
        return result
    
    def _log_rule_application(self, decision_id, business_id, rule, action, metric_value, rule_matched, verdict, confidence):
        conn = self.connect()
        cursor = conn.cursor()
        try:
            cursor.execute("""INSERT INTO audit.action_scoring_rule_application
                (decision_id, business_id, rule_id, rule_version_number, action_name, action_type, bottleneck_type,
                 score_metric, metric_value, threshold, operator, rule_matched, verdict_assigned, confidence)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (decision_id, business_id, rule.rule_id, rule.version_number, action.action_name, action.action_type,
                 action.bottleneck_type, rule.score_metric, metric_value, rule.threshold, rule.operator,
                 rule_matched, verdict, confidence))
            conn.commit()
        except Exception as e:
            logger.error(f"Failed to log rule application: {e}")
        finally:
            cursor.close()
