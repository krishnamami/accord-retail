# PRD — Accord Retail

**Product:** Accord Retail — Retail Sales Intelligence
**Version:** 1.0 (Phase 1)
**Status:** Draft for review
**Date:** September 12, 2026
**Owner:** krishnamami
**Related docs:** [`CONTEXT.md`](./CONTEXT.md) · `ARCHITECTURE.md` (pending)
**Portfolio:** Accord Solutions · Parent platform: Context-OS

---

## TL;DR

Retail operators have sales data everywhere and answers nowhere. Accord Retail takes a
business's sales, customer, product, and channel data — entered by form or CSV in Phase 1 —
and returns four things: **where growth is coming from, where revenue is leaking, which
opportunities are worth pursuing, and the top 3 actions to take next**, ranked by impact
versus effort. It is a sales intelligence product, not another dashboard.

---

## 1. Problem Statement

### 1.1 The core problem

Retail businesses — from a single Shopify store to a regional chain — cannot answer four
questions about their own business:

| # | Question | Why it matters |
|---|----------|----------------|
| 1 | **Where is my sales growth coming from?** | Without it, spend goes to the loudest channel, not the best one |
| 2 | **Where am I losing customers and revenue?** | Leaks compound silently: churn, low performers, margin erosion, conversion drop-off |
| 3 | **What are my highest-potential opportunities?** | Under-served segments and under-used channels stay invisible |
| 4 | **What should I prioritize first?** | Limited time and cash mean the *order* of initiatives is the decision |

The data to answer these questions already exists — in POS exports, ecommerce admin panels,
marketplace reports, ad platforms, and spreadsheets. The problem is that it is
**unnormalized** (different schemas per system), **unjoined** (product, customer, and channel
data live apart), and **never turned into a ranked decision**.

### 1.2 Why existing solutions don't work

| Category | Examples | Where it falls short |
|----------|----------|----------------------|
| **Platform-native analytics** | Shopify Analytics, Amazon Seller Central reports, Square Dashboard | Sees one channel only. A seller on Shopify + Amazon + a physical store gets three disconnected views and no combined truth |
| **Generic BI tools** | Looker Studio, Power BI, Tableau, Metabase | Blank canvas. Requires the operator to model the data, define retail metrics, and interpret the charts themselves. Reports *what happened*; never says *what to do* |
| **Spreadsheets** | Excel, Google Sheets | The de facto integration layer. Manual, fragile, stale, and analysis depth is capped by the owner's time and skill |
| **Consultants / fractional analysts** | Agencies, freelance analysts | Produce the right output but cost $5k–$20k per engagement and deliver a point-in-time snapshot, not a repeatable process |

Every option is either **not unified** (single-channel) or **too generic** (dashboards
with no retail intelligence). None produces a prioritized action list.

### 1.3 Impact

| Cost | How it shows up |
|------|-----------------|
| **Money lost** | Ad budget kept on channels with declining contribution; SKUs carried at negative margin; discounting that erodes price without lifting volume; repeat-customer churn unnoticed until revenue dips |
| **Time wasted** | Owners and managers spend hours per week rebuilding spreadsheet reports instead of running the business; analysis is redone from scratch every quarter |
| **Decisions missed** | Best-performing segment never gets more inventory or marketing; underused channel never gets tested; the highest-leverage fix is buried under ten lower-value ones |

The operator's real bottleneck is not *data* — it is a **ranked answer**.

---

## 2. Personas

### 2.1 Persona summary

