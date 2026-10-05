# Shared Retail Deterministic Layer

Shared calculations provide one governed definition of common business facts for all agents/personas.

Planned modules:

- `metrics/revenue_metrics.py`
- `metrics/margin_metrics.py`
- `metrics/customer_metrics.py`
- `metrics/inventory_metrics.py`
- `metrics/pricing_metrics.py`
- `context/context_builder.py`
- `evidence/evidence_builder.py`

Shared metrics must be deterministic, versionable, traceable to source data, and reusable. Persona code must not redefine them.
