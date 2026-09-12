# GOVERNANCE.md — Accord Retail

**Version:** 0.1
**Status:** Living specification — update as features, consultants, and governance rules are added
**Date:** September 12, 2026
**Owner:** krishnamami
**Related docs:** [`PRD.md`](./PRD.md) · `accord_retail_ontology_v0_1.docx` · `ARCHITECTURE.md` (pending) · [`CONTEXT.md`](./CONTEXT.md)

This document defines:

1. **Actors** — the roles in the system
2. **Access control** — who can do what
3. **Data sensitivity** — what data each role can see
4. **Approval workflows** — when multiple roles must coordinate

> **Governing principle.** Role determines **who** may participate. Decision determines **whether** the action is permitted. No verb that changes the business is authorised by role alone.

> **Vocabulary note.** Verb names, decision types, and object names follow the ontology (`accord_retail_ontology_v0_1.docx`). One reconciliation: the ontology's RECOMMENDATION_ASSESSMENT outcome is `ASSESSED | CANNOT_ASSESS`; this document additionally uses `RECOMMENDED | NOT_RECOMMENDED` as the **per-recommendation verdict** inside an `ASSESSED` outcome. See §14.

---

## 1. Actors

| Actor | Role | Represented by | Responsibilities | Phase |
|-------|------|----------------|------------------|-------|
| **Business Owner** | Owner | Retail owner / e-commerce manager | Submits data, receives diagnosis, executes actions, reports outcomes | P1+ |
| **Consultant** | Advisor | Shopify specialist, retail consultant, agency | Reviews diagnosis on behalf of owner, advises on execution, validates results | P1+ |
| **Platform** | System | Accord backend | Runs analysis, generates recommendations, stores audit trail | P1+ |
| **Shopify** | Data Source | Shopify API | Provides transactional data, inventory, customer data | P2+ |

Notes:
- A person may hold the Owner role for more than one business (e.g. a multi-brand operator). Each business is a separate tenant; the role is granted per tenant.
- The Platform is the only actor that writes Evidence from raw intake and the only actor that writes Decisions. Humans never author a Decision.
- Shopify is an actor only in the sense that it asserts data; it holds no role and performs no verbs.

---

## 2. Verbs & Entitlements

Who can perform what action, under what conditions.

| Verb | Performed by | Requires role | Requires decision | Authorized by | Phase |
|------|--------------|---------------|-------------------|---------------|-------|
| `SUBMIT_DATA` | Business Owner | Owner | None | Role only | P1 |
| `ANALYZE` | Platform | None | None | Automatic (triggered by data; minimum-data threshold applies) | P1 |
| `PROPOSE_ACTIONS` | Platform | None | BOTTLENECK_DIAGNOSIS = `IDENTIFIED` | Automatic | P1 |
| `PUBLISH_REPORT` | Platform | None | RECOMMENDATION_ASSESSMENT complete (`ASSESSED` or `CANNOT_ASSESS`) | Automatic | P1 |
| `VIEW_REPORT` | Business Owner, Consultant | Owner or Advisor | None | Role only (Advisor requires an owner grant, §7) | P1 |
| `CONNECT_SHOPIFY` | Business Owner | Owner | None | OAuth consent | P2 |
| `SYNC_DATA` | Platform | None | None | `CONNECT_SHOPIFY` completed; active connector | P2 |
| `EXECUTE_ACTION` | Business Owner | Owner | RECOMMENDATION_ASSESSMENT = `ASSESSED`, recommendation verdict `RECOMMENDED` | Business Owner decides | P2 |
| `RECORD_OUTCOME` | Business Owner | Owner | Action executed (`status = done`) | Owner updates | P2 |

**Key principle:** Role determines **WHO** may participate. Decision determines **WHETHER** the action is permitted.

Two consequences:
- The Platform verbs (`ANALYZE`, `PROPOSE_ACTIONS`, `PUBLISH_REPORT`, `SYNC_DATA`) have no human authoriser. They run when their precondition is met and refuse, visibly, when it is not.
- `EXECUTE_ACTION` never blocks an owner from running their business. It blocks an action from being **recorded as recommended by Accord** when no decision said so. An owner who acts against or without a recommendation records it as an override (§14).

---

## 3. Data Access by Role

