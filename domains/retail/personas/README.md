# Retail Persona Data Products

Each persona receives governed outputs from one or more decision agents. Persona preparation must not redefine shared metrics or agent rules.

Each persona folder will contain:

- `prepare.py` — assemble role-specific context from governed agent outputs and shared facts.
- `prioritization.py` — role-specific ranking/severity/attention ordering.
- `contract.py` — stable backend/API contract consumed by the persona UI.

Personas: `ceo_owner`, `marketing_crm`, `merchandising`, `operations`, `finance`.
