# Product Specification — Marsh Vantage

**FP&A Variance Analysis & Intelligence Platform**
**Version:** 2.0 | **Last Updated:** 2026-04-04

---

## 1. Vision

An AI-powered platform that automatically detects material variances across the P&L, understands WHY they occurred through 360-degree intelligence analysis, generates narrative explanations at every level of the organization, and routes them through a structured review/approval workflow before distribution to leadership.

**Core value chain:** Data → Variances → Intelligence → Narratives → Review → Reports → Decisions

---

## 2. Personas

### 2.1 Analyst (FP&A)
- **Job:** Investigate variances, review AI-drafted narratives, explain root causes
- **Sees:** All variances, all statuses, detail-level narratives
- **Does:** Edit narratives, provide hypothesis feedback, approve drafts
- **Pages:** Dashboard, P&L, Chat, Review, Reports

### 2.2 BU Leader
- **Job:** Understand own BU's variance picture
- **Sees:** Own BU only, reviewed + approved, midlevel narratives
- **Restriction:** Cannot see other BUs
- **Pages:** Dashboard (BU-scoped), P&L, Chat, Reports

### 2.3 Director (Finance Director)
- **Job:** Approve analyst commentary, quality-gate reports
- **Sees:** All BUs, reviewed + approved, midlevel narratives
- **Does:** Approve/hold narratives, bulk approve, trigger summary regeneration
- **Pages:** Dashboard, P&L, Chat, Approvals, Reports, Exec Summary

### 2.4 CFO
- **Job:** Consume the approved financial story
- **Sees:** Approved only, summary-level narratives
- **Does:** Final approval authority, generate board reports
- **Pages:** Exec Summary (landing), Dashboard, P&L, Chat, Approvals, Reports

### 2.5 HR Finance
- **Job:** Analyze headcount-related cost variances only
- **Sees:** HC domain accounts only (Salaries, Benefits, Contractors, Training, Recruitment)
- **Pages:** Dashboard (HC-filtered), P&L, Chat, Review

### 2.6 Board Viewer
- **Job:** Read the final financial narrative
- **Sees:** Approved only, board + summary level
- **Pages:** Exec Summary (landing), Reports

### 2.7 Admin
- **Job:** Configure platform, manage users, run engine
- **Sees:** Everything
- **Pages:** All pages + Admin panel + Engine Control

---

## 3. Application Pages

### 3.1 Executive Summary (`/executive`)
Narrative-first landing page for CFO/Director/Board. Tells the financial story with supporting visuals.

| Section | Content |
|---|---|
| **Headline** | AI-generated period summary ("May 2026: Revenue down 2.4%, EBITDA down 12.5%") |
| **KPI Cards** | Revenue, EBITDA, Gross Profit, Net Income with variance % |
| **Revenue Section** | Section narrative + colored driver pills |
| **Cost Section** | COGS + OpEx narratives with drivers |
| **Profitability** | 3 margin gauges (Gross, EBITDA, Net) + narrative |
| **Risk Items** | Netting alerts + trend alerts |
| **Full Narrative** | 3-paragraph CFO-ready story |
| **Downloads** | Board Deck (PPTX) + Executive Flash (PDF) |

### 3.2 Dashboard (`/`)
Operational view for analysts. Tables, charts, alerts, variance drill-down.

| Section | Content |
|---|---|
| **KPI Cards** | 5 cards with sparklines |
| **Executive Summary** | AI-generated narrative (persona-appropriate level) |
| **Alert Cards** | Netting pairs + trending variances |
| **Waterfall Chart** | EBITDA bridge from comparator to actual |
| **Revenue Trend** | 12-month trailing with actual vs budget |
| **Variance Heatmap** | BU × Geography matrix |
| **Material Variances** | Sortable, searchable table → click for detail modal |

### 3.3 P&L View (`/pl`)
Hierarchical P&L with expand/collapse, calculated rows, margin gauges, narrative panel.

### 3.4 Chat (`/chat`)
Conversational AI agent. Classifies intent, queries computation engine, streams response via SSE.

### 3.5 Review Queue (`/review`)
Analyst landing: edit narratives, provide hypothesis feedback, approve drafts. Sorted by impact/SLA.

### 3.6 Approval Queue (`/approval`)
Director/CFO: bulk approve analyst-reviewed items. Report gate (only approved in reports).

