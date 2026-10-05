# Accord Retail — Modular Decision Architecture

Accord Retail separates shared deterministic facts, decision agents, persona-specific data products, and UI contracts.

## Decision flow

Canonical runtime data → shared deterministic metrics → agent context → calculations → evidence → rules → boundary evaluation → recommendation/decision → persona data product → UI.

## Agent contract

Each decision agent owns seven modules:

- `context.py` — assembles the canonical/raw context permitted for the decision.
- `calculations.py` — deterministic derived facts only.
- `rules.py` — evaluates and records rules, including fired and non-fired rules.
- `boundaries.py` — determines recommendation authority: recommend, human approval, cannot decide, or escalate.
- `evidence.py` — builds evidence and source lineage supporting the decision.
- `recommendations.py` — maps governed findings to permitted recommendations/actions.
- `agent.py` — orchestrates the modules and emits a decision package.

Every decision package must retain context, calculations, evidence, rules evaluated/fired, boundary results, recommendation, permitted actions, versions, and audit/replay identifiers.

The LLM may explain or summarize a governed decision; it does not invent deterministic facts, rules, or the decision boundary.

## Decision agents

- `revenue_health`
- `margin_health`
- `inventory_exposure`
- `customer_retention`
- `pricing_opportunity`

## Personas

- `ceo_owner`
- `marketing_crm`
- `merchandising`
- `operations`
- `finance`

A persona does not redefine shared metrics or decision logic. It prepares and prioritizes governed agent outputs for that role. Multiple personas may consume the same decision with different presentation and permitted actions.

## Persona data products

Database-facing persona structures live under `database/persona_views/`. UI code should consume persona-ready structures/API contracts rather than rebuilding business calculations from operational tables.

## Decision Workbench

A governed decision should support these reusable UI tabs:

1. Summary
2. Context
3. Calculations
4. Evidence
5. Rules & Boundaries
6. Actions
7. Audit / Replay
