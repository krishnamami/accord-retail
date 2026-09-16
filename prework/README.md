# PREWORK FOR STEP 7: AGENTS

Validate decisions before building agents.

## Quick Start

```bash
cd prework
python3 prework_7_orchestrator.py
```

## Scripts

1. **prework_7a_validate_decisions.py**
   - Validate decisions are correct
   - Show evidence→rules→decisions chain
   - Check for inconsistencies

2. **prework_7b_rule_activation_model.py**
   - Understand how rules activate context
   - Map rules to agents
   - Show guardrails for each agent

3. **prework_7c_verify_chain.py**
   - Verify complete chain works end-to-end
   - Check for breaks in pipeline
   - Validate audit trail

4. **prework_7_orchestrator.py**
   - Run all 3 scripts in sequence
   - Summary report

## Key Concept

**Rules are FIRST-CLASS CITIZENS**

Instead of: Context → Rules → Decisions

The correct model is: Rules Activate → Context Built → Decision Generated
                            ↓
                    Guardrails Set → Agent Constrained

## Next: Step 7 Agents

After prework validates everything, build:
- RetentionAgent
- InventoryAgent
- PricingAgent
- ChannelAgent
