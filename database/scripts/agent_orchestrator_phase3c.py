#!/usr/bin/env python3
import asyncio
import json
import logging
import psycopg2
from psycopg2.extras import DictCursor
from uuid import uuid4
from dotenv import load_dotenv
import os
from anthropic import Anthropic
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BaseAgent:
    def _parse_json_response(self, response_text: str) -> dict:
        text = response_text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        try:
            return json.loads(text)
        except:
            return {"error": "parse failed", "raw": text[:200]}

class DecisionReadinessAgent(BaseAgent):
    def __init__(self, client):
        self.client = client
    
    async def run(self, decision_object: dict) -> tuple:
        prompt = f"""Audit this decision. Sufficient evidence to decide?
Decision: {json.dumps(decision_object, indent=2, default=str)}
Respond ONLY with JSON: {{"decision_readiness": "READY", "rationale": "..."}}
Options: READY, CONDITIONAL, CANNOT_DECIDE"""
        try:
            msg = self.client.messages.create(model="claude-sonnet-4-6", max_tokens=1000, messages=[{"role": "user", "content": prompt}])
            output = self._parse_json_response(msg.content[0].text)
            return output.get("decision_readiness", "READY"), output
        except Exception as e:
            return "CANNOT_DECIDE", {"error": str(e)}

class RecommendationExplainerAgent(BaseAgent):
    def __init__(self, client):
        self.client = client
    
    async def run(self, decision_object: dict) -> dict:
        prompt = f"""Explain this recommendation.
Decision: {json.dumps(decision_object, indent=2, default=str)}
Respond ONLY with JSON: {{"summary": "...", "why_now": {{}}, "why_this_option": {{}}, "why_not_other_options": [], "key_evidence": [], "assumptions_to_watch": []}}"""
        try:
            msg = self.client.messages.create(model="claude-sonnet-4-6", max_tokens=1500, messages=[{"role": "user", "content": prompt}])
            return self._parse_json_response(msg.content[0].text)
        except Exception as e:
            return {"error": str(e)}

class RiskAssessorAgent(BaseAgent):
    def __init__(self, client):
        self.client = client
    
    async def run(self, decision_object: dict) -> dict:
        prompt = f"""Assess risks in this recommendation.
Decision: {json.dumps(decision_object, indent=2, default=str)}
Respond ONLY with JSON: {{"overall_risk": "MEDIUM", "overall_risk_rationale": "...", "risks": [], "blocking_risks": [], "monitoring_signals": [], "approval_guardrails": []}}"""
        try:
            msg = self.client.messages.create(model="claude-sonnet-4-6", max_tokens=1500, messages=[{"role": "user", "content": prompt}])
            return self._parse_json_response(msg.content[0].text)
        except Exception as e:
            return {"error": str(e)}

class OutcomePredictorAgent(BaseAgent):
    def __init__(self, client):
        self.client = client
    
    async def run(self, decision_object: dict) -> dict:
        prompt = f"""Predict 30/60/90 day outcomes.
Decision: {json.dumps(decision_object, indent=2, default=str)}
Respond ONLY with JSON: {{"day_30": {{"headline": "..."}}, "day_60": {{"headline": "..."}}, "day_90": {{"headline": "..."}}, "confidence_commentary": "...", "assumptions_that_matter": [], "measurement_dashboard": {{}}}}"""
        try:
            msg = self.client.messages.create(model="claude-sonnet-4-6", max_tokens=2000, messages=[{"role": "user", "content": prompt}])
            return self._parse_json_response(msg.content[0].text)
        except Exception as e:
            return {"error": str(e)}

class ScenarioAgent(BaseAgent):
    def __init__(self, client):
        self.client = client
    
    async def run(self, decision_object: dict) -> dict:
        prompt = f"""Compare scenarios for this decision.
Decision: {json.dumps(decision_object, indent=2, default=str)}
Respond ONLY with JSON: {{"scenario_name": "...", "comparison_narrative": "...", "scenario_tradeoff_analysis": [], "recommendation_impact": "...", "when_to_use_this_scenario": "..."}}"""
        try:
            msg = self.client.messages.create(model="claude-sonnet-4-6", max_tokens=1500, messages=[{"role": "user", "content": prompt}])
            return self._parse_json_response(msg.content[0].text)
        except Exception as e:
            return {"error": str(e)}

