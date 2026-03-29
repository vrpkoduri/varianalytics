# FP&A Variance Analysis Agent

## Project Overview

An AI-powered, model-agnostic agentic platform for automated variance detection, root cause analysis, and financial narrative generation. Standalone React + FastAPI web app on Azure/Databricks.

**Specs & Docs in `/docs/`:**
- `FPA_Master_Spec_v1.docx` — Single source of truth: product spec + solution design + workflow + commentary learning (supersedes all prior docs)
- `synthetic-data-spec.json` — Dimension hierarchies and data generation rules
- `MASTER_SPRINT_PLAN.md` — Sprint-by-sprint build plan with acceptance criteria
- `TESTING_FRAMEWORK.md` — Test strategy, tools, conventions
- `API_REFERENCE.md` — All 50 endpoints documented
- `ARCHITECTURE.md` — Architecture decision records, data flow, system overview

## Current Sprint: Sprint 0 — Foundation

### Deliverables (in order):
1. **Synthetic Data Generator** — 36 months of P&L data across 5 ragged-hierarchy dimensions. Output: all 15 tables as parquet/CSV.
2. **Computation Engine** — 5.5-pass materiality-first engine. Runs on synthetic data, produces enriched tables.
3. **Project Scaffolding** — Microservice skeletons, React app shell, docker-compose.

### Sprint 1 (next):
Vertical slice: Revenue variance end-to-end with chat + dashboard + review workflow.

## Architecture

### Microservices (3 services, 50 endpoints)
- **Service 1: Gateway + Chat** (8000) — Auth, chat SSE, dimensions, config, review/approval, notifications
- **Service 2: Computation** (8001) — 5.5-pass engine, dashboard, variances, drill-down, synthesis, P&L
- **Service 3: Reports** (8002) — PDF/PPTX/DOCX/XLSX, scheduling, distribution

### Tech Stack
- **Frontend:** React 18+ (TypeScript) + Tailwind CSS + shadcn/ui + Recharts + D3.js
- **Backend:** FastAPI (Python 3.11+)
- **LLM:** LiteLLM (model-agnostic)
- **Data (MVP):** pandas DataFrames + synthetic data
- **Data (Prod):** Databricks (Unity Catalog, Delta Lake, SQL Serverless)
- **Vector Store:** Databricks Vector Search / Qdrant
- **Cache:** Redis
- **Auth:** Azure AD (Entra ID) + OAuth 2.0
- **Hosting:** Azure Container Apps

### Project Structure
```
variance-agent/
├── services/
│   ├── gateway/           # Service 1
│   │   ├── api/           # auth, chat, dimensions, config, review, approval
│   │   ├── agents/        # Orchestrator + domain agents
│   │   ├── prompts/       # System prompts, tool defs (YAML)
│   │   └── notifications/ # Teams/Slack webhooks, SMTP
│   ├── computation/       # Service 2
│   │   ├── api/           # dashboard, variances, drilldown, P&L
│   │   ├── engine/        # 5.5-pass computation
│   │   ├── decomposition/ # Vol/Price/Mix, Rate/Vol/Timing
│   │   ├── detection/     # Netting + trend detection
│   │   └── synthesis/     # Narrative synthesis (review-triggered)
│   └── reports/           # Service 3
│       ├── api/
│       ├── generators/    # PDF, PPTX, DOCX, XLSX
│       └── scheduler/
├── shared/
│   ├── data/              # synthetic.py, databricks.py, cache.py
│   ├── models/            # Pydantic schemas
│   ├── hierarchy/         # Rollup, traversal utilities
│   ├── knowledge/         # RAG retrieval, embedding, vector search
│   └── config/            # Thresholds YAML, model routing YAML
├── frontend/src/
│   ├── components/        # StatusBadge, NarrativeEditor, ExportMenu
│   ├── views/             # Dashboard, PL, Chat, Review, Approval, Reports, Admin
│   ├── hooks/             # useVariances, useDashboard, useSSE, useReviewQueue
│   ├── context/           # GlobalFilters, UserContext, ReviewStats
│   └── utils/             # Formatters, theme, persona helpers
├── infra/                 # docker-compose, Azure Bicep
└── docs/                  # Master spec, synthetic-data-spec.json
```

