# Pricing Opportunity Agent Specification

Status: **Specification approved for implementation review**

## Business question
Where does current realized/list pricing appear misaligned with demand, margin, competitor context or inventory position, and what price action—if any—can be recommended within governed profitability and authority boundaries?

## Decision grain
SKU/product, aggregated to category/business.

## Consuming personas
Merchandising, Finance, CEO / Owner; Operations may consume markdown/rebalancing candidates and Revenue/Margin agents consume pricing context.

## Context
Product/SKU, list price when available, realized selling price, revenue, units, COGS, gross margin, historical price/revenue/unit periods, competitor price evidence, discounts/promotions when explicit, inventory position/supply and category. Missing competitor or discount data remains missing; it is never synthesized.

## Deterministic calculations
- realized selling price = revenue / units when units > 0
- list-to-realized discount pct when list price is valid
- gross margin and margin floor headroom
- competitor price gap pct when comparable/fresh competitor evidence exists
- revenue and unit change pct
- price movement where historical realized price is available
- inventory supply/exposure inputs from Inventory Exposure
- candidate price scenarios only within configured step/range
- projected unit margin and gross margin for each candidate scenario
- estimated impact only using explicit scenario assumptions; label it scenario, not fact

## Evidence
REALIZED_PRICE, LIST_PRICE, COGS, GROSS_MARGIN, REVENUE_TREND, UNIT_TREND, COMPETITOR_PRICE_COMPARISON, DISCOUNT_CONTEXT, INVENTORY_CONTEXT. Competitor evidence must include comparability and freshness.

## Rules
Initial families: priced materially above/below comparable competitor; demand deterioration with margin headroom; excessive discounting; margin-floor pressure; excess inventory with markdown headroom; strong demand/low inventory where price increase may be evaluated; insufficient evidence/no-action. Retain all evaluated/fired rules.

## Boundary conditions
Configured minimum gross-margin floor; maximum price-change percentage/step; competitor freshness/comparability; minimum evidence quality/confidence; product/category exclusions; MAP or contractual constraints when represented in KB; persona entitlement; approval threshold. Never recommend a price that violates a hard boundary. Never treat a scenario estimate as guaranteed impact.

Boundary outcomes:
- RECOMMEND — candidate lies within all hard boundaries and evidence threshold.
- HUMAN_APPROVAL — candidate is supportable but requires authority.
- CANNOT_DECIDE — required cost/price/evidence is missing or stale.
- ESCALATE — policy conflict, material exception or competing signals require review.

## Decision outcomes
NO_CHANGE, PRICE_DECREASE_CANDIDATE, PRICE_INCREASE_CANDIDATE, PROMOTION_REVIEW, CANNOT_DECIDE, ESCALATE.

## Recommendations and actions
Recommend an allowed price range/candidate scenario, maintain price, review promotion/discount, or route for approval. Execution of a price change is separate from recommendation and requires entitlement/action governance.

## Decision package
Decision, severity/opportunity, current and candidate price context, scenario impact, confidence, calculations, evidence, evaluated/fired rules, hard/soft boundaries and PASS/FAIL results, allowed/restricted actions, owner/approval state, lineage and timestamps.

## Decision Workbench
Summary | Context | Calculations | Evidence | Rules & Boundaries | Actions | Audit / Replay

The UI must clearly distinguish observed facts from modeled scenarios and show which boundary limited the final recommendation.