class Phase3COrchestrator:
    def __init__(self, db_url, client):
        self.db_url = db_url
        self.client = client
        self.readiness = DecisionReadinessAgent(client)
        self.explainer = RecommendationExplainerAgent(client)
        self.risk = RiskAssessorAgent(client)
        self.outcome = OutcomePredictorAgent(client)
        self.scenario = ScenarioAgent(client)
    
    async def run_for_decision(self, decision_id):
        logger.info(f"Phase 3C: {decision_id}")
        exec_id = str(uuid4())
        
        conn = psycopg2.connect(self.db_url)
        cursor = conn.cursor(cursor_factory=DictCursor)
        cursor.execute("SELECT * FROM runtime.decision WHERE decision_id = %s", (decision_id,))
        decision = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not decision:
            return {"error": "not found"}
        
        biz_id = decision['business_id']
        conn = psycopg2.connect(self.db_url)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO runtime.agent_execution (execution_id, decision_id, business_id, execution_status, triggered_by) VALUES (%s, %s, %s, 'IN_PROGRESS', 'orchestrator')", (exec_id, decision_id, biz_id))
        conn.commit()
        cursor.close()
        conn.close()
        
        decision_dict = dict(decision)
        readiness_verdict, readiness_output = await self.readiness.run(decision_dict)
        conn = psycopg2.connect(self.db_url)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO runtime.agent_decision_readiness (decision_id, execution_id, decision_readiness, readiness_rationale) VALUES (%s, %s, %s, %s)", (decision_id, exec_id, readiness_verdict, json.dumps(readiness_output, default=str)))
        conn.commit()
        cursor.close()
        conn.close()
        
        if readiness_verdict == "CANNOT_DECIDE":
            conn = psycopg2.connect(self.db_url)
            cursor = conn.cursor()
            cursor.execute("UPDATE runtime.agent_execution SET execution_status='COMPLETED', readiness_agent_status='COMPLETED', execution_completed_at=NOW() WHERE execution_id=%s", (exec_id,))
            conn.commit()
            cursor.close()
            conn.close()
            return {"execution_id": exec_id, "decision_id": decision_id, "readiness_verdict": readiness_verdict, "agents_run": ["readiness"]}
        
        logger.info(f"[{readiness_verdict}] Running 4 parallel agents...")
        start = time.time()
        
        exp_task = self.explainer.run(decision_dict)
        risk_task = self.risk.run(decision_dict)
        out_task = self.outcome.run(decision_dict)
        scen_task = self.scenario.run(decision_dict)
        
        exp_out, risk_out, out_out, scen_out = await asyncio.gather(exp_task, risk_task, out_task, scen_task)
        
        elapsed = int((time.time() - start) * 1000)
        
        conn = psycopg2.connect(self.db_url)
        cursor = conn.cursor()
        
        cursor.execute("INSERT INTO runtime.agent_recommendation_explainer (decision_id, execution_id, summary) VALUES (%s, %s, %s)", (decision_id, exec_id, exp_out.get("summary", "")))
        cursor.execute("INSERT INTO runtime.agent_risk_assessment (decision_id, execution_id, overall_risk, overall_risk_rationale) VALUES (%s, %s, %s, %s)", (decision_id, exec_id, risk_out.get("overall_risk", "MEDIUM"), risk_out.get("overall_risk_rationale", "")))
        cursor.execute("INSERT INTO runtime.agent_outcome_prediction (decision_id, execution_id, day_30_summary, day_60_summary, day_90_summary) VALUES (%s, %s, %s, %s, %s)", (decision_id, exec_id, out_out.get("day_30", {}).get("headline", ""), out_out.get("day_60", {}).get("headline", ""), out_out.get("day_90", {}).get("headline", "")))
        cursor.execute("INSERT INTO runtime.agent_scenario_analysis (decision_id, execution_id, comparison_narrative, recommendation_impact) VALUES (%s, %s, %s, %s)", (decision_id, exec_id, scen_out.get("comparison_narrative", ""), scen_out.get("recommendation_impact", "")))
        cursor.execute("UPDATE runtime.agent_execution SET execution_status='COMPLETED', readiness_agent_status='COMPLETED', explainer_agent_status='COMPLETED', risk_agent_status='COMPLETED', outcome_agent_status='COMPLETED', scenario_agent_status='COMPLETED', execution_duration_ms=%s, execution_completed_at=NOW() WHERE execution_id=%s", (elapsed, exec_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return {"execution_id": exec_id, "decision_id": decision_id, "readiness_verdict": readiness_verdict, "agents_run": ["readiness", "explainer", "risk", "outcome", "scenario"], "elapsed_ms": elapsed}
