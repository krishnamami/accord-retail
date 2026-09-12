# CONTEXT.md — Accord Retail

**Session Date:** September 12, 2026
**Session Focus:** Architecture and positioning finalized for Accord Retail
**Repo:** https://github.com/krishnamami/accord-retail
**Portfolio:** Accord Solutions (5 industry applications) · Parent platform: Context-OS

---

## 1. What Was Accomplished This Session

| # | Item | Outcome |
|---|------|---------|
| 1 | Problem statement defined | Four questions retail operators cannot answer today |
| 2 | Product positioning locked | Retail **Sales Intelligence** platform, not a BI dashboard |
| 3 | Output contract defined | Sources · Loss drivers · Opportunities · Prioritized actions |
| 4 | Architecture decisions made | 7 decisions (multi-tenant, connector pattern, normalized model, 3 phases) |
| 5 | Phase scope split | Phase 1 manual intake → Phase 2 live connectors → Phase 3 multi-tenant scale |
| 6 | Reuse path confirmed | Same architecture powers all 5 Accord applications |
| 7 | Repo created | Empty; no code committed yet |

### Problem Identified

Retail businesses cannot answer:

1. **Where is my sales growth coming from?**
2. **Where am I losing customers and revenue?**
3. **What are my highest-potential opportunities?**
4. **What should I prioritize first?**

Data exists (POS, ecommerce, spreadsheets) but is unnormalized, unjoined, and never turned
into a ranked decision. Existing tools report *what happened*; nobody answers *what to do next*.

### Solution

A Retail Sales Intelligence platform that ingests sales, customer, product, and channel data
and produces four outputs:

| Output | Definition |
|--------|-----------|
| **Sales sources** | Growth decomposed by product, customer, channel, and time period |
| **Loss drivers** | Low performers, customer churn, conversion leaks, margin erosion |
| **Opportunities** | High-potential segments, underused channels, cross-sell / upsell paths |
| **Prioritized actions** | Top 3 initiatives ranked by impact vs. effort |

---

## 2. Current Test Results

**N/A** — no code written yet.

| Suite | Status |
|-------|--------|
| Ingestion tests | Not started |
| Normalization tests | Not started |
| Analysis engine tests | Not started |
| End-to-end (form → report) | Not started |

_Placeholder: populate once the Phase 1 prototype lands._

---

## 3. Architecture Decisions Made

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | **Multi-tenant from day one** — `tenant_id` scoped on all data | Retrofitting tenancy is the single most expensive rewrite; cost is near-zero if done at schema creation |
| 2 | **Connector pattern** — pluggable sources (form, CSV, Shopify, WooCommerce, Square) | New data source = new connector, zero change to analysis engine |
| 3 | **Normalized data model** — products, customers, sales, channels, inventory, pricing, marketing | Analysis engine reads one schema regardless of origin system |
| 4 | **Phase 1 = manual entry (form + CSV)** | Validates the analysis engine before spending effort on OAuth integrations |
| 5 | **Phase 2 = live connectors** | Real-time data once the analysis output is proven valuable |
| 6 | **Phase 3 = multi-tenant scale** across all Accord products | Shared infrastructure, independent deployments |
| 7 | **Same architecture powers all 5 Accord applications** (retail, logistics, field service, knowledge, proposals) | Only connectors + metric definitions are industry-specific; pipeline is constant |

### Pipeline Shape

```
Sources (form / CSV / Shopify / WooCommerce / Square)
    ↓  connector layer
Normalized schema (products · customers · sales · channels · inventory · pricing · marketing)
    ↓  analysis engine
Metrics → gap detection → opportunity identification → prioritization
    ↓
Report / dashboard  (sources · losses · opportunities · top 3 actions)
```

This mirrors the EDMS pattern: **data → normalize → analyze → report**.

### Phase Scope

**Phase 1 — Validate the analysis engine**
- Form intake: products, customers, current sales, pricing, channels, marketing, competitors, goals
- CSV upload capability
- Normalized ingestion to the standard schema
- Analysis engine: metrics, gap detection, opportunity identification, prioritization
- Report / dashboard output

**Phase 2 — Live data**
- Shopify connector (OAuth, real-time sales data)
- WooCommerce connector
- Square connector
- Continuous sync to keep data fresh
- Everything else runs as-is — **analysis engine unchanged**

**Phase 3 — Scale**
- Multi-tenant API
- Independent deployments
- Accordion platform (shared infrastructure)
- Support for all 5 industries

### Known Dependencies

| Dependency | Note |
|------------|------|
| **EDMS** (`edms-simulator`) | Architecture mirrors its data → normalize → analyze → report flow |
| **Decision OS** (`decision-os`) | Same principles: tenant isolation, API-first |
| **Accord portfolio** | Must eventually support 5 industry products without a rewrite |

---

## 4. Files Created

**N/A** — repo is empty. No files committed this session.

| Planned file | Purpose | Status |
|--------------|---------|--------|
| `PRD.md` | Problem statement, personas, success metrics | Not started |
| `ARCHITECTURE.md` | Data model, connectors, analysis engine | Not started |
| `CONTEXT.md` | This document | Created (uncommitted) |

---

## 5. Repo State

| Item | State |
|------|-------|
| Repo | https://github.com/krishnamami/accord-retail |
| Contents | Empty — no commits on `main` |
| Phase 1 architecture | **Defined** |
| Phase 1 prototype | Not started |
| Demo | Not started |
| Tests | None |
| PRD | Not started |
| ARCHITECTURE doc | Not started |

---

## 6. What To Do Next

| Order | Task | Definition of Done |
|-------|------|--------------------|
| 1 | **Finalize `PRD.md`** | Problem statement, personas, success metrics written |
| 2 | **Finalize `ARCHITECTURE.md`** | Data model, connector interface, analysis engine spec written |
| 3 | **Build Phase 1 prototype** | Form + CSV ingestion → normalized data → analysis → report |
| 4 | **Demo the analysis** | Runs end-to-end on synthetic retail data |
| 5 | **Add Shopify connector** | Phase 2 begins only after Phase 1 works |

Sequencing rule: **do not start connectors until the analysis engine produces a report
someone would act on.** Phase 1 exists to prove the output is worth the integration cost.

---

## 7. Key Numbers To Remember

| Number | Meaning |
|--------|---------|
| **4** | Questions the platform must answer (growth sources, losses, opportunities, priorities) |
| **4** | Analysis outputs produced (sources, loss drivers, opportunities, prioritized actions) |
| **3** | Initiatives in the prioritized action list (ranked by impact / effort) |
| **3** | Delivery phases (manual intake → live connectors → multi-tenant scale) |
| **5** | Accord industry applications sharing this architecture |
| **5** | Connector types planned (form, CSV, Shopify, WooCommerce, Square) |
| **7** | Normalized entities (products, customers, sales, channels, inventory, pricing, marketing) |
| **7** | Architecture decisions locked this session |
| **1** | `tenant_id` scoped on every table, from day one |
| **0** | Files committed to the repo so far |

---

## Team & Context

- **Portfolio:** Accord Solutions — 5 industry-specific applications
  (retail, logistics, field service, knowledge, proposals)
- **Parent platform:** Context-OS — unified multi-tenant intelligence platform
- **Related repos:** [`edms-simulator`](https://github.com/krishnamami/edms-simulator) ·
  [`decision-os`](https://github.com/krishnamami/decision-os)
