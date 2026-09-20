#!/usr/bin/env python3
"""
PREWORK STEP 7a: VALIDATE DECISIONS
Before building agents, validate that decisions were generated correctly.
This ensures Step 6 (Apply Rules) and Step 7 (Generate Decisions) are sound.

Rules are FIRST-CLASS CITIZENS:
- Rules determine which context is built
- Context determines which decisions are generated
- Agents must respect this chain
"""

import psycopg2
import json

import os
import sys

# Credentials are never hard-coded: DATABASE_URL comes from the environment / .env (see database/scripts/db_config.py)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'database', 'scripts'))
from db_config import connect  # noqa: E402

def main():
    conn = connect()
    cursor = conn.cursor()
    
    print("\n" + "="*80)
    print("PREWORK STEP 7a: VALIDATE DECISIONS")
    print("="*80)
    print("\nValidating decision generation chain:")
    print("RULE FIRED → CONTEXT BUILT → DECISION GENERATED\n")
    
    # 1. Get all decisions
    print("1. DECISIONS GENERATED")
    print("-" * 80)
    cursor.execute("""
    SELECT 
        d.decision_id,
        d.business_id,
        d.decision_type,
        d.outcome,
        d.concluded_at,
        d.reasoning_json->>'context_id' as context_id
    FROM runtime.decision d
    ORDER BY d.business_id;
    """)
    
    decisions = cursor.fetchall()
    print(f"Total decisions: {len(decisions)}\n")
    
    for dec_id, biz_id, dec_type, outcome, concluded_at, ctx_id in decisions[:3]:
        print(f"  • Decision: {str(dec_id)[:8]}...")
        print(f"    Business: {biz_id}")
        print(f"    Type: {dec_type}")
        print(f"    Outcome: {outcome}")
        print(f"    Context: {ctx_id}\n")
    
    # 2. For each decision, show which rules fired
    print("\n2. RULES THAT FIRED FOR EACH DECISION")
    print("-" * 80)
    cursor.execute("""
    SELECT 
        d.decision_id,
        d.business_id,
        COUNT(CASE WHEN re.fired = true THEN 1 END) as rules_fired,
        COUNT(*) as rules_evaluated,
        ARRAY_AGG(DISTINCT gkr.rule_name ORDER BY gkr.rule_name) FILTER (WHERE re.fired = true) as fired_rules
    FROM runtime.decision d
    LEFT JOIN runtime.rule_execution re ON d.business_id = re.business_id
    LEFT JOIN ontology.kb_governance_rule gkr ON re.rule_id = gkr.rule_id
    GROUP BY d.decision_id, d.business_id
    ORDER BY d.business_id
    LIMIT 5;
    """)
    
    rule_results = cursor.fetchall()
    for dec_id, biz_id, fired, evaluated, rules in rule_results:
        print(f"\n  Business: {biz_id}")
        print(f"  Rules fired: {fired}/{evaluated}")
        if rules:
            for rule in rules:
                print(f"    ✓ {rule}")
    
    # 3. Show evidence→rules→decisions chain
    print("\n\n3. EVIDENCE → RULES → DECISIONS CHAIN")
    print("-" * 80)
    cursor.execute("""
    SELECT DISTINCT
        e.business_id,
        e.evidence_type,
        (e.payload_json->>'value')::numeric as evidence_value,
        gkr.rule_name,
        re.fired,
        d.outcome
    FROM runtime.evidence e
    LEFT JOIN runtime.rule_execution re ON e.business_id = re.business_id
    LEFT JOIN ontology.kb_governance_rule gkr ON re.rule_id = gkr.rule_id
    LEFT JOIN runtime.decision d ON e.business_id = d.business_id
    WHERE e.evidence_type IN ('churn_rate', 'repeat_purchase_rate')
    ORDER BY e.business_id, e.evidence_type
    LIMIT 5;
    """)
    
    chains = cursor.fetchall()
    for biz_id, ev_type, ev_val, rule, fired, outcome in chains:
        print(f"\n  Business: {biz_id}")
        print(f"    Evidence: {ev_type} = {ev_val:.2f}")
        print(f"    Rule: {rule}")
        print(f"    Fired? {fired}")
        print(f"    Decision: {outcome}")
    
    # 4. Validate business context matches decision
    print("\n\n4. CONTEXT VALIDITY CHECK")
    print("-" * 80)
    cursor.execute("""
    SELECT 
        bc.business_id,
        bc.context_json->>'name' as business_name,
        (bc.context_json->>'churn_rate')::numeric as churn_rate,
        (bc.context_json->>'repeat_rate')::numeric as repeat_rate,
        d.outcome,
        d.reasoning_json->>'context_id' as decision_context_id
    FROM state.business_context bc
    LEFT JOIN runtime.decision d ON bc.business_id = d.business_id
    ORDER BY bc.business_id
    LIMIT 5;
    """)
    
    contexts = cursor.fetchall()
    for biz_id, name, churn, repeat, outcome, ctx_id in contexts:
        print(f"\n  Business: {name} ({biz_id})")
        print(f"    Churn Rate: {churn:.2f} (threshold: 0.30)")
        print(f"    Repeat Rate: {repeat:.2f} (threshold: 0.25)")
        print(f"    Decision Outcome: {outcome}")
        
        # Validate logic
        if churn and churn > 0.30:
            expected = "BOTTLENECK_IDENTIFIED"
        else:
            expected = "IDENTIFIED"
        
        if outcome == expected:
            print(f"    ✅ VALID - Decision matches rule logic")
        else:
            print(f"    ⚠️  MISMATCH - Expected {expected}, got {outcome}")
    
    # 5. Summary statistics
    print("\n\n5. VALIDATION SUMMARY")
    print("-" * 80)
    
    cursor.execute("""
    SELECT 
        COUNT(DISTINCT d.decision_id) as total_decisions,
        COUNT(DISTINCT d.business_id) as businesses_diagnosed,
        COUNT(DISTINCT CASE WHEN re.fired = true THEN re.business_id END) as businesses_with_rules_fired,
        COUNT(DISTINCT CASE WHEN d.outcome = 'IDENTIFIED' THEN d.decision_id END) as identified_decisions
    FROM runtime.decision d
    LEFT JOIN runtime.rule_execution re ON d.business_id = re.business_id;
    """)
    
    total_dec, biz_diag, biz_fired, identified = cursor.fetchone()
    
    print(f"\n  Total Decisions: {total_dec}")
    print(f"  Businesses Diagnosed: {biz_diag}")
    print(f"  Businesses with Rules Fired: {biz_fired}")
    print(f"  Identified Bottlenecks: {identified}")
    print(f"\n  ✅ Decision validation complete")
    
    # 6. Key insight: Rules as first-class citizens
    print("\n\n6. RULES AS FIRST-CLASS CITIZENS")
    print("-" * 80)
    print("""
    KEY INSIGHT FOR STEP 7 (AGENTS):
    
    • Rules fired determine what context is RELEVANT
    • Context is BUILT based on which rules are active
    • Agents must respect rule boundaries as guardrails
    • Each agent operates within a RULE SCOPE
    """)
    
    cursor.close()
    conn.close()
    
    print("\n" + "="*80)
    print("✅ DECISION VALIDATION COMPLETE")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
