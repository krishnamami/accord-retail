# Inventory Exposure Agent Specification

Status: **Specification approved for implementation review**

## Business question
Which products create stockout, excess, slow-moving or working-capital exposure, what is the business impact, and what inventory intervention is supportable within policy boundaries?

## Decision grain
SKU/product, aggregated to category and business.

## Consuming personas
Operations, Merchandising, Finance, CEO / Owner; Revenue Health consumes supported availability-driven revenue risk.

## Context
Product/SKU, on-hand quantity, reorder point, cost basis, price, historical units/sales velocity, relevant periods, category, inventory observations and revenue/margin context. Lead time, inbound/open orders, shelf-life and location are optional and must not be assumed when unavailable.

## Deterministic calculations
- quantity_on_hand
- inventory_value from valid cost basis
- sales velocity over defined window
- weeks/days of supply only when velocity is valid
- reorder-point gap
- stockout/reorder exposure
- excess inventory against configured supply threshold
- slow-moving indicator from governed definition
- inventory turnover where required inputs are comparable
- working-capital exposure
- revenue-at-risk estimate only when demand/availability evidence supports it

## Evidence
INVENTORY_POSITION, REORDER_POINT, SALES_VELOCITY, INVENTORY_TURNOVER, SLOW_MOVING_INVENTORY, STOCKOUT_FREQUENCY, REVENUE_CONTEXT, MARGIN_CONTEXT. Evidence must retain observation timestamp because inventory is time-sensitive.

## Rules
Initial families: at/below reorder point; probable stockout risk; excess weeks of supply; slow-moving stock; high-value excess inventory; high-demand constrained inventory; margin-sensitive markdown candidate. All evaluated/fired rules are retained.

## Boundary conditions
Do not recommend exact replenishment quantity without required lead-time/demand policy inputs. Do not recommend transfer when location-level stock is unavailable. Do not recommend markdown percentage without Pricing/Margin boundary evaluation. Stale inventory snapshots or insufficient sales history can force CANNOT_DECIDE. High-value or policy-sensitive actions require HUMAN_APPROVAL.

Boundary outcomes: RECOMMEND, HUMAN_APPROVAL, CANNOT_DECIDE, ESCALATE.

## Decision outcomes
BALANCED, WATCH, STOCKOUT_RISK, EXCESS_INVENTORY, SLOW_MOVING, REBALANCE_CANDIDATE, CANNOT_DECIDE, ESCALATE.

## Recommendations and actions
Review/replenish, reduce future purchasing, investigate transfer, route markdown candidate to Pricing/Margin, prioritize constrained high-value products, or monitor. Exact action parameters are emitted only when required context and authority exist.

## Decision package
Decision, severity, inventory/financial exposure, recommendation, confidence, SKU/category context, calculations, evidence, evaluated/fired rules, boundaries, allowed/restricted actions, owner/approval state, lineage and timestamps.

## Decision Workbench
Summary | Context | Calculations | Evidence | Rules & Boundaries | Actions | Audit / Replay
