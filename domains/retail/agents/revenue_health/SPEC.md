# Revenue Health Agent Specification

Status: **Specification approved for implementation review**

## Business question
Where is revenue deteriorating or accelerating, what dimensions explain the movement, how material is the impact, and is there enough governed evidence to recommend intervention?

## Decision grain
Business first; drill-down by month, channel, product/category and customer/cohort when supported by canonical data.

## Consuming personas
- CEO / Owner — overall revenue health, material risks/opportunities, priority and owner.
- Finance — revenue exposure, concentration and financial impact.
- Merchandising — product/category contribution and deterioration.
- Marketing / CRM — channel/customer contribution where evidence supports attribution.
- Operations — availability-driven revenue risk where inventory evidence supports it.

## Context
Canonical inputs may include business, sale, product, customer, inventory and prepared metrics. Required context includes reporting period, historical revenue, units sold, product/category contribution and channel contribution. Optional context includes purchasing customers, retention/cohort metrics, inventory availability and pricing evidence.

Context must preserve source identifiers, observation period, upload/source lineage and data-quality state. Missing optional context must never be silently imputed.

## Deterministic calculations
- revenue_total
- revenue_change_amount and revenue_change_pct
- revenue trend across available periods
- units_sold and unit_change_pct
- average realized revenue per unit where units are valid
- revenue_by_channel and channel_mix
- revenue_by_product/category and contribution_pct
- revenue concentration
- purchasing_customer change where supported
- top positive/negative contributors
- estimated revenue exposure only when the causal driver is supported by evidence

Each calculation records formula, inputs, result, period, quality status and lineage in the calculation trace.

## Evidence
Candidate evidence types include REVENUE_TREND, REVENUE_TOTAL, UNITS_SOLD, CHANNEL_MIX, PRODUCT_REVENUE_CONTRIBUTION, PURCHASING_CUSTOMERS, CUSTOMER_RETENTION, INVENTORY_AVAILABILITY and PRICING_CONTEXT.

Evidence must state the observed fact, source, period/freshness and confidence/quality. A trend alone proves movement, not cause.

## Rules
Rules classify revenue movement and supported drivers. Initial rule families:
- material revenue decline / growth
- sustained versus single-period movement
- unit-led movement
- channel concentration or channel deterioration
- product/category concentration or deterioration
- customer-volume deterioration when customer evidence exists
- inventory-linked revenue risk when stock evidence exists
- pricing-linked revenue movement only when pricing evidence exists

All evaluated rules are retained; fired rules are separately identified.

## Boundary conditions
The agent may diagnose observed revenue movement from deterministic evidence. It must not assert causality without supporting evidence. It must not forecast impact beyond available assumptions or recommend pricing, inventory or customer actions outside the relevant downstream agent's authority.

Boundary outcomes:
- RECOMMEND — sufficient evidence for a governed revenue-health recommendation.
- HUMAN_APPROVAL — recommendation is supported but requires persona authority or cross-functional action.
- CANNOT_DECIDE — required evidence, history or data quality is insufficient.
- ESCALATE — material risk exists but causal signals conflict or governance requires review.

## Decision outcomes
HEALTHY, WATCH, REVENUE_RISK, REVENUE_OPPORTUNITY, CANNOT_DECIDE, ESCALATE.

## Recommendations and actions
Permitted recommendations include investigate a supported driver, prioritize a product/channel/customer segment, route to Pricing/Inventory/Retention for specialized action, or maintain/watch. The Revenue Health agent does not directly invent price changes, replenishment quantities or customer offers.

## Decision package
Must include decision, severity, recommendation, expected/observed impact, confidence, context references, calculations, evidence, rules evaluated, rules fired, boundaries, boundary status, allowed/restricted actions, owner/approval state, KB/rule/metric versions, source lineage and timestamps.

## Decision Workbench
Summary | Context | Calculations | Evidence | Rules & Boundaries | Actions | Audit / Replay

The Summary must separate observed movement from inferred driver. Audit/Replay must preserve the exact data, calculation/rule versions and decision boundary used at decision time.
