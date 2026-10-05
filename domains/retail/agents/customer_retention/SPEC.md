# Customer Retention Agent Specification

Status: **Specification approved for implementation review**

## Business question
Is the active purchasing customer base strengthening or deteriorating, which customers/cohorts/segments drive retention risk, what revenue is exposed, and what intervention is justified by available evidence?

## Decision grain
Business and cohort/segment; customer-level only when identity, purchase history and policy permit it.

## Consuming personas
Marketing / CRM, CEO / Owner, Finance; Revenue Health consumes supported customer-volume drivers.

## Context
Customer identity/key, purchase history, transaction dates, revenue, order count, cohort/first-purchase period when derivable, purchasing-customer counts, channel where attributable, historical comparison periods and any explicit acquisition-cost data. No demographic or behavioral attribute may be invented.

## Deterministic calculations
- purchasing_customers by period
- repeat_purchase_rate from explicit purchase history
- retention rate using a documented cohort/window definition
- churn/inactivity rate using a documented inactivity definition
- purchase frequency
- recency
- customer/cohort revenue contribution
- customer lifetime value only when the chosen deterministic definition and observation window are documented
- CAC and LTV:CAC only when acquisition cost is actually available and attributable
- revenue at risk from defined at-risk cohorts, not from unsupported propensity guesses

Existing processed churn values must be reconciled before use; negative churn rates are invalid under the proposed rate definition.

## Evidence
PURCHASING_CUSTOMERS, REPEAT_PURCHASE_RATE, COHORT_RETENTION, CHURN_OR_INACTIVITY, CUSTOMER_REVENUE, PURCHASE_RECENCY, PURCHASE_FREQUENCY, LTV, CAC when available. Evidence records cohort/window definitions.

## Rules
Initial families: purchasing-customer decline; repeat-rate deterioration; cohort retention below governed benchmark; inactivity threshold reached; high-value customer/cohort at risk; healthy/improving retention; concentration risk. Retain evaluated and fired rules.

## Boundary conditions
The agent must not claim predictive churn unless a validated predictive model exists. Deterministic inactivity/retention is distinct from predicted churn. No personalized incentive amount is recommended without offer policy, economics and entitlement. Missing history, identity quality or insufficient cohort observation yields CANNOT_DECIDE. Sensitive/protected attributes are outside this agent contract.

Boundary outcomes: RECOMMEND, HUMAN_APPROVAL, CANNOT_DECIDE, ESCALATE.

## Decision outcomes
HEALTHY, WATCH, RETENTION_RISK, RETENTION_OPPORTUNITY, CANNOT_DECIDE, ESCALATE.

## Recommendations and actions
Prioritize an at-risk cohort/segment, investigate a channel/customer driver, trigger approved outreach workflow when entitlement/policy exists, or monitor. Offer values and customer-level actions require explicit policy and authority.

## Decision package
Decision, severity, customer/revenue exposure, recommendation, confidence, cohort/window context, calculations, evidence, evaluated/fired rules, boundaries, allowed/restricted actions, owner/approval state, lineage and timestamps.

## Decision Workbench
Summary | Context | Calculations | Evidence | Rules & Boundaries | Actions | Audit / Replay
