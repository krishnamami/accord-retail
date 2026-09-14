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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AgentOrchestrator:
    def __init__(self, database_url, anthropic_client):
        self.database_url = database_url
        self.client = anthropic_client
    
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
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            return {"error": str(e), "raw_response": text}
    
    async def run_for_decision(self, decision_id):
        logger.info(f"\n{'='*70}")
        logger.info(f"AGENT ORCHESTRATOR: Starting for decision {decision_id}")
        logger.info(f"{'='*70}\n")
        
        execution_id = str(uuid4())
        
        conn = psycopg2.connect(self.database_url)
        cursor = conn.cursor(cursor_factory=DictCursor)
        cursor.execute("SELECT * FROM runtime.decision WHERE decision_id = %s", (decision_id,))
        decision = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not decision:
            logger.error(f"Decision {decision_id} not found")
            return {"error": "Decision not found"}
        
        business_id = decision['business_id']
        
        conn = psycopg2.connect(self.database_url)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO runtime.agent_execution 
            (execution_id, decision_id, business_id, execution_status, triggered_by)
            VALUES (%s, %s, %s, 'IN_PROGRESS', 'orchestrator')
        """, (execution_id, decision_id, business_id))
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"[GATE] Running Decision Readiness Agent...")
        
        prompt = f"""You are a decision quality auditor. Is there sufficient evidence to decide?

Decision ID: {decision_id}
Recommendation: {decision.get('reasoning_json', {})}

Respond ONLY with JSON (no markdown):
{{"decision_readiness": "READY", "rationale": "Sufficient evidence to proceed"}}

Options: READY, CONDITIONAL, or CANNOT_DECIDE
"""
        
        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            readiness_text = message.content[0].text
            readiness_output = self._parse_json_response(readiness_text)
            readiness_verdict = readiness_output.get("decision_readiness", "READY")
        
        except Exception as e:
            logger.error(f"Claude API error: {e}")
            readiness_verdict = "CANNOT_DECIDE"
            readiness_output = {"error": str(e)}
        
        logger.info(f"[GATE] Verdict: {readiness_verdict}\n")
        
        conn = psycopg2.connect(self.database_url)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO runtime.agent_decision_readiness
            (decision_id, execution_id, decision_readiness, readiness_rationale)
            VALUES (%s, %s, %s, %s)
        """, (decision_id, execution_id, readiness_verdict, json.dumps(readiness_output)))
        conn.commit()
        cursor.close()
        conn.close()
        
        conn = psycopg2.connect(self.database_url)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE runtime.agent_execution 
            SET execution_status = 'COMPLETED', 
                readiness_agent_status = 'COMPLETED',
                execution_completed_at = NOW()
            WHERE execution_id = %s
        """, (execution_id,))
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"{'='*70}")
        logger.info(f"AGENT ORCHESTRATOR: Complete")
        logger.info(f"{'='*70}\n")
        
        return {
            "execution_id": execution_id,
            "decision_id": decision_id,
            "readiness_verdict": readiness_verdict
        }

async def main():
    load_dotenv()
    database_url = os.getenv("DATABASE_URL")
    api_key = os.getenv("ANTHROPIC_API_KEY")
    
    if not database_url:
        logger.error("DATABASE_URL not set in .env")
        return
    
    if not api_key:
        logger.error("ANTHROPIC_API_KEY not set in .env")
        return
    
    client = Anthropic(api_key=api_key)
    orchestrator = AgentOrchestrator(database_url, client)
    
    conn = psycopg2.connect(database_url)
    cursor = conn.cursor(cursor_factory=DictCursor)
    cursor.execute("""
        SELECT decision_id FROM runtime.decision 
        WHERE decision_type = 'RECOMMENDATION_ASSESSMENT'
        ORDER BY created_at DESC
        LIMIT 1
    """)
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if row:
        decision_id = row['decision_id']
        result = await orchestrator.run_for_decision(decision_id)
        logger.info(f"Result: {json.dumps(result, indent=2, default=str)}")
    else:
        logger.error("No RECOMMENDATION_ASSESSMENT decisions found")

if __name__ == "__main__":
    asyncio.run(main())