| | **Maya — Small E-Commerce Owner** | **Derek — Regional Chain Operations Manager** | **Priya — Multi-Marketplace Seller** |
|---|---|---|---|
| **Business** | DTC skincare brand on Shopify, ~$600k/yr | 8-location home & garden chain, ~$14M/yr, Square POS + WooCommerce site | Consumer electronics accessories on Amazon, eBay, Walmart, and own site, ~$2.5M/yr |
| **Team** | Solo + 1 part-time VA | 8 store managers, 1 marketing coordinator, part-time bookkeeper | 3 people: owner, ops lead, listings specialist |
| **Data today** | Shopify Analytics, Meta Ads Manager, Klaviyo, a Google Sheet | Square reports per store, WooCommerce admin, monthly P&L from accountant | Four marketplace dashboards, a 3PL portal, weekly Excel roll-up |
| **Technical comfort** | Low — can export a CSV, won't touch SQL | Medium — comfortable with Excel pivots | Medium-high — has tried Looker Studio and abandoned it |
| **Current pain** | "I'm spending $9k/month on ads and I genuinely don't know if new customers or repeat buyers are driving growth" | "Two stores are dragging the region down and I can't tell if it's product mix, staffing, or local competition" | "Amazon fees keep rising. I don't know which SKUs are still profitable per channel or where to shift inventory" |
| **Decision they need to make** | Where to put the next $3k of marketing spend; whether to invest in retention or acquisition | Which stores and categories to fix first with a limited Q4 budget | Which SKUs to pull from which marketplace and which channel to grow |
| **What "success" looks like** | A clear answer on growth source + 3 things to do this month | A ranked list of store/category problems with expected impact | A per-channel profitability view and a reallocation plan |
| **Phase 1 data entry** | CSV export from Shopify (orders, customers, products) + form for ads/goals | CSV export from Square per store + form for channels/competitors | CSV exports per marketplace + form for fees/goals |

### 2.2 Persona detail

**Maya — Small E-Commerce Owner**
- *Background:* Founded the brand 3 years ago. Growth was 40% YoY until this year when it
  flattened. Reads Shopify Analytics weekly but the numbers don't tell her *why*.
- *Pain point:* She cannot decompose growth into new vs. repeat customers, product lines,
  or channels. Ad spend has crept up while revenue held flat — she suspects a leak but
  can't locate it.
- *Needs to decide:* Retention vs. acquisition focus for the next quarter, and which two
  product lines to push.

**Derek — Regional Chain Operations Manager**
- *Background:* 12 years in retail ops. Reports to an owner who asks "why is the region
  down 6%?" at every monthly review. Builds the answer by hand from 8 Square exports.
- *Pain point:* Store-level and category-level performance are never in the same view.
  He knows *which* stores underperform but not *what* is driving it, so fixes are guesses.
- *Needs to decide:* How to allocate a fixed Q4 improvement budget across stores and
  categories for maximum regional impact.

**Priya — Multi-Marketplace Seller**
- *Background:* Scaled from Amazon-only to four channels in two years. Margin has
  compressed as fees rose and competition intensified.
- *Pain point:* Each marketplace reports differently; no unified per-SKU, per-channel
  contribution margin exists. She is likely carrying loss-making SKUs on at least one
  channel without knowing which.
- *Needs to decide:* Which SKU/channel combinations to cut, which channel to invest in,
  and where inventory should sit.

---

## 3. Solution Overview

### 3.1 What Accord Retail does

Accord Retail is a **Retail Sales Intelligence platform**. It ingests a retailer's sales,
customer, product, and channel data, normalizes it into one schema, runs a retail analysis
engine over it, and returns a report with four outputs:

| Output | Definition | Answers question |
|--------|------------|------------------|
| **Sales sources** | Growth decomposed by product, customer segment, channel, and time period | #1 — Where is growth coming from? |
| **Loss drivers** | Low performers, customer churn, conversion leaks, margin erosion | #2 — Where am I losing revenue? |
| **Opportunities** | High-potential segments, underused channels, cross-sell / upsell paths | #3 — What has the most upside? |
| **Prioritized actions** | Top 3 initiatives ranked by impact vs. effort | #4 — What do I do first? |

Pipeline (see `ARCHITECTURE.md` for the full spec):

```
Sources (form / CSV  →  later: Shopify / WooCommerce / Square)
    ↓  connector layer
Normalized schema (products · customers · sales · channels · inventory · pricing · marketing)
    ↓  analysis engine
Metrics → gap detection → opportunity identification → prioritization
    ↓
Report  (sources · losses · opportunities · top 3 actions)
```

