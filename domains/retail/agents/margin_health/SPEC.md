# Margin Health Agent Specification

Status: **Specification approved for implementation review**

## Business question
Where is gross margin healthy, deteriorating or leaking; which products/categories/channels contribute; and what intervention can be recommended without violating profitability or evidence boundaries?

## Decision grain
Business and product/category; channel where cost/revenue allocation supports it.

## Consuming personas
CEO / Owner, Finance, Merchandising; Pricing consumes margin boundaries and Operations may consume inventory-related margin findings.

## Context
Revenue, units, product price/list price when available, COGS/cost basis, product/category, channel, discounts/promotions when available, historical periods, inventory context and competitor/pricing evidence when relevant. Every input retains period, source and quality lineage.

## Deterministic calculations
- gross_profit_amount = revenue - COGS
- gross_margin_pct = gross_profit / revenue when revenue > 0
- product/category gross margin
- margin_change_amount and margin_change_pct/points across comparable periods
- revenue-weighted margin
- contribution to margin erosion/improvement
- realized unit revenue and unit cost when valid
- discount/promotion dependency only when explicit discount data exists
- estimated margin dollars at risk/opportunity only from explicit, traceable assumptions

`processed product_margin` must not be trusted until its current formula is reconciled with canonical revenue and COGS.

## Evidence
GROSS_MARGIN, COGS, REVENUE, PRODUCT_MARGIN, MARGIN_TREND, DISCOUNT_CONTEXT, PRICING_CONTEXT, INVENTORY_CONTEXT. Evidence must distinguish observed margin from hypotheses about why margin moved.

## Rules
Initial families: margin below approved floor; material margin deterioration; high-revenue/low-margin concentration; product/category margin outlier; margin improvement; pricing/discount-associated erosion when supported; inventory-related markdown exposure when supported.

Retain every evaluated rule and the subset fired.

## Boundary conditions
Never recommend an action that drives projected margin below the configured floor. Never attribute erosion to discount, supplier cost, pricing or inventory without corresponding evidence. If COGS is absent/stale or revenue/cost periods are incomparable, return CANNOT_DECIDE for margin diagnosis. Cross-functional price or inventory changes are routed to the specialized agent and may require human approval.

Boundary outcomes: RECOMMEND, HUMAN_APPROVAL, CANNOT_DECIDE, ESCALATE.

## Decision outcomes
HEALTHY, WATCH, MARGIN_RISK, MARGIN_OPPORTUNITY, CANNOT_DECIDE, ESCALATE.

## Recommendations and actions
Prioritize products/categories for review; protect margin floor; investigate supported cost/discount/pricing drivers; route price candidates to Pricing Opportunity; route markdown/excess-stock drivers to Inventory Exposure. No unsupported price or cost changes.

## Decision package
Decision, severity, observed margin impact, recommendation, confidence, context, calculations, evidence, evaluated/fired rules, boundaries, allowed/restricted actions, owner/approval state, version lineage and timestamps.

## Decision Workbench
Summary | Context | Calculations | Evidence | Rules & Boundaries | Actions | Audit / Replay
