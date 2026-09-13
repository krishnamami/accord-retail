# Accord Retail Scripts

## Pipeline Execution

### `run_pipeline.py` (CURRENT - USE THIS ONE)
Complete 8-step decision intelligence pipeline:
1. Load raw business data
2. Validate data schema
3. Fold, transform & normalize to business metrics
4. Project metrics as KB-typed evidence
5. Build business context snapshots
6. Apply governance rules
7. Generate bottleneck diagnosis decisions
8. Audit trail + decision replay

**Usage:**
```bash
cd ~/OneDrive/Documents/accord-retail
python3 scripts/run_pipeline.py
```

**Output:**
- 10 raw data uploads
- 10 validated records
- 10 normalized business records
- 50 evidence items (5 types × 10 businesses)
- 10 business contexts
- 20 rule evaluations
- 10 bottleneck diagnosis decisions
- 60 audit logs
- 10 decision replays
- **Total: 190 records**

### `run_pipeline_v1.py` (ARCHIVED)
First attempt with schema issues. Kept for reference.

## Database Loaders

### `../database/loaders/load_ontology_from_json.py`
Loads the knowledge base ontology from JSON into PostgreSQL:
- Knowledge base versions
- Evidence types
- Governance rules
- Verbs and links

## Next Steps

1. Run pipeline: `python3 scripts/run_pipeline.py`
2. Verify data in workbench
3. Build persona agents to consume decisions
4. Integrate with Decision OS