## Key Design Decisions

### Data Model (15 tables)
- **Dimensions (6):** dim_hierarchy (parent-child Geo/Segment/LOB/CC), dim_business_unit (flat), dim_account (parent-child + calculated rows + template overlay), dim_period, dim_view (MTD/QTD/YTD), dim_comparison_base (Budget/Forecast/PY)
- **Base Fact (1):** fact_financials — MTD atomic grain with actual/budget/forecast/PY + FX columns
- **Computed (5):** fact_variance_material (5-level narratives + synthesis tracking), fact_decomposition, fact_netting_flags, fact_trend_flags, fact_correlations
- **Workflow (1):** fact_review_status — AI_DRAFT → ANALYST_REVIEWED → APPROVED + edits + hypothesis feedback
- **Knowledge (1):** knowledge_commentary_history — approved commentaries + vector embeddings for RAG
- **Audit (1):** audit_log — every engine run, LLM call, review action, data access

### Computation Engine (5.5-pass materiality-first)
1. **Pass 1:** Raw variance at ALL intersections. Calculated rows (EBITDA etc.) resolved in dependency order AFTER rollup.
2. **Pass 1.5:** Netting detection — 6 checks (MVP: 1-4). Summary nodes below threshold.
3. **Pass 2:** Threshold filter — OR logic. Three types: material, netted, trending.
4. **Pass 2.5:** Trend detection — 4 rules (MVP: 1-2).
5. **Pass 3:** Decomposition — Revenue: Vol×Price×Mix×FX; COGS: Rate×Vol×Mix; OpEx: Rate×Vol×Timing×Onetime. Fallback methods when unit data unavailable.
6. **Pass 4:** Correlation + root cause — pairwise scan, batched LLM hypotheses.
7. **Pass 5:** RAG-enhanced multi-level narrative generation (4 levels: detail/midlevel/summary/oneliner + board on-demand). Creates fact_review_status (AI_DRAFT). Logs to audit_log.
8. **Post:** Notifications (Teams/Slack).
9. **Synthesis:** OUTSIDE engine — triggered by analyst approval. Bottom-up child commentary aggregation.

### Edge Cases (handle gracefully)
- Budget=0 → pct=NULL, flagged "unbudgeted"
- Missing PY → skip vs PY comparison
- New account → skip trend, flag "New"
- Empty hierarchy node → $0 contribution
- Missing FX → skip FX decomposition
- Negative budget → sign convention applies, agent notes

### Comparison Matrix (9 views)
- 3 bases × 3 aggregations. Base fact stores MTD only. QTD/YTD computed by engine.

### Ragged Hierarchies
- Parent-child with materialized rollup_path. App cache at startup (~20MB). No recursive CTEs at runtime.

### Agent Design (LLM-thin)
- LLM: intent + NL generation. Code: computation, routing, data, thresholds.
- 10 tools mapped to Service 2 APIs. Never sees raw bulk data.
- SSE streaming with typed events (token, data_table, mini_chart, suggestion, confidence, netting_alert, review_status, done).
- Review-status-aware: BU Leaders see REVIEWED/APPROVED only. CFO sees APPROVED only. Analysts see all.
- Persona-aware: adapts narrative depth to viewer role.

### Commentary Learning (MVP)
- **RAG few-shot:** Retrieve 2-3 similar approved commentaries as examples (70% semantic + 15% account + 15% magnitude).
- **Knowledge base:** Auto-populated from review workflow. Vector embeddings for retrieval.
- **4-level narratives:** detail (analyst), midlevel (BU leader), summary (CFO), board (on-demand).
- **Bottom-up synthesis:** Analyst approves detail → parent summary auto-synthesized from children.
- **Hypothesis feedback:** Thumbs up/down → enriches RAG (MVP), trains XGBoost (Phase 2).