### 3.7 Reports (`/reports`)
Generate XLSX/PDF/PPTX/DOCX. Schedule automated generation. All reports pull from narrative pyramid.

### 3.8 Admin (`/admin`)
Thresholds, model routing, users & roles, audit log, **engine control** (Phase 3).

---

## 4. Global Filters

| Filter | Options | Default | Effect |
|---|---|---|---|
| **Business Unit** | Marsh, Mercer, Guy Carpenter, Oliver Wyman, MMC Corporate, All | All | Scopes all data |
| **View Type** | MTD, QTD, YTD | MTD | Time aggregation |
| **Comparison Base** | Budget, Forecast, Prior Year | Budget | Comparator |
| **Period** | 36 months (2024-01 to 2026-12) | Latest | Analysis period |
| **Dimension** | Geography / Segment / LOB / Cost Center tree | None | Hierarchy filter |

---

## 5. Narrative Pyramid

Narratives are generated bottom-up — each layer consumes the approved output of the layer below.

```
Layer 7: BOARD NARRATIVE (on-demand, approval-gated)
Layer 6: EXECUTIVE SUMMARY (headline + 3-paragraph narrative + risks)
Layer 5: SECTION NARRATIVES (Revenue, COGS, OpEx, Non-Op, Profitability)
Layer 4: PARENT SUMMARIES (reference approved children)
Layer 3: LEAF DETAIL (decomposition + correlations + all intelligence context)
Layer 2: QTD (from MTD monthly progression)
Layer 1: YTD (from QTD quarterly context)
```

### Generation Stages (Independent, Each Feeds Next)

| Stage | Input | Output | LLM Calls/Period |
|---|---|---|---|
| Stage 1: Leaves | Variance + all 14 intelligence dimensions | 4-level narrative per leaf | ~4,800 |
| Stage 2: Parents | Children's narratives | Parent narrative referencing children | ~1,600 |
| Stage 3: Sections | Parent narratives + KPIs | 5 P&L section narratives | ~5 |
| Stage 4: Executive | Sections + risks + cross-BU themes | Headline + full narrative | ~1 |

### Cascade Regeneration

When any node changes (edit/approval), all dependent nodes auto-regenerate:
```
Edit leaf → parent → calculated rows → section → executive
Takes ~30 seconds (8-10 LLM calls for affected chain only)
Debounced: 60 seconds after last edit
```

---

## 6. 360-Degree Variance Intelligence

### Built (Phase 2)

| Dimension | What It Provides |
|---|---|
| Decomposition | Volume × Price × Mix × FX root cause drivers |
| Netting | Offsetting variances hidden at parent level |
| Trends | Consecutive period direction patterns |
| Correlations | Statistically related variance pairs |
| Carry-Forward | Prior period narrative as context |
| Seasonality | Expected monthly patterns |
| FX Framing | Currency impact narrative |
| RAG | Learning from approved narratives |

### Planned (Phase 3)

| # | Dimension | Example |
|---|---|---|
| 1 | **Materiality Context** | "This $200K is 0.3% of revenue but 8% of EBITDA" |
| 2 | **Risk Classification** | "FX-driven: uncontrollable. Hiring: controllable." |
| 3 | **Cumulative Projection** | "Full-year impact: $3.2M at current rate" |
| 4 | **Variance Persistence** | "Decaying — was -10.2% in May, now -8.7%" |
| 5 | **Cross-Dimensional Pivot** | "Not a cost center issue — 85% is EMEA geography" |
| 6 | **Peer Comparison** | "Tech costs over budget in ALL 5 BUs — enterprise-wide" |
| 7 | **Causal Chains** | "15-FTE shortfall → Advisory Fee decline (r=0.87)" |
| 8 | **Multi-Year Patterns** | "Same Q2 softness in 2024 and 2025, recovered Q3" |
| 9 | **Narrative Coherence** | Cross-narrative consistency validation |
| 10 | **Anomaly Detection** | "This magnitude never occurred in 36 months" |
| 11 | **Leading/Lagging** | "Comp moved 2 months before revenue — staffing signal" |
| 12 | **Budget Assumptions** | "Budget assumed 8% growth; actual 3%" |
| 13 | **Market Context** | "EUR weakened 4%. Insurance sector -2.3% in Q2" |
| 14 | **Waterfall Attribution** | Ordered additive bridge for charts |
| 15 | **Theme Clustering** | "APAC Revenue Weakness (12 variances, $2.1M)" |

