#!/usr/bin/env python3
"""
PREWORK STEP 7d: DETAILED DECISION REPORT
Shows each business/lineitem with its complete decision chain.
"""

import psycopg2

DB_CONFIG = {
    "host": "database-1.c1qseu4kq079.us-west-2.rds.amazonaws.com",
    "port": 5432,
    "database": "accord_retail",
    "user": "postgres",
    "password": "Sharanya87$"
}

def main():
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    print("\n" + "="*100)
    print("DETAILED DECISION REPORT FOR EACH BUSINESS")
    print("="*100)
    
    # Get all businesses
    cursor.execute("""
    SELECT business_id, name 
    FROM runtime.business 
    ORDER BY business_id;
    """)
    
    businesses = cursor.fetchall()
    decision_summary = []
    
    for idx, (biz_id, biz_name) in enumerate(businesses, 1):
        print(f"\n{'='*100}")
        print(f"LINEITEM {idx}: {biz_id}")
        print(f"Business: {biz_name}")
        print(f"{'='*100}")
        
        # Get evidence
        cursor.execute("""
        SELECT 
            evidence_type,
            (payload_json->>'value')::numeric as value,
            payload_json->>'confidence' as confidence
        FROM runtime.evidence
        WHERE business_id = %s
        ORDER BY evidence_type;
        """, (biz_id,))
        
        evidence_data = cursor.fetchall()
        print("\n[1] EVIDENCE")
        for ev_type, value, confidence in evidence_data:
            print(f"  • {ev_type:30s}: {value:10.4f}  (confidence: {confidence})")
        
        # Get rules
        cursor.execute("""
        SELECT 
            gkr.rule_name,
            re.fired,
            re.outcome_produced
        FROM runtime.rule_execution re
        JOIN ontology.kb_governance_rule gkr ON re.rule_id = gkr.rule_id
        WHERE re.business_id = %s
        ORDER BY gkr.rule_name;
        """, (biz_id,))
        
        rules_data = cursor.fetchall()
        rules_fired = [r[0] for r in rules_data if r[1]]
        
        print("\n[2] RULES EVALUATED")
        for rule_name, fired, outcome in rules_data:
            status = "✓ FIRED" if fired else "✗"
            print(f"  {status} {rule_name:30s}: {outcome}")
        
        print(f"\n  → Rules Fired: {len(rules_fired)}")
        if rules_fired:
            for rule in rules_fired:
                print(f"     • {rule}")
        
        # Get context
        cursor.execute("""
        SELECT 
            context_id,
            observation_period_start,
            observation_period_end,
            context_json,
            generated_for_kb_version
        FROM state.business_context
        WHERE business_id = %s;
        """, (biz_id,))
        
        context_result = cursor.fetchone()
        print("\n[3] CONTEXT BUILT")
        if context_result:
            ctx_id, period_start, period_end, ctx_json, kb_version = context_result
            print(f"  Context ID: {ctx_id}")
            print(f"  KB Version: {kb_version}")
            print(f"  Period: {period_start} to {period_end}")
            print(f"  Context Attributes:")
            for key, val in ctx_json.items():
                if isinstance(val, (int, float)):
                    print(f"    • {key:30s}: {val:.4f}" if isinstance(val, float) else f"    • {key:30s}: {val}")
                else:
                    print(f"    • {key:30s}: {str(val)[:50]}")
        
        # Get decision
        cursor.execute("""
        SELECT 
            decision_id,
            decision_type,
            outcome,
            reasoning_json,
            kb_version_used,
            concluded_at
        FROM runtime.decision
        WHERE business_id = %s;
        """, (biz_id,))
        
        decision_result = cursor.fetchone()
        print("\n[4] DECISION GENERATED")
        if decision_result:
            dec_id, dec_type, outcome, reasoning, kb_ver, concluded = decision_result
            print(f"  Decision ID: {dec_id}")
            print(f"  Type: {dec_type}")
            print(f"  Outcome: ➜ {outcome}")
            print(f"  KB Version: {kb_ver}")
            print(f"  Concluded: {concluded}")
            print(f"  Reasoning:")
            for key, val in reasoning.items():
                print(f"    • {key}: {str(val)[:70]}")
        else:
            outcome = None
            print("  No decision generated")
        
        # Validate chain
        print("\n[5] CHAIN VALIDATION")
        cursor.execute("""
        SELECT 
            COUNT(DISTINCT e.business_id) as has_evidence,
            COUNT(DISTINCT CASE WHEN re.fired = true THEN re.business_id END) as has_rules_fired,
            COUNT(DISTINCT bc.business_id) as has_context,
            COUNT(DISTINCT d.business_id) as has_decision
        FROM runtime.evidence e
        LEFT JOIN runtime.rule_execution re ON e.business_id = re.business_id
        LEFT JOIN state.business_context bc ON e.business_id = bc.business_id
        LEFT JOIN runtime.decision d ON e.business_id = d.business_id
        WHERE e.business_id = %s;
        """, (biz_id,))
        
        chain_result = cursor.fetchone()
        has_ev, has_fired, has_ctx, has_dec = chain_result
        
        if has_ev and has_ctx and has_dec:
            print("  ✅ COMPLETE: Evidence → Rules → Context → Decision")
            status = "COMPLETE"
        elif has_fired and has_dec:
            print("  ✅ PARTIAL: Rules fired → Decision generated")
            status = "PARTIAL"
        else:
            print("  ⚠️  INCOMPLETE")
            status = "INCOMPLETE"
        
        decision_summary.append({
            'idx': idx,
            'business_id': biz_id,
            'business_name': biz_name,
            'evidence_count': len(evidence_data),
            'rules_fired': len(rules_fired),
            'decision_outcome': outcome if decision_result else 'NONE',
            'chain_status': status
        })
    
    # SUMMARY TABLE
    print(f"\n\n{'='*100}")
    print("SUMMARY: ALL BUSINESSES")
    print(f"{'='*100}\n")
    
    print(f"{'#':<3} {'Business ID':<40} {'Name':<20} {'Ev':<3} {'Rules':<6} {'Decision':<15} {'Status':<12}")
    print("-" * 100)
    
    for item in decision_summary:
        print(f"{item['idx']:<3} {str(item['business_id'])[:40]:<40} {item['business_name'][:20]:<20} "
              f"{item['evidence_count']:<3} {item['rules_fired']:<6} {str(item['decision_outcome']):<15} {item['chain_status']:<12}")
    
    # STATISTICS
    print(f"\n{'='*100}")
    print("STATISTICS")
    print(f"{'='*100}\n")
    
    cursor.execute("""
    SELECT 
        COUNT(DISTINCT b.business_id) as total_businesses,
        COUNT(DISTINCT e.business_id) as businesses_with_evidence,
        COUNT(DISTINCT CASE WHEN re.fired = true THEN re.business_id END) as businesses_with_rules_fired,
        COUNT(DISTINCT bc.business_id) as businesses_with_context,
        COUNT(DISTINCT d.business_id) as businesses_with_decisions,
        COUNT(e.evidence_id) as total_evidence_items,
        SUM(CASE WHEN re.fired = true THEN 1 ELSE 0 END) as total_rules_fired,
        COUNT(d.decision_id) as total_decisions
    FROM runtime.business b
    LEFT JOIN runtime.evidence e ON b.business_id = e.business_id
    LEFT JOIN runtime.rule_execution re ON b.business_id = re.business_id
    LEFT JOIN state.business_context bc ON b.business_id = bc.business_id
    LEFT JOIN runtime.decision d ON b.business_id = d.business_id;
    """)
    
    stats = cursor.fetchone()
    total_biz, biz_ev, biz_fired, biz_ctx, biz_dec, total_ev, total_fired, total_dec = stats
    
    print(f"  Total Businesses:                 {total_biz}")
    print(f"  Businesses with Evidence:         {biz_ev}")
    print(f"  Businesses with Rules Fired:      {biz_fired}")
    print(f"  Businesses with Context:          {biz_ctx}")
    print(f"  Businesses with Decisions:        {biz_dec}")
    print(f"  Total Evidence Items:             {total_ev}")
    print(f"  Total Rules Fired:                {total_fired}")
    print(f"  Total Decisions Generated:        {total_dec}")
    
    # DECISION DISTRIBUTION
    print(f"\n{'='*100}")
    print("DECISION OUTCOMES DISTRIBUTION")
    print(f"{'='*100}\n")
    
    cursor.execute("""
    SELECT 
        outcome,
        COUNT(*) as count
    FROM runtime.decision
    GROUP BY outcome
    ORDER BY count DESC;
    """)
    
    decision_dist = cursor.fetchall()
    for outcome, count in decision_dist:
        print(f"  {outcome:<20}: {count}")
    
    # KEY FINDINGS
    print(f"\n{'='*100}")
    print("KEY FINDINGS")
    print(f"{'='*100}\n")
    
    cursor.execute("""
    SELECT 
        (bc.context_json->>'churn_rate')::numeric as churn_rate,
        (bc.context_json->>'repeat_rate')::numeric as repeat_rate,
        (bc.context_json->>'margin')::numeric as margin,
        (bc.context_json->>'revenue')::numeric as revenue
    FROM state.business_context bc
    ORDER BY churn_rate DESC
    LIMIT 5;
    """)
    
    print("  Top 5 businesses by churn rate:")
    for i, (churn, repeat, margin, revenue) in enumerate(cursor.fetchall(), 1):
        print(f"    {i}. Churn: {churn:.2%} | Repeat: {repeat:.2%} | Margin: {margin:.2%} | Revenue: ${revenue:,.0f}")
    
    cursor.close()
    conn.close()
    
    print(f"\n{'='*100}")
    print("✅ DETAILED DECISION REPORT COMPLETE")
    print(f"{'='*100}\n")

if __name__ == "__main__":
    main()