### 3.2 Key differentiator: unified view + intelligent analysis

| | Dashboards (status quo) | Accord Retail |
|---|---|---|
| **Scope** | One platform at a time | All channels and stores in one normalized model |
| **Output** | Charts the user must interpret | Findings the user can act on |
| **Question answered** | "What happened?" | "What is driving it, and what should I do next?" |
| **Prioritization** | None — everything has equal weight | Top 3 actions ranked by impact vs. effort |
| **Retail knowledge** | User must supply it | Built into the engine (churn, margin, channel mix, SKU performance) |
| **Setup** | Model the data yourself | Fill a form or upload a CSV |

The product is **not** a BI tool with retail templates. The unit of value is a
**ranked decision**, not a visualization. Charts exist only to support the findings.

### 3.3 How it solves each persona's problem

| Persona | Sales sources | Loss drivers | Opportunities | Prioritized actions |
|---------|---------------|--------------|---------------|---------------------|
| **Maya** | Growth split new vs. repeat, by product line, by channel | Rising CAC vs. flat revenue; repeat rate decline in a cohort; discount-heavy SKUs | Under-marketed product line with high repeat rate; email channel underused | e.g. (1) Shift $2k/mo from prospecting to retention flows, (2) Bundle the two highest-repeat SKUs, (3) Cut the two lowest-margin SKUs from paid ads |
| **Derek** | Regional growth by store × category | Two stores' category mix skewed to low-margin lines; one store's transaction count down 15% | Categories strong in 6 stores but under-stocked in the 2 laggards | e.g. (1) Rebalance inventory in laggard stores toward top regional categories, (2) Investigate store 4 traffic drop, (3) Standardize the promo calendar |
| **Priya** | Contribution by SKU × marketplace after fees | SKUs profitable on own site but negative on Amazon after FBA fees; eBay returns rate | Walmart channel growing fastest with lowest competition | e.g. (1) Delist 11 negative-margin SKUs from Amazon, (2) Move inventory toward Walmart, (3) Raise price on 4 SKUs with inelastic demand |

---

## 4. User Journey (Phase 1)

| Step | User action | System behavior | Exit criteria |
|------|-------------|-----------------|---------------|
| **1. Sign up** | Creates an account with email + password; names the business | Creates tenant (`tenant_id` scoped from day one); shows onboarding | User lands on the intake screen in < 2 minutes |
| **2. Enter business data** | Chooses **form** or **CSV upload**. Form covers: products, customers, current sales, pricing, channels, marketing, competitors, goals. CSV covers: orders, customers, products (templates provided) | Validates inputs, maps to normalized schema, surfaces missing or inconsistent fields, shows a data-completeness score | Data passes minimum-completeness threshold; user confirms "Analyze" |
| **3. System analyzes** | Waits (target < 60 seconds) | Runs metrics → gap detection → opportunity identification → prioritization across sales sources, loss drivers, and opportunities | Report generated |
| **4. Receive action plan** | Reads the report: sources, loss drivers, opportunities, **top 3 actions** with expected impact and effort | Renders report with plain-language findings, supporting numbers, and confidence notes where data was thin | User can state the 3 actions and why they're ranked that way |
| **5. Take action** | Marks each action as *planned* / *done* / *skipped*; optionally schedules a follow-up analysis | Stores action status; prompts for a re-run after 30 days to measure change | At least one action marked *planned*; follow-up scheduled |

**Guiding rules for the journey**
- Time from sign-up to first report: **< 20 minutes** with a CSV, **< 30 minutes** by form.
- Every finding must cite the data behind it — no "black box" recommendations.
- If data is insufficient for a finding, the report says so and names the missing input,
  rather than fabricating a number.

---

## 5. Success Metrics

### 5.1 Outcome metrics (does the product work?)