### Peer Comparison (Detail Level, Not BU Aggregate)

| Level | When | Value |
|---|---|---|
| Same cost account across BUs | Always for shared categories | Enterprise-wide patterns |
| Same geo across BUs | Geographic variance detected | Regional macro factors |
| Same ratio across BUs | Margin/ratio variance | Structural shifts |
| Outlier within peer pattern | One BU deviates | BU-specific vs systemic |

Primary purpose: **"Is this mine (isolated) or ours (systemic)?"**

---

## 7. Variance Knowledge Graph

Foundation for all intelligence. Built at engine startup, queried during narrative generation.

### Node Types
Account, Dimension, Period, BusinessUnit, Variance, Narrative, Hypothesis, MarketContext

### Edge Types
parent_of, calc_depends_on, correlates_with, likely_causes, same_pattern_as, explained_by_dimension, leads/lags, peer_of, prior_period_of, section_member_of, approved_version_of, fx_impacted_by, derived_from (data lineage)

### Query API
- `get_full_context(variance_id)` → all 15 intelligence dimensions in one call
- `get_cascade_chain(account_id)` → what to regenerate
- `get_peer_pattern(account_id, period)` → systemic/isolated
- `get_causal_ancestors(account_id)` → root cause chain
- `estimate_cascade_cost(account_id)` → LLM calls + $

---

## 8. Engine Architecture

### Process A: Variance Analysis (Pure Math)
```
Pass 1:    Raw variance at all intersections
Pass 1.5:  Netting detection (6 checks)
Pass 2:    Threshold filter (OR logic)
Pass 2.1:  Materiality contextualization (NEW)
Pass 2.5:  Trend detection + multi-year patterns + persistence scoring
Pass 2.7:  Anomaly detection (NEW)
Pass 3:    Decomposition (Vol × Price × Mix × FX)
Pass 3.5:  Cross-dimensional pivot detection (NEW)
Pass 3.75: Peer comparison (NEW)
```
Triggers: new actuals, budget revision, threshold change. Runtime: ~15 seconds.

### Process B: Intelligence & Narratives (LLM or Template)
```
Pass 4:    Correlation + causal chains + leading/lagging
Pass 4.5:  Cumulative impact projection (NEW)
Pass 5:    Narrative generation (4 stages)
Pass 5.5:  Narrative coherence validation (NEW)
```
Triggers: manual from Admin, cascade from edit/approval. Runtime: ~3 min (template) or ~100 min (LLM) per period.

### Engine Control Panel (Admin)
- Select periods, process (A/B/both), stages, generation mode (LLM/template)
- Cost estimate before run
- Progress tracking with ETA
- Run history with cost
- Preview mode (5 samples)

---

## 9. Review Workflow

### Status Lifecycle
```
AI_DRAFT → ANALYST_REVIEWED → APPROVED (terminal)
         → ESCALATED → ANALYST_REVIEWED
         → DISMISSED → AI_DRAFT
```

### Features
- **Soft locking** — 30-min edit lock prevents concurrent edits
- **Version history** — append-only audit trail of every change
- **Edit intent** — why the analyst changed it (factual correction, added context, style, etc.)
- **Cascade regen** — edit triggers automatic parent/section/exec refresh
- **FY-scoped queue** — filter by fiscal year
- **Staleness indicators** — "Generated 2 hours ago, 3 children edited since"

### Trigger Locations
| Location | Button | What It Runs |
|---|---|---|
| Review item (parent) | "Regenerate Summary" | Cascade: affected parents + sections + exec |
| Approval item | "Refresh Section + Exec" | Sections + executive only |
| Exec Summary page | "Refresh" | Stage 3 + 4 |
| Admin → Engine | Full controls | Any combination |
| Auto (on edit) | Cascade trigger | Smart regen (debounced) |

---

## 10. Reports

All reports are **consumers of the narrative pyramid** — they pull pre-built content, not self-assembled.

| Format | Audience | Layers Used |
|---|---|---|
| **XLSX** | Analyst | Leaf detail + parent summary + section narratives tab |
| **PDF Flash** | CFO | Executive summary + sections + top 5 variances |
| **PPTX Deck** | Board | Headline + executive narrative + sections + risks |
| **DOCX Narrative** | Board | Full executive + section analysis + risks + recommendations |

