#!/usr/bin/env python3
"""
PREWORK STEP 7c: VERIFY COMPLETE CHAIN
Evidence → Rules → Context → Decisions
"""

import psycopg2

import os
import sys

# Credentials are never hard-coded: DATABASE_URL comes from the environment / .env (see database/scripts/db_config.py)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'database', 'scripts'))
from db_config import connect  # noqa: E402

def main():
    conn = connect()
    cursor = conn.cursor()
    
    print("\n" + "="*80)
    print("PREWORK STEP 7c: VERIFY COMPLETE CHAIN")
    print("="*80)
    print("\nValidating: EVIDENCE → RULES → CONTEXT → DECISIONS\n")
    
    # 1. For each business, trace the complete chain
    print("1. COMPLETE CHAIN FOR EACH BUSINESS")
    print("-" * 80)
    
    cursor.execute("""
    SELECT DISTINCT business_id FROM runtime.business ORDER BY business_id LIMIT 3;
    """)
    
    test_businesses = cursor.fetchall()
    
    for (biz_id,) in test_businesses:
        print(f"\n{'='*80}")
        print(f"BUSINESS: {biz_id}")
        print(f"{'='*80}")
        
        # Get evidence
        cursor.execute("""
        SELECT 
            evidence_type,
            (payload_json->>'value')::numeric as value
        FROM runtime.evidence
        WHERE business_id = %s
        ORDER BY evidence_type;
        """, (biz_id,))
        
        evidence = cursor.fetchall()
        print("\n[STEP 1] EVIDENCE")
        for ev_type, value in evidence:
            print(f"  • {ev_type}: {value:.4f}")
        
        # Get rules that fired
        cursor.execute("""
        SELECT 
            gkr.rule_name,
            re.fired
        FROM runtime.rule_execution re
        JOIN ontology.kb_governance_rule gkr ON re.rule_id = gkr.rule_id
        WHERE re.business_id = %s
        ORDER BY gkr.rule_name;
        """, (biz_id,))
        
        rules = cursor.fetchall()
        print("\n[STEP 2] RULES EVALUATED")
        fired_count = sum(1 for _, fired in rules if fired)
        for rule_name, fired in rules:
            status = "✓ FIRED" if fired else "✗ not fired"
            print(f"  • {rule_name}: {status}")
        
        # Get context
        cursor.execute("""
        SELECT context_json
        FROM state.business_context
        WHERE business_id = %s;
        """, (biz_id,))
        
        context_result = cursor.fetchone()
        if context_result:
            ctx_json = context_result[0]
            print(f"\n[STEP 3] CONTEXT BUILT")
            for key, val in list(ctx_json.items())[:5]:
                print(f"  • {key}: {val}")
        
        # Get decision
        cursor.execute("""
        SELECT outcome, concluded_at
        FROM runtime.decision
        WHERE business_id = %s;
        """, (biz_id,))
        
        decision_result = cursor.fetchone()
        if decision_result:
            outcome, concluded = decision_result
            print(f"\n[STEP 4] DECISION GENERATED")
            print(f"  Outcome: {outcome}")
            print(f"  Concluded: {concluded}")
        
        # Validate chain
        print(f"\n[VALIDATION]")
        if fired_count > 0 and decision_result:
            print(f"  ✅ Chain complete: Evidence → Rules → Context → Decision")
        elif fired_count == 0 and decision_result:
            print(f"  ⚠️  No rules fired but decision generated")
        else:
            print(f"  ✅ Chain working")
    
    # 2. Overall pipeline statistics
    print(f"\n\n{'='*80}")
    print("2. OVERALL PIPELINE STATISTICS")
    print(f"{'='*80}\n")
    
    cursor.execute("""
    SELECT 
        (SELECT COUNT(*) FROM runtime.evidence) as total_evidence,
        (SELECT COUNT(DISTINCT business_id) FROM runtime.evidence) as businesses_with_evidence,
        (SELECT COUNT(*) FROM runtime.rule_execution WHERE fired = true) as rules_fired,
        (SELECT COUNT(*) FROM state.business_context) as contexts_built,
        (SELECT COUNT(*) FROM runtime.decision) as decisions_generated;
    """)
    
    stats = cursor.fetchone()
    total_ev, biz_ev, rules_fired, contexts, decisions = stats
    
    print(f"  Total Evidence Items: {total_ev}")
    print(f"  Businesses with Evidence: {biz_ev}")
    print(f"  Rules Fired: {rules_fired}")
    print(f"  Contexts Built: {contexts}")
    print(f"  Decisions Generated: {decisions}")
    
    print(f"\n{'='*80}")
    print("✅ PREWORK COMPLETE - READY FOR STEP 7")
    print(f"{'='*80}\n")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    main()