| Metric | Definition | Phase 1 target |
|--------|------------|----------------|
| **Growth clarity** | User can answer "where is my growth coming from?" after reading the report (post-report survey, yes/no) | ≥ 80% yes |
| **Leak identification** | User can name their top 3 revenue leaks from the report | ≥ 80% can |
| **Prioritization** | User can list their next 3 initiatives and the impact rationale | ≥ 80% can |
| **Actionable insights** | Average number of findings the user rates "actionable" per report | ≥ 3 |

### 5.2 Funnel metrics (do users get through it?)

| Metric | Definition | Phase 1 target |
|--------|------------|----------------|
| **Analysis completion** | % of sign-ups that reach a generated report | ≥ 60% |
| **Time to first report** | Median minutes from sign-up to report | ≤ 20 min (CSV) |
| **Data completeness** | Median completeness score at "Analyze" | ≥ 70% |
| **Return for follow-up** | % of users who run a second analysis within 45 days | ≥ 40% |
| **Action follow-through** | % of reports with ≥ 1 action marked *planned* or *done* | ≥ 50% |

Targets are starting hypotheses for a 10-user beta; they will be re-baselined after Phase 1.

---

## 6. Scope

### 6.1 In scope — Phase 1

| Area | Included |
|------|----------|
| **Accounts** | Sign-up, login, single business per account |
| **Intake** | Structured form (products, customers, sales, pricing, channels, marketing, competitors, goals); CSV upload with templates for orders, customers, products |
| **Data model** | Normalized schema: products, customers, sales, channels, inventory, pricing, marketing — `tenant_id` on every table |
| **Analysis engine** | Metrics, gap detection, opportunity identification, impact/effort prioritization |
| **Report** | Sales sources, loss drivers, opportunities, top 3 prioritized actions; exportable as PDF |
| **Follow-up** | Action status tracking; re-run analysis on updated data |
| **Demo** | End-to-end run on synthetic retail data; polished demo video |

### 6.2 Out of scope — Phase 1

| Item | Why deferred | Target phase |
|------|--------------|--------------|
| **Live connectors** (Shopify, WooCommerce, Square, Amazon) | Validate the analysis output before paying the OAuth/sync integration cost | Phase 2 |
| **Continuous data sync** | Depends on live connectors | Phase 2 |
| **Multi-tenant admin** (org management, roles, billing, per-tenant deployments) | Schema is tenant-scoped from day one; admin tooling is not needed for a 10-user beta | Phase 2–3 |
| **Advanced forecasting** (demand prediction, scenario modeling, ML-driven projections) | Requires a longer data history and a validated baseline engine | Phase 2+ |
| **Execution platform** (auto-applying recommendations, pushing changes to Shopify, launching campaigns) | Accord Retail **prioritizes** actions; it does not execute them. Execution belongs to the operator | Not planned |
| **Inventory / supply-chain optimization** | Different problem space; inventory is an input to margin analysis only | Not planned in Retail |
| **Native mobile app** | Web-only for beta | Later |

**Scope rule:** Phase 2 begins only when Phase 1 produces a report a beta user acts on.
Connectors are not started until the analysis engine is proven worth integrating.

---

## 7. Dependencies & Risks

### 7.1 Dependencies

| Dependency | Type | Status | Note |
|------------|------|--------|------|
| **`ARCHITECTURE.md` finalized** | Internal | Pending | Data model, connector interface, and analysis engine spec must be locked before build starts |
| **Normalized schema** | Internal | Defined (7 entities) | Analysis engine contract depends on it |
| **Synthetic retail dataset** | Internal | Not started | Needed for engine development, tests, and the demo video |
| **EDMS pattern** (`edms-simulator`) | Reference | Available | Architecture mirrors data → normalize → analyze → report |
| **Decision OS** (`decision-os`) | Reference | Available | Tenant isolation and API-first principles |
| **10 beta users** | External | Not recruited | Mix across the three personas |

