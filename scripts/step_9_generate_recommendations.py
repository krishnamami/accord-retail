#!/usr/bin/env python3
import psycopg2
from psycopg2.extras import DictCursor
import json
import sys
import os
from uuid import uuid4
from datetime import datetime
from dotenv import load_dotenv
import logging

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'database', 'scripts'))
from action_rule_engine import ActionRuleEngine, Action

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    logger.error("DATABASE_URL not set in .env")
    sys.exit(1)

def generate_actions_for_bottleneck(bottleneck_data: dict) -> list:
    bottleneck_type = bottleneck_data.get('bottleneck_type', 'unknown')
    churn_rate = bottleneck_data.get('churn_rate', 0)
    actions = []
    
    if bottleneck_type == 'churn' or True:
        price_roi = 0.82 if churn_rate > 0.40 else 0.65
        actions.append(Action(action_name="Raise prices 10-15%", action_type="PRICE_CHANGE", bottleneck_type="churn",
                            roi=price_roi, payback_weeks=4, investment_usd=5000, risk_level=3, customer_impact_pct=0.15))
        actions.append(Action(action_name="Launch loyalty program", action_type="LOYALTY_OFFER", bottleneck_type="churn",
                            roi=0.68, payback_weeks=12, investment_usd=50000, risk_level=2, customer_impact_pct=0.25))
        actions.append(Action(action_name="Discontinue bottom products", action_type="PRODUCT_KILL", bottleneck_type="churn",
                            roi=0.52, payback_weeks=6, investment_usd=10000, risk_level=3, customer_impact_pct=0.20))
        actions.append(Action(action_name="Hybrid approach", action_type="PRICE_CHANGE", bottleneck_type="churn",
                            roi=0.82, payback_weeks=8, investment_usd=35000, risk_level=2, customer_impact_pct=0.18))
        actions.append(Action(action_name="Do nothing", action_type="DO_NOTHING", bottleneck_type="churn",
                            roi=0.0, payback_weeks=0, investment_usd=0, risk_level=4, customer_impact_pct=1.0))
    return actions

def score_actions(actions: list, decision_id: str, business_id: str, engine: ActionRuleEngine) -> dict:
    scored_actions = {}
    for action in actions:
        result = engine.score_action(action, decision_id=decision_id, business_id=business_id)
        scored_actions[action.action_name] = result
    return scored_actions

def insert_recommendation_decision(conn, business_id: str, bottleneck_decision_id: str, bottleneck_name: str, bottleneck_data: dict, scored_actions: dict) -> str:
    cursor = conn.cursor()
    recommendation_actions = []
    rank = 1
    verdict_priority = {'RECOMMENDED': 1, 'CONDITIONAL': 2, 'REQUIRES_APPROVAL': 3, 'NOT_RECOMMENDED': 4}
    sorted_results = sorted(scored_actions.items(), key=lambda x: (verdict_priority.get(x[1].final_verdict, 5), -x[1].confidence))
    
    for action_name, scoring_result in sorted_results:
        recommendation_actions.append({
            "rank": rank, "action_name": action_name, "verdict": scoring_result.final_verdict,
            "confidence": scoring_result.confidence, "rules_applied": len(scoring_result.rules_applied),
            "reasoning": scoring_result.reasoning
        })
        rank += 1
    
    reasoning_json = {
        "bottleneck_name": bottleneck_name, "bottleneck_source_decision": str(bottleneck_decision_id),
        "actions": recommendation_actions, "business_snapshot": bottleneck_data,
        "generated_at": datetime.now().isoformat(),
        "summary": f"Generated {len(recommendation_actions)} action options for {bottleneck_name}"
    }
    
    has_recommended = any(a["verdict"] == "RECOMMENDED" for a in recommendation_actions)
    outcome = "ASSESSED" if has_recommended else "CANNOT_ASSESS"
    decision_id = str(uuid4())
    
    try:
        cursor.execute("""
            INSERT INTO runtime.decision (
                decision_id, business_id, decision_type, subject_id,
                outcome, reasoning_json, kb_version_used, concluded_at
            ) VALUES (%s, %s, %s, %s, %s, %s, 
                     (SELECT kb_version_id FROM ontology.kb_version WHERE is_active = true LIMIT 1),
                     NOW())
        """, (decision_id, business_id, 'RECOMMENDATION_ASSESSMENT', business_id, outcome, json.dumps(reasoning_json)))
        conn.commit()
        logger.info(f"Inserted RECOMMENDATION_ASSESSMENT: {decision_id}")
        return decision_id
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to insert: {e}")
        raise
    finally:
        cursor.close()

def main():
    conn = psycopg2.connect(DATABASE_URL)
    engine = ActionRuleEngine(DATABASE_URL)
    
    print("\n" + "="*70)
    print("STEP 9: GENERATE ACTION RECOMMENDATIONS (Phase 2)")
    print("="*70)
    
    try:
        cursor = conn.cursor(cursor_factory=DictCursor)
        cursor.execute("""
            SELECT decision_id, business_id, outcome, reasoning_json,
                   COALESCE(reasoning_json->>'business_snapshot', '{}')::jsonb as business_data
            FROM runtime.decision
            WHERE decision_type = 'BOTTLENECK_DIAGNOSIS'
              AND outcome = 'IDENTIFIED'
            ORDER BY created_at DESC
        """)
        
        bottlenecks = cursor.fetchall()
        logger.info(f"Found {len(bottlenecks)} BOTTLENECK_DIAGNOSIS decisions")
        
        if not bottlenecks:
            print("No bottleneck decisions found.")
            return
        
        recommendations_created = 0
        for bottleneck in bottlenecks:
            business_data = bottleneck['business_data']
            business_name = business_data.get('name', 'Unknown')
            reasoning = bottleneck['reasoning_json']
            bottleneck_name = reasoning.get('bottleneck_name', 'Unknown bottleneck')
            
            logger.info(f"\nProcessing: {business_name} - {bottleneck_name}")
            
            actions = generate_actions_for_bottleneck(reasoning)
            logger.info(f"  Generated {len(actions)} action options")
            
            scored = score_actions(actions, str(bottleneck['decision_id']), str(bottleneck['business_id']), engine)
            logger.info(f"  Scored {len(scored)} actions")
            
            rec_decision_id = insert_recommendation_decision(
                conn, str(bottleneck['business_id']), str(bottleneck['decision_id']),
                bottleneck_name, dict(reasoning), scored
            )
            recommendations_created += 1
        
        print("\n" + "="*70)
        print("PHASE 2 COMPLETE")
        print("="*70)
        print(f"Bottlenecks processed: {len(bottlenecks)}")
        print(f"Recommendations generated: {recommendations_created}")
        
        cursor.execute("SELECT COUNT(*) as count FROM runtime.decision WHERE decision_type = 'RECOMMENDATION_ASSESSMENT'")
        result = cursor.fetchone()
        print(f"Total RECOMMENDATION_ASSESSMENT decisions: {result['count']}")
        
    except Exception as e:
        logger.error(f"Phase 2 failed: {e}", exc_info=True)
        sys.exit(1)
    finally:
        cursor.close()
        conn.close()
        engine.close()

if __name__ == "__main__":
    main()