---

## 11. Data Model

### Fact Tables
| Table | Rows | Purpose |
|---|---|---|
| fact_financials | ~49K | MTD actuals, budget, forecast, PY, FX |
| fact_variance_material | ~106K | Material variances with narratives (12 periods × 3 bases × 3 views) |
| fact_decomposition | ~65K | Vol/Price/Mix/FX components |
| fact_netting_flags | ~121 | Netting detection results |
| fact_trend_flags | ~116K | Trend detection results |
| fact_correlations | ~240 | Pairwise correlation pairs |
| fact_review_status | ~106K | Review workflow state |
| fact_section_narrative | 60 | Section-level narratives (5 × 12 periods) |
| fact_executive_summary | 12 | Period-level executive summaries |

### Dimension Tables
| Table | Purpose |
|---|---|
| dim_hierarchy | Parent-child trees (Geo, Segment, LOB, CostCenter) |
| dim_business_unit | 5 BUs |
| dim_account | 38 accounts (28 leaf + 10 calculated) |
| dim_period | 36 months with fiscal calendar |

### Auth Tables (PostgreSQL)
users, roles, user_roles, permissions, narrative_version_history

### Config (YAML)
thresholds.yaml, model_routing.yaml, seasonal_profiles.yaml, market_context.yaml, budget_assumptions.yaml, causal_graph.yaml, risk_classification.yaml

---

## 12. RAG Knowledge Base

- **Cross-period RAG:** Use approved narratives from OTHER periods as examples
- **Same-period, different account:** OK (style reference)
- **Same-period, same account:** NO (circular)
- **Retrieval:** 70% semantic + 15% account match + 15% magnitude proximity
- **Growing intelligence:** Each approval cycle improves future AI drafts

---

## 13. Cost Structure

| Scenario | Cost | Time |
|---|---|---|
| Template only (12 periods) | $0 | ~5 min |
| LLM latest period | ~$55 | ~100 min |
| LLM latest quarter (3) | ~$160 | ~5 hours |
| LLM all 12 months | ~$600 | ~20 hours |
| Cascade (1 edit) | ~$0.80 | ~30 sec |

---

## 14. Complete Roadmap

### Completed
- **MVP (Sprints 0-6):** Engine, 3 services, frontend, auth, reports, 947 tests
- **Phase 2 (2A-2H):** Narrative pyramid, carry-forward, seasonal, FX, exec page, workflow enhancement, report integration, 1,067 tests

### Phase 3: Intelligence Engine (~16 weeks)
| Sprint | What |
|---|---|
| 3A | Knowledge Graph + data lineage |
| 3B | Engine separation + stage independence |
| 3C | Cascade regeneration |
| 3D | Admin Engine Control + task queue |
| 3E | Hot-reload + period storage + Redis cache |
| 3F | Quick intelligence (materiality, risk, projection, persistence) |
| 3G | Core intelligence (pivot, peer, causal, multi-year, lead/lag, DBSCAN) |
| 3H | Quality + context (coherence, anomaly, budget validation, STL, market, LLM quality scoring) |
| 3I | Model routing + provider flexibility |

### Phase 4: Production Deployment (~8 weeks)
| Sprint | What |
|---|---|
| 4A | Databricks integration |
| 4B | CI/CD pipeline |
| 4C | Azure deployment + TLS/HTTPS + encryption |
| 4D | Observability (OpenTelemetry, Prometheus, Grafana) |
| 4E | Security hardening (token revocation, session management, WAF) |
| 4F | Data governance (DR, GDPR, retention, backup) |
| 4G | Load testing |

### Phase 5: ML Intelligence (~8 weeks)
| Sprint | What |
|---|---|
| 5A | XGBoost root cause ranking |
| 5B | Random Forest predictive variance |
| 5C | DBSCAN clustering enhancement |
| 5D | Isolation Forest anomaly enhancement |
| 5E | STL seasonal auto-detection |
| 5F | ML model governance |

### Phase 6: Extended Platform (~12 weeks)
| Sprint | What |
|---|---|
| 6A-C | Balance Sheet, Headcount, KPI agents |
| 6D-E | Teams integration, Excel add-in |
| 6F-G | Multi-entity, multi-step approval chains |
| 6H-L | Collaborative comments, external API, global search, SSO, onboarding, mobile |