| Data | Business Owner | Consultant | Platform | Shopify |
|------|----------------|------------|----------|---------|
| Business revenue | READ | READ | READ/WRITE | — |
| Product margins | READ | READ | READ/WRITE | — |
| Customer data (aggregated) | READ | READ | READ/WRITE | READ (if connected) |
| Customer PII (names, emails) | — | — | — | Never collected |
| Monthly diagnosis | READ | READ | — | — |
| Recommendations | READ | READ | — | — |
| Audit trail of decisions | READ | READ (limited to owner's behalf) | READ/WRITE | — |
| Settings & API keys | READ/WRITE | — | READ | — |
| Shopify connection status | READ | READ | READ/WRITE | — |

Notes:
- "Platform — READ/WRITE" on revenue, margins and customer data means the Platform derives Evidence from intake. It does not mean a human operator of Accord can read tenant data; operational access is covered in §6 and §9.
- "Monthly diagnosis" and "Recommendations" are Platform-**written** (as Decision outputs) but are listed as "—" for Platform because no Platform verb *reads them back* except `PUBLISH_REPORT`, which is read-only.
- Shopify's READ on aggregated customer data reflects that the source system holds it; Accord reads it only through the OAuth scope granted in §5.

**PII Rule:** Accord Retail **NEVER** collects, stores, or displays individual customer names, emails, or IDs. All data is aggregated — cohorts, segments, repeat counts — never identifiable individuals.

Implementation of the PII rule:
- CSV intake rejects, at upload, any column that matches a PII pattern (name, email, phone, address). The row set is not ingested until the column is removed.
- Where a stable customer key is needed for repeat-rate and cohort calculation, the Platform stores a **one-way hash** of the source `customer_id` (`Customer.external_ref`), salted per tenant. The original value is discarded at ingest.
- Phase 2 Shopify scopes request `read_orders`, `read_products`, `read_inventory`; customer records are read only to derive cohort and order-count fields, and the PII fields are dropped before persistence.

---

## 4. Phase 1 Access Model (Manual Entry)

**Scenario:** Business Owner submits a form or CSV.

| Step | Actor | Action | Data access | Authorization |
|------|-------|--------|-------------|---------------|
| 1 | Business Owner | Fill form (products, customers, sales, goals) or upload CSV | Write to intake | Owner role |
| 2 | Platform | Ingest & normalize to Evidence | Read intake, Write Evidence | System role |
| 3 | Platform | Run `BOTTLENECK_DIAGNOSIS` | Read Evidence | System role; minimum-data threshold met |
| 4 | Platform | Run `RECOMMENDATION_ASSESSMENT` | Read Bottleneck + Evidence | System role; diagnosis outcome `IDENTIFIED` |
| 5 | Platform | Generate report | Read Decisions | System role |
| 6 | Business Owner | View report | Read report, download PDF | Owner role |
| 7 | Consultant (optional) | View owner's report on their behalf | Read report | Owner grants access (mechanism in §7) |

Access is **per-business (tenant)**. No cross-business visibility.

Phase 1 has exactly one human role with write access — the Owner — and that access is limited to intake. Every derived record (Evidence, Decision, Bottleneck, Recommendation) is Platform-written and read-only to humans.

---

## 5. Phase 2 Access Model (Shopify Connected)

**Scenario:** Business Owner grants Shopify OAuth.

| Step | Actor | Action | Data access | Authorization |
|------|-------|--------|-------------|---------------|
| 1 | Business Owner | Grant OAuth permission | Write Shopify app install | OAuth consent |
| 2 | Platform | Sync Shopify data (daily) | Read Shopify API, Write Evidence | Shopify OAuth scope |
| 3 | Platform | Run `BOTTLENECK_DIAGNOSIS` | Read Evidence | System role |
| 4 | Platform | Generate report | Read Decisions | System role |
| 5 | Business Owner | View report + action history | Read report, Read Action audit trail | Owner role |
| 6 | Business Owner | Execute action (e.g. launch loyalty program) | Update Action status | Owner role + `RECOMMENDED` verdict |
| 7 | Business Owner | Record outcome (e.g. churn improved 3 %) | Write new Evidence (outcome, `provenance = asserted`) | Owner role |
| 8 | Platform | Next month: re-diagnose with new Evidence | Read Evidence | System role |

Step 7 is the only path by which a human writes Evidence after Phase 1 intake. It is always tagged `asserted` (not `observed`), so the next diagnosis can weight it accordingly and a consultant can see which numbers came from the owner rather than the ledger.

---

## 6. Multi-Tenant Isolation (Phase 3)

Each tenant has:
- Separate Evidence, Decision, and Action records
- Separate OAuth connection (if using Shopify)
- Separate audit trail

| Check | Implementation |
|-------|----------------|
| **Database-level isolation** | Every table has `business_id`; all queries are filtered by `business_id` at the DB layer (row-level security or a mandatory scoped repository — never ad-hoc `WHERE` clauses) |
| **API-level isolation** | Every endpoint reads `business_id` from the authenticated request context, never from the request body or query string; returns `403` on mismatch |
| **Audit log isolation** | Every audit entry is tagged with `business_id`; consultants see only their assigned clients' records |
| **No cross-tenant data leakage** | Test: *Can user A see user B's diagnosis?* The answer must be **no** at every layer — DB, API, report rendering, PDF export, and error messages |

The schema is tenant-scoped from Phase 1 (ontology §2: every object carries `business_id`). Phase 3 adds the API and deployment tooling around it; it does not retrofit tenancy.

---

## 7. Consultant Access (Phase 2+)

**Current assumption (to be confirmed):**
- A Consultant acts on behalf of one or more Business Owners.
- A Consultant sees reports and audit trails for **assigned clients only**.
- A Consultant **cannot** modify a diagnosis (read-only).
- A Consultant **can** advise on actions (comment / collaboration feature — TBD).

**Access model:**
1. The Business Owner explicitly shares access: *"grant `[consultant_email]` read access to my reports."*
2. The Platform creates a link: `consultant_id → business_id` (with `granted_at`, `granted_by`, `revoked_at`).
3. The Consultant can `VIEW_REPORT` — report, audit trail, and recommendations — for that business only.
4. The Consultant cannot `EXECUTE_ACTION` or `RECORD_OUTCOME`; the Business Owner does.
5. The Owner can revoke the grant at any time; revocation is itself an audit event.

**Open questions (do not block Phase 1):**
- Can a Consultant hold grants from businesses that compete with each other, and should the Owner be told?
- Does "advise" become a first-class object (a Comment linked to a Recommendation) or stay out-of-band?
- Should a Consultant be able to `SUBMIT_DATA` on an Owner's behalf (agency-managed stores)? Current answer: no.

---

## 8. API Key Security (Phase 2+)

**For Shopify OAuth:**
- Access token stored **encrypted** in a secrets manager (AWS Secrets Manager or equivalent), never in the application database.
- **Never logged, never returned to the client.** Responses expose connection *status* only (§3).
- Stored per business: `business_id → encrypted_shopify_token`.
- **Rotated annually**, or on demand.
- **Revocation:** the Business Owner can disconnect at any time; disconnect deletes the token and stops `SYNC_DATA` on the next scheduled run.

**For external integrations (future — WooCommerce, Square, marketplaces):**
- Same pattern: encrypted, per-business, rotated, owner-revocable.

---

## 9. Audit & Compliance

**Every change is logged with:**

| Field | Content |
|-------|---------|
| **Who** | Actor role (and `user_id` where a human) |
| **What** | Action / verb |
| **When** | Timestamp (UTC) |
| **Why** | Decision outcome that authorised it (`decision_id`), or `role_only` for intake verbs |
| **What changed** | Before / after for mutations |

**Immutability:** the audit trail is **append-only**. Entries cannot be deleted or edited. Phase 2 makes it tamper-evident (hash-chained or signed, §12).

**Retention:** indefinite, or per legal / compliance requirement.

**Reports available to the Business Owner:**
- *"Show me all decisions about my business."*
- *"Show me all actions taken."*
- *"Show me all data changes."*
- *"Show me who accessed my data and when."*

The Decision record itself (ontology §9 — `input_evidence`, `input_digest`, `reasoning`, `concluded_at`) is part of the audit trail. The audit log answers *who did what*; the Decision record answers *why the platform concluded what it did*.

---

## 10. Approval Workflows

**Phase 1 — no multi-party workflows:**
- Business Owner submits data.
- Platform auto-analyzes.
- Report published. No approval needed.

**Phase 2 — potential multi-party (TBD):**
- If a business has multiple owners (e.g. partners), should both approve an action before it is recorded?
- **Currently: no.** An Owner records an action unilaterally. Add an approval step later if needed.

**Phase 3 — governance gates (TBD):**
- High-investment actions (e.g. hiring, rebranding) might require CFO approval before recording.
- **Currently: out of scope.** Accord records what the owner did; the owner is accountable.

Design rule for when approvals are added: an approval is a **verb entitled by a decision**, not a role override. It gates `EXECUTE_ACTION`; it never modifies a Decision.

---

## 11. Data Retention & Deletion

**Data retention:**

| Record | Retention | Reason |
|--------|-----------|--------|
| Evidence | Indefinite | Historical data supports trend detection |
| Decisions | Indefinite | Audit trail; replay |
| Actions | Indefinite | Accountability |
| Audit logs | Indefinite | Compliance |
| Raw intake (CSV files) | 90 days after successful ingest | Reprocessing window; then deleted |
| Shopify tokens | Until disconnect | Deleted immediately on revocation |

**User deletion (GDPR / privacy):**

If a Business Owner requests data deletion:
- **Can** stop future data collection (disconnect Shopify; close account).
- **Cannot** delete past Evidence / Decisions / Audit (legal hold; the records describe the business, not a person).
- **Can** request a PII purge — Accord stores no PII (§3), so the purge confirms there is nothing to remove and the response is recorded in the audit log.

Where a legal requirement forces deletion of a tenant's records, the deletion is performed at tenant level, logged as its own audit event, and the Decision digests are retained so the deletion can be proven.

---

## 12. Security Checklist (Phase 1 → Phase 2 transition)

- [ ] All API endpoints require authentication (JWT or OAuth)
- [ ] All database queries filtered by `business_id` (tenant isolation)
- [ ] Secrets (API keys, credentials) stored encrypted, never logged
- [ ] Audit trail immutable and tamper-evident (hash-chained or signed)
- [ ] CSV uploads validated and scanned for injection / malware (size limit, MIME check, formula-injection stripping of leading `=`, `+`, `-`, `@`)
- [ ] CSV uploads rejected if PII columns are detected (§3)
- [ ] Rate limiting on sync and upload endpoints (prevent API abuse)
- [ ] Error messages don't leak data (no *"user john@example.com not found"*)
- [ ] Logs don't contain sensitive data (revenue figures, customer counts anonymised)
- [ ] HTTPS only (no HTTP)
- [ ] CORS configured — only authorised domains
- [ ] Cross-tenant test (§6) passes at DB, API, report, and PDF layers

---

## 13. Roles & Permissions Matrix

Simple reference:

| Role | `SUBMIT_DATA` | `ANALYZE` | `VIEW_REPORT` | `EXECUTE_ACTION` | `RECORD_OUTCOME` | `ADMIN` |
|------|:---:|:---:|:---:|:---:|:---:|:---:|
| **Business Owner** | ✓ | — | ✓ | ✓ | ✓ | ✓ (own business) |
| **Consultant** | — | — | ✓\* | — | — | — |
| **Platform** | — | ✓ | — | — | — | ✓ |

\* Consultant sees the report only if the Business Owner grants access (§7).

`ADMIN` for an Owner means: manage settings, grant/revoke consultant access, connect/disconnect Shopify, request deletion — for their own business only. `ADMIN` for the Platform means: scheduler, connector lifecycle, migrations — never reading tenant data outside a logged, scoped operation.

---

## 14. Decision Authorization Logic

Decision outcomes gate actions.

| Decision | Outcome / verdict | Action entitlements |
|----------|-------------------|---------------------|
| `BOTTLENECK_DIAGNOSIS` | `IDENTIFIED` | `PROPOSE_ACTIONS` — recommendations can be generated |
| `BOTTLENECK_DIAGNOSIS` | `IDENTIFIED` (confidence < 0.7) | `PROPOSE_ACTIONS`, with the low-confidence flag carried into every recommendation and the report |
| `BOTTLENECK_DIAGNOSIS` | `CANNOT_DECIDE` | No actions (missing or contradicted data); report names what to supply |
| `RECOMMENDATION_ASSESSMENT` | `ASSESSED` → recommendation verdict `RECOMMENDED` | `EXECUTE_ACTION` — Business Owner can act and the action is recorded as recommended |
| `RECOMMENDATION_ASSESSMENT` | `ASSESSED` → recommendation verdict `NOT_RECOMMENDED` | No entitled action. The Business Owner **can override**: the action is recorded with `authorization = owner_override` and the decision it contradicts |
| `RECOMMENDATION_ASSESSMENT` | `CANNOT_ASSESS` | No action (missing data); report names what to supply |

**Override rule.** An owner override is always permitted and always visible. It is recorded against the Decision it overrides, so the next diagnosis and any consultant review can see that the business acted outside the recommendation. Accord never silently blocks and never silently allows.

---

*This document is a living specification. Update it as you add features, consultants, and governance rules. Changes to §2 (verbs), §13 (matrix), or §14 (authorization logic) require a corresponding update to the ontology and a version bump on both.*