### 7.2 Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Users underestimate the value of analysis** — they expect a dashboard and don't see why a ranked action list is different | High | High | Lead with the top 3 actions, not the charts; demo video shows a before/after decision; onboarding frames the four questions up front |
| **Manual data-entry friction** — form is long, CSV mapping fails, users abandon before "Analyze" | High | High | CSV templates matching Shopify/Square export formats; progressive form with completeness score; allow partial analysis with flagged gaps. Phase 2 connectors remove this entirely |
| **Analysis quality on thin data** — a small store with 3 months of history yields weak findings | Medium | High | Confidence notes on every finding; minimum-data thresholds; report names what to add for better results rather than guessing |
| **Recommendations feel generic** — "improve retention" instead of a specific, numbered action | Medium | High | Every action must cite the data, quantify expected impact, and reference specific SKUs/channels/segments |
| **Scope creep toward connectors or forecasting** | Medium | Medium | Sequencing rule in §6.2; connectors gated on Phase 1 success criteria |
| **Beta recruitment** — fewer than 10 users complete the flow | Medium | Medium | Recruit 15–20 to net 10 completions; offer the report free in exchange for feedback |
| **Data sensitivity** — users hesitate to upload sales and customer data | Low | Medium | Tenant isolation from day one; no PII required for analysis (customer IDs may be hashed); clear data-handling statement at upload |

---

## 8. Success Criteria (Phase 1 exit)

Phase 1 is complete when **all** of the following are true:

| # | Criterion | Measure | Status |
|---|-----------|---------|--------|
| 1 | **10 beta users complete analysis + report** | 10 distinct tenants with a generated report, spanning at least 2 of the 3 personas | ☐ |
| 2 | **Average user finds 3+ actionable insights** | Post-report survey; mean "actionable" findings ≥ 3 | ☐ |
| 3 | **Demo video produced and polished** | End-to-end walkthrough on synthetic data: sign-up → intake → report → actions; suitable for external audiences | ☐ |
| 4 | **Ready to add first live connector (Shopify)** | Connector interface defined in `ARCHITECTURE.md`; form and CSV connectors implemented against it; adding Shopify requires no change to the analysis engine | ☐ |
| 5 | **Engine validated on synthetic and real data** | Ingestion, normalization, analysis, and end-to-end test suites green; at least 3 beta reports reviewed manually for correctness | ☐ |

**Phase 1 does not exit** on partial completion. If criterion 2 fails, the analysis engine
is revised before any connector work begins.

---

## Appendix A — Open Questions

| # | Question | Owner | Needed by |
|---|----------|-------|-----------|
| 1 | Impact/effort scoring model — fixed heuristics or configurable per tenant? | Architecture | `ARCHITECTURE.md` |
| 2 | Minimum data thresholds per finding type (e.g. months of history for churn) | Analysis engine | Before beta |
| 3 | Do we require customer-level rows in Phase 1, or support aggregate-only intake? | Product | Before form design |
| 4 | Report format: web-only, PDF export, or both in beta? | Product | Before beta |
| 5 | Beta recruitment channel for the three personas | Founder | Before build complete |

## Appendix B — Glossary

| Term | Meaning |
|------|---------|
| **Sales source** | A decomposition of revenue growth by product, customer segment, channel, or period |
| **Loss driver** | A quantified cause of lost revenue or margin: churn, low performers, conversion leaks, margin erosion |
| **Opportunity** | An under-exploited segment, channel, or product path with quantified upside |
| **Prioritized action** | A specific initiative with expected impact, effort, and rank |
| **Connector** | A pluggable data source (form, CSV, Shopify, WooCommerce, Square) mapping into the normalized schema |
| **Normalized schema** | The single data model the analysis engine reads: products, customers, sales, channels, inventory, pricing, marketing |
| **Tenant** | One business account; every row is scoped by `tenant_id` |

---

*Document history*

| Version | Date | Change |
|---------|------|--------|
| 1.0 | 2026-09-12 | Initial draft aligned to `CONTEXT.md` |