### Workflow (Full in MVP)
- **Status:** AI_DRAFT → ANALYST_REVIEWED → APPROVED (+ ESCALATED, DISMISSED, AUTO_CLOSED).
- **Review Queue:** Analyst landing page. Sort by impact, SLA indicators, batch actions.
- **Approval Queue:** Director bulk approve. Report gate (only APPROVED distributed).
- **NarrativeEditor:** Edit + diff + hypothesis feedback.
- **Notifications:** Teams/Slack for alerts, review needed, approval needed, SLA warnings.
- **Exports:** Excel (.xlsx), PowerPoint (.pptx from template), PDF.

### Persona-RBAC Integration
- BU Leaders: detail only within own BU. Cross-BU blocked.
- HR Finance: detail only in HC domain.
- Board Viewer: Board + Summary only.
- All others: full access within role scope.

### Theme
- Dark + Light with user toggle. Tailwind semantic tokens.

### ML Phasing
- **MVP: Zero ML.** Deterministic + LLM.
- **Phase 2:** Isolation Forest, linear regression, STL seasonality.
- **Phase 3:** XGBoost root cause ranking, Random Forest predictive, DBSCAN clustering.

## Coding Conventions

### Python
- 3.11+, type hints, Pydantic, async/await, docstrings, pytest, Black + isort
- No LangChain. Direct LiteLLM SDK.

### TypeScript
- React 18+ functional + hooks, strict mode, Tailwind, shadcn/ui
- Context + useReducer (no Redux), custom hooks, Recharts + D3.js

### General
- Config in YAML (thresholds, model routing)
- Environment variables for secrets
- Docker-compose for local dev
- Conventional commits

# CLAUDE.md — Design Addendum

## Add this section to your existing CLAUDE.md:

---

## Design Reference (Sprint 1+)

The UI has been fully prototyped and spec'd. These 4 files are the design source of truth:

| File | What | Size |
|------|------|------|
| `docs/FPA_Variance_Agent_UI.html` | **Working prototype** — open in browser as pixel-perfect visual target | 136KB |
| `docs/VANTAGE_DESIGN_SPEC.md` | **Design specification** — every color, spacing, animation, interaction, tooltip | 557 lines |
| `docs/design-tokens.ts` | **Design tokens** — copy to `frontend/src/theme/tokens.ts` | TypeScript |
| `docs/COMPONENT_INVENTORY.md` | **Component map** — prototype functions → React components + state mapping | 200 lines |

### Design Rules (non-negotiable)
1. **Color split**: Cobalt (#002C77) + Teal (#00A8C7) for chrome. Gold/Emerald/Coral/Amber/Purple for data semantics only. Never cross.
2. **Typography**: Playfair Display for numbers and titles. DM Sans for everything else.
3. **Glassmorphism**: Every card uses `backdrop-filter: blur(16px)` + translucent background + teal border glow on hover.
4. **Persona-first**: All data passes through persona RBAC filter before rendering. CFO sees approved only. BU Leader sees own BU only.
5. **Gradient stripe**: 2px cobalt→teal gradient at top of every card.
6. **Animation**: fadeUp entrance (0.45s, 50ms stagger), crossfade tab transitions (150ms), counter animations on KPIs, decomposition bar cascade.

### Build Order (Frontend)
1. Theme + tokens + global styles (background, glassmorphism, typography)
2. Header (two-tier) + Sidebar (donut, trees)
3. Dashboard (KPIs, charts, heatmap, variance table)
4. Modal (the detail panel — used from every page)
5. P&L (recursive grid + margin gauges)
6. Chat (SSE streaming + typing indicator)
7. Review Queue (sortable, searchable, persona-filtered + hypothesis feedback)
8. Approvals (report gate + analyst groups)
9. Reports (3 sub-tabs + 3 report preview templates)
10. Polish (transitions, confetti, tooltips, print CSS)

