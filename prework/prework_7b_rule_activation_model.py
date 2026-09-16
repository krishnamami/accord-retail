#!/usr/bin/env python3
"""
PREWORK STEP 7b: RULE ACTIVATION MODEL
Build a model of HOW RULES ACTIVATE CONTEXT.
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
    
    print("\n" + "="*80)
    print("PREWORK STEP 7b: RULE ACTIVATION MODEL")
    print("="*80)
    print("\nUnderstanding: RULES BUILD CONTEXT\n")
    
    # 1. List all active rules
    print("1. ACTIVE GOVERNANCE RULES")
    print("-" * 80)
    cursor.execute("""
    SELECT 
        gkr.rule_id,
        gkr.rule_name,
        gkr.enforcement,
        gkr.phase
    FROM ontology.kb_governance_rule gkr
    ORDER BY gkr.rule_name;
    """)
    
    rules = cursor.fetchall()
    print(f"Total active rules: {len(rules)}\n")
    
    for rule_id, rule_name, enforcement, phase in rules:
        print(f"  • {rule_name}")
        print(f"    Enforcement: {enforcement}")
        print(f"    Phase: {phase}\n")
    
    # 2. Show which rules fired in our data
    print("\n2. RULES FIRED IN CURRENT DATA")
    print("-" * 80)
    cursor.execute("""
    SELECT 
        gkr.rule_name,
        COUNT(CASE WHEN re.fired = true THEN 1 END) as times_fired,
        COUNT(*) as times_evaluated,
        ARRAY_AGG(DISTINCT re.business_id ORDER BY re.business_id) as business_ids_affected
    FROM ontology.kb_governance_rule gkr
    LEFT JOIN runtime.rule_execution re ON gkr.rule_id = re.rule_id
    GROUP BY gkr.rule_name
    ORDER BY times_fired DESC;
    """)
    
    fired_rules = cursor.fetchall()
    for rule_name, fired, evaluated, biz_ids in fired_rules:
        print(f"\n  {rule_name}")
        print(f"    Fired: {fired}/{evaluated} times")
        if biz_ids and fired > 0:
            print(f"    Affected businesses: {len(set(biz_ids))}")
    
    # 3. Show the context→agent mapping
    print("\n\n3. CONTEXT DETERMINES AGENT ASSIGNMENT")
    print("-" * 80)
    
    cursor.execute("""
    SELECT 
        bc.business_id,
        COUNT(DISTINCT re.rule_id) as rules_fired,
        ARRAY_AGG(DISTINCT gkr.rule_name ORDER BY gkr.rule_name) as rules,
        (bc.context_json->>'churn_rate')::numeric as churn_rate,
        (bc.context_json->>'repeat_rate')::numeric as repeat_rate
    FROM state.business_context bc
    LEFT JOIN runtime.rule_execution re ON bc.business_id = re.business_id AND re.fired = true
    LEFT JOIN ontology.kb_governance_rule gkr ON re.rule_id = gkr.rule_id
    GROUP BY bc.business_id, bc.context_json
    ORDER BY bc.business_id
    LIMIT 5;
    """)
    
    context_agents = cursor.fetchall()
    for biz_id, rules_fired, rules_arr, churn, repeat in context_agents:
        print(f"\n  Business: {biz_id}")
        print(f"    Churn: {churn:.2f}, Repeat: {repeat:.2f}")
        print(f"    Rules fired: {rules_fired}")
        if rules_arr and rules_arr[0]:
            agents_needed = []
            for rule in rules_arr:
                if 'CHR' in rule or 'RPR' in rule or 'RET' in rule:
                    agents_needed.append('RetentionAgent')
                if 'INV' in rule:
                    agents_needed.append('InventoryAgent')
                if 'MAR' in rule or 'REV' in rule:
                    agents_needed.append('PricingAgent')
            
            print(f"    Agents needed: {', '.join(set(agents_needed))}")
    
    print("\n\n4. AGENT RESPONSIBILITY MATRIX")
    print("-" * 80)
    print("""
    Agent: RetentionAgent
    ├─ Rules: CHR_001, RPR_001, RET_001
    ├─ Triggers: churn > 30% OR repeat < 25%
    ├─ Context: [churn_rate, repeat_rate, CLV]
    └─ Guardrails: Max 25% discount, $20k spend
    
    Agent: InventoryAgent
    ├─ Rule: INV_001
    ├─ Trigger: slow_moving > 20%
    ├─ Context: [inventory_turnover, margins]
    └─ Guardrails: Max 40% discount, 10% margin
    
    Agent: PricingAgent
    ├─ Rules: MAR_001, REV_001
    ├─ Trigger: margin < 35%
    ├─ Context: [product_margin, elasticity]
    └─ Guardrails: Max 10% increase quarterly
    """)
    
    cursor.close()
    conn.close()
    
    print("\n" + "="*80)
    print("✅ RULE ACTIVATION MODEL COMPLETE")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
