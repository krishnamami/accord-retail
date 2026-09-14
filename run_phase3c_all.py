#!/usr/bin/env python3
import asyncio
import psycopg2
from psycopg2.extras import DictCursor
import os
from dotenv import load_dotenv
from database.scripts.agent_orchestrator_phase3c import Phase3COrchestrator
from anthropic import Anthropic

async def run_all():
    load_dotenv()
    db_url = os.getenv("DATABASE_URL")
    api_key = os.getenv("ANTHROPIC_API_KEY")
    
    if not db_url or not api_key:
        print("ERROR: DATABASE_URL or ANTHROPIC_API_KEY not set")
        return
    
    client = Anthropic(api_key=api_key)
    orchestrator = Phase3COrchestrator(db_url, client)
    
    conn = psycopg2.connect(db_url)
    cursor = conn.cursor(cursor_factory=DictCursor)
    cursor.execute("""
        SELECT decision_id FROM (
            SELECT decision_id, ROW_NUMBER() OVER (PARTITION BY decision_id ORDER BY created_at DESC) as rn
            FROM runtime.decision 
            WHERE decision_type = 'RECOMMENDATION_ASSESSMENT'
        ) t WHERE rn = 1
    """)
    decisions = cursor.fetchall()
    cursor.close()
    conn.close()
    
    print(f"\nPHASE 3C: Running all 5 agents for {len(decisions)} decisions\n")
    
    for i, decision in enumerate(decisions, 1):
        decision_id = decision['decision_id']
        print(f"[{i}/{len(decisions)}] {str(decision_id)[:8]}...", end=" ", flush=True)
        
        result = await orchestrator.run_for_decision(decision_id)
        print(f"Readiness: {result.get('readiness_verdict')}, Agents: {len(result.get('agents_run', []))}, Time: {result.get('elapsed_ms', 0)}ms")

if __name__ == "__main__":
    asyncio.run(run_all())
