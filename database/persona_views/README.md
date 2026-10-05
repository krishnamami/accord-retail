# Persona Database Views

Database-facing structures for persona-ready data products.

Planned views/contracts:

- `ceo_owner.sql`
- `marketing_crm.sql`
- `merchandising.sql`
- `operations.sql`
- `finance.sql`

Views should expose prepared, governed data for UI/API consumption. They must not duplicate decision formulas that belong in the shared metric or agent layers.
