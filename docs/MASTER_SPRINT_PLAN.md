# Master Sprint Plan — FP&A Variance Analysis Agent

**Version:** 1.1 | **Last Updated:** 2026-03-28 | **Phase:** MVP (Weeks 1–12)

---

## Overview

This document is the single source of truth for sprint planning, deliverable tracking, and build order across the entire MVP. Each sprint includes build plans, acceptance criteria, testing requirements, and dependencies.

**Architecture:** 3 microservices + React frontend + shared library + Docker Compose
**Data Model:** 15 tables (6 dim + 1 base fact + 5 computed + 1 workflow + 1 knowledge + 1 audit)
**Engine:** 5.5-pass materiality-first computation pipeline

---

## Sprint 0 — Foundation

**Goal:** Project infrastructure, synthetic data, and computation engine.
**Duration:** Week 1–2

### Deliverable 0.3: Project Scaffolding [COMPLETE]
- [x] Directory structure per spec (services/, shared/, frontend/, tests/, infra/, docs/)
- [x] Shared library — Pydantic models (15 tables), enums, hierarchy utilities, config, formatters
- [x] Gateway service skeleton — 7 API routers, agents, prompts, notifications
- [x] Computation service skeleton — 5 API routers, 7 engine passes, decomposition, detection
- [x] Reports service skeleton — 3 API routers, 4 generators, scheduler
- [x] React app shell — Vite + React 18 + TypeScript + Tailwind, 7 views with routing, theme toggle
- [x] Docker Compose — 6 services (3 Python + frontend + Redis + Nginx) with dev overrides
- [x] Test framework — pytest with conftest, unit tests for hierarchy/models/formatting
- [x] Documentation structure — Sprint plan, testing framework, API ref, architecture
- [x] Config files — pyproject.toml, .gitignore, .env.example, .dockerignore

### Deliverable 0.1: Synthetic Data Generator [COMPLETE]

**Location:** `shared/data/synthetic.py` + `scripts/generate_synthetic_data.py`
**Output:** 15 tables as Parquet + CSV in `data/output/`

#### Build Plan

**Phase A — Dimension Tables (no dependencies):**
1. `dim_hierarchy` — Flatten all 4 hierarchy trees (Geo 26 nodes, Segment 13 nodes, LOB 13 nodes, CostCenter 20 nodes) into parent-child rows with materialized rollup_path
2. `dim_business_unit` — 5 BUs (Marsh, Mercer, Guy Carpenter, Oliver Wyman, MMC Corporate)
3. `dim_account` — 36 account nodes (28 detail + 8 calculated rows) with calc formulas, variance signs, P&L categories, dependency ordering
4. `dim_period` — 36 months (2024-01 to 2026-12) with fiscal year/quarter/month, is_closed, is_current
5. `dim_view` — 3 rows (MTD, QTD, YTD)
6. `dim_comparison_base` — 3 rows (Budget, Forecast, Prior Year)

**Phase B — Base Fact Table (depends on Phase A):**
7. `fact_financials` — MTD atomic grain at leaf-level intersections:
   - Revenue: BU-specific profiles × geo distribution × seasonality × growth × volatility noise
   - Costs: Revenue-proportional with per-category ratios × volatility
   - Budget: Same structure with tighter noise (95% accuracy)
   - Forecast: Actuals with even tighter noise (98% accuracy) for closed periods
   - Prior Year: 12-month shift of previous year actuals
   - FX: Local currency amounts + budget/actual rates per geo-currency mapping
   - Scenario injections: 4 deliberate variance scenarios
   - Estimated rows: ~50,000–100,000 depending on dimension pruning

**Phase C — Empty Schema Tables:**
8–15. fact_variance_material, fact_decomposition, fact_netting_flags, fact_trend_flags, fact_correlations, fact_review_status, knowledge_commentary_history, audit_log — Create empty DataFrames with correct column schemas

**Validation:**
- Rollup consistency: leaf sum = parent for every hierarchy path
- No nulls in required fields
- Calculated row formulas balance (Gross Profit = Revenue - COR, etc.)
- Budget/actual ratio within expected volatility band
- All 4 scenario injections visible in output
- Parquet + CSV parity check

#### Acceptance Criteria
- [x] All 15 tables generated successfully (80 hierarchy nodes, 38 accounts, 82,080 fact rows)
- [x] Parquet + CSV output in `data/output/` (30 files total)
- [x] Validation passes with zero errors
- [x] Reproducible with seed=42 (deterministic output verified)
- [x] `python scripts/generate_synthetic_data.py` runs end-to-end (<1s)
- [x] 135 tests passing (105 unit + 30 integration)

#### Testing
- Unit: Dimension table generation, hierarchy flattening, rollup path correctness
- Integration: Full generation pipeline, validation suite
- Data quality: Statistical checks on distribution, seasonality patterns

### Deliverable 0.2: Computation Engine [COMPLETE]

**Location:** `services/computation/engine/`
**Input:** Synthetic data from `data/output/`
**Output:** Populated computed tables (fact_variance_material, etc.)

#### Build Plan

**Pass 1 — Raw Variance:**
- All Account × Dimension × Period × Base × View
- MTD variance = actual − comparator
- QTD/YTD by summing MTDs
- Bottom-up rollup via depth-sorted hierarchy
- Calculated rows resolved AFTER rollup in dependency order
- Edge cases: budget=0, missing PY, negative budget, new account

**Pass 1.5 — Netting Detection:**
- Check 1: Gross offset (gross > 3× net)
- Check 2: Dispersion (child std dev > 10pp)
- Check 3: Directional split (children in opposing directions)
- Check 4: Cross-account (same dimension, different accounts)

**Pass 2 — Threshold Filter:**
- OR logic: abs_threshold OR pct_threshold
- Resolution: close_week > role > account > domain > global
- Three types advance: material, netted, trending

**Pass 2.5 — Trend Detection:**
- Rule 1: Consecutive direction (3+ periods same sign)
- Rule 2: Cumulative YTD breach

**Pass 3 — Decomposition:**
- Revenue: Volume × Price × Mix × FX
- COGS: Rate × Volume × Mix
- OpEx: Rate × Volume × Timing × One-time
- Fallback methods when unit data unavailable

**Pass 4 — Correlation & Root Cause:**
- Pairwise scan of material variances
- Top pairs batched for LLM hypothesis generation
- Placeholder for MVP (no LLM in Sprint 0)

**Pass 5 — Narrative Generation:**
- Placeholder for MVP (requires LLM integration in Sprint 1)
- Generate empty narrative shells with metadata

#### Acceptance Criteria
- [x] Full pipeline runs on synthetic data in <10 seconds (budget: 5 min)
- [x] 300,237 total variances computed → 4,422 material variances
- [x] 11 netting flags detected (gross offset, dispersion, directional split, cross-account)
- [x] 9,695 trend flags detected (consecutive direction + cumulative YTD breach)
- [x] 2,622 decompositions produced (revenue/COGS/OpEx)
- [x] 20 pairwise correlations found
- [x] 4,422 template narratives generated with review status (AI_DRAFT)
- [x] Calculated rows (EBITDA, Gross Profit, etc.) resolve correctly in dependency order
- [x] 193 tests passing (141 prior + 52 new engine tests)

---

## Sprint 1 — Revenue Vertical Slice [IN PROGRESS]

**Goal:** Revenue variance end-to-end with chat, dashboard, and review workflow.
**Duration:** Week 3–4
**Dependencies:** Sprint 0 complete (193 tests, 300K variances, 4,422 material)

### Key Decisions
- **LLM:** Template/keyword-based first → LiteLLM wired as late enhancement (SD-14)
- **Database:** PostgreSQL via docker-compose for review/approval persistence
- **Build cadence:** 3 checkpoints with commit/push at each

### Sub-Deliverables (Build Order)

#### Checkpoint 1: Backend APIs + Database (SD 1–5)

**SD-1: PostgreSQL + Database Layer**
- SQLAlchemy async engine + ORM models (ReviewStatus, AuditLog, Conversation, ChatMessage)
- Seed review_status from fact_review_status.parquet on first boot
- PostgreSQL 16 in docker-compose
- Files: `shared/database/{engine,models,seed}.py`, `infra/docker-compose.yml`

**SD-2: Data Access Service**
- Singleton wrapping DataLoader + HierarchyCache with typed query methods
- Methods: get_summary_cards, get_waterfall, get_heatmap, get_trends, get_variance_list, get_variance_detail, get_pl_statement
- File: `shared/data/service.py`

**SD-3: Computation Service Endpoints (8 endpoints)**
- Dashboard: summary, waterfall, heatmap, trends
- Variances: list, detail, by-account
- P&L: statement, account detail
- Drilldown: drill, decomposition, netting, correlations
- Files: `services/computation/api/{dashboard,variances,pl,drilldown}.py`

**SD-4: Gateway Dimension + Review + Approval Endpoints**
- Dimensions: hierarchies, BUs, accounts, periods
- Review: queue (with RBAC), actions (status transitions), stats
- Approval: queue (ANALYST_REVIEWED filter), bulk actions, stats
- Files: `services/gateway/api/{dimensions,review,approval}.py`, `shared/data/review_store.py`

**SD-5: SSE Streaming Infrastructure**
- StreamingContext (asyncio.Queue), typed SSE event models, ConversationManager
- Chat endpoints: POST message → agent, GET stream → SSE
- Files: `services/gateway/streaming/{events,context,manager}.py`, `services/gateway/api/chat.py`

**📦 CP-1: ~50 new tests, all backend APIs functional**

#### Checkpoint 2: Agents + Frontend (SD 6–13)

**SD-6: Agent Implementation (Template-First)**
- KeywordIntentClassifier: regex patterns for revenue, P&L, waterfall, etc.
- ToolExecutor: maps tool names → httpx calls to computation service
- Response templates with `{variable}` placeholders for real data
- OrchestratorAgent.handle_message(): classify → route → execute → stream
- PLAgent + RevenueAgent: generate_response() with template interpolation
- Files: `services/gateway/agents/{intent,tools,templates,orchestrator,domain_agents}.py`

**SD-7: Frontend Shared Components (17 components)**
- Charts: WaterfallChart, HeatmapGrid, TrendChart (Recharts)
- Cards: SummaryCard
- Tables: DataTable (generic sortable/paginated), ExpandableRow
- Chat: ChatMessage, ChatInput, SSEStreamDisplay
- Narrative: NarrativePanel, NarrativeEditor
- P&L: PLTable, PLRow
- Review: ReviewTable, ReviewDetailPanel
- Approval: ApprovalTable, BulkApprovalBar

**SD-8: Frontend Hooks (7 hooks)**
- useDashboard, useVariances, useReviewQueue, useSSE (modify stubs)
- useApproval, usePLStatement, useChat (new)

**SD-9–13: Frontend Views**
- DashboardView: filter bar + summary cards + waterfall + heatmap + trends
- ChatView: conversation sidebar + message list + input + SSE streaming
- PLView: recursive PLTable + NarrativePanel + CFO preview toggle
- ReviewView: stats bar + ReviewTable + ReviewDetailPanel + NarrativeEditor
- ApprovalView: stats bar + ApprovalTable + BulkApprovalBar

**📦 CP-2: Full UI functional, ~25 new tests**

#### Checkpoint 3: LLM Enhancement + E2E (SD 14–15)

**SD-14: LiteLLM Integration**
- LLMIntentClassifier (LiteLLM function calling) alongside keyword classifier
- LLM narrative generation using system prompts from YAML
- Config toggle: `use_llm_agents: bool`

**SD-15: E2E Testing**
- Full flow: chat → agent → computation → SSE → review → approval
- Both services + DB, end-to-end verification

**📦 CP-3: Sprint 1 complete**

### Shared Components Centralized

| Component | Location | Used By |
|-----------|----------|---------|
| DataService | `shared/data/service.py` | Computation API, Gateway API |
| ReviewStore | `shared/data/review_store.py` | Gateway review/approval |
| Database engine | `shared/database/engine.py` | Gateway service |
| SSE events | `services/gateway/streaming/events.py` | Chat, agents, frontend |
| DataTable | `frontend/src/components/tables/DataTable.tsx` | All list views |
| SummaryCard | `frontend/src/components/cards/SummaryCard.tsx` | Dashboard, stats bars |

### Testing Plan

| Checkpoint | New Unit | New Integration | New E2E | Running Total |
|-----------|---------|----------------|---------|---------------|
| CP-1 | ~50 | ~4 | — | ~247 |
| CP-2 | ~25 | ~3 | — | ~275 |
| CP-3 | ~4 | — | ~1 | ~280 |

### Acceptance Criteria
- [ ] User asks "How did revenue perform?" → gets streamed answer with real data
- [ ] Dashboard shows revenue waterfall, heatmap, trend with computed data
- [ ] P&L view shows revenue hierarchy with expand/collapse and narratives
- [ ] Analyst sees AI_DRAFT variances in review queue, can review/edit/approve
- [ ] Director sees ANALYST_REVIEWED in approval queue, can bulk approve
- [ ] Review/approval state persists in PostgreSQL across restarts
- [ ] All tests pass (target: ~280)

---

## Sprint 2 — Full P&L + Workflow [IN PROGRESS]

**Goal:** Wire real engine data to dashboard alerts, complete review workflow with persistence, add PostgreSQL durability.
**Duration:** Week 5–6
**Dependencies:** Sprint 1 complete (527 tests, 120+ components, real data flowing)

### Build Plan (3 Checkpoints)

#### CP-1: Wire Real Data to Existing UI [IN PROGRESS]
- **D1: Netting/Trend Alert API** — Add `get_netting_alerts()` + `get_trend_alerts()` to DataService, expose via 2 new dashboard endpoints, wire to AlertCards on frontend
- **D4: Modal Decomposition** — Fetch `/drilldown/decomposition/{id}` when modal opens, transform components for display
- Tests: 13 new tests (6 alert service + 4 alert API + 3 drilldown)

#### CP-2: Complete Workflow Actions [IN PROGRESS]
- **D2: NarrativeEditor Persistence** — POST edited narrative to `/review/actions`, extract shared `useReviewAction` hook
- **D5: Hypothesis Feedback** — POST ✓/✗ feedback to `/review/actions`
- **Bug fix:** `useReviewQueue` sends 'confirm' (invalid) → fix to 'approve'
- **Bug fix:** `review_store.py` accepts hypothesis_feedback but never stores it
- Tests: 3 new review action tests

#### CP-3: PostgreSQL Persistence [IN PROGRESS]
- **D3: Database Integration** — Init PostgreSQL in gateway lifespan, create `AsyncReviewStore` (dual-write: DataFrame + PostgreSQL), await store methods in review/approval endpoints, seed on startup, graceful fallback if DB unavailable
- Tests: 5 new async store tests

### Acceptance Criteria
- [ ] Dashboard netting alerts from real engine data (not hardcoded)
- [ ] Dashboard trend alerts from real engine data
- [ ] Modal decomposition from drilldown API
- [ ] Narrative edit → POST → persisted
- [ ] Hypothesis feedback → POST → persisted
- [ ] Review/approval state persists in PostgreSQL
- [ ] Graceful fallback when PostgreSQL unavailable
- [ ] All tests pass (target: 550+)

---

## Sprint 3 — Narratives + Learning

**Goal:** RAG pipeline, 4-level persona-aware narratives, synthesis.
**Duration:** Week 7–8

### Deliverables

1. **LLM Integration (LiteLLM)**
   - Pass 4: Batched hypothesis generation
   - Pass 5: Multi-level narrative generation
   - Model routing per task

2. **RAG Pipeline**
   - Embedding generation for variance context
   - Vector store (Qdrant) setup
   - Similarity search (70% semantic + 15% account + 15% magnitude)
   - Few-shot example injection into prompts

3. **4-Level Narratives**
   - Detail (analyst, 3–5 sentences)
   - Midlevel (BU leader, 2–3 sentences)
   - Summary (CFO, 1–2 sentences)
   - Oneliner (dashboard)
   - Board (on-demand)

4. **Bottom-Up Synthesis**
   - Triggered by analyst approval
   - Cascade upward through hierarchy
   - Parent midlevel + summary from child commentaries

5. **Knowledge Base**
   - Auto-populate from review workflow
   - Approved commentaries stored with embeddings
   - Hypothesis feedback loop

### Acceptance Criteria
- [ ] AI-generated narratives for material variances
- [ ] RAG retrieval returns relevant prior commentaries
- [ ] Synthesis produces parent-level narratives from children
- [ ] CFO gets summary-level, analyst gets detail-level
- [ ] Knowledge base grows with each approval cycle

---

## Sprint 4 — Reports + Notifications

**Goal:** Excel/PDF export, Teams/Slack notifications, scheduling.
**Duration:** Week 9–10

### Deliverables

1. **Excel Export**
   - Formatted .xlsx with narratives
   - P&L structure preserved
   - Variance color coding
   - Drill-down tabs per BU

2. **PDF Report**
   - Period-end formatted report
   - Executive summary + detailed sections
   - Charts embedded as images

3. **Notifications**
   - Teams adaptive cards (engine complete, review needed)
   - Slack Block Kit messages
   - Email (SMTP) for approvals and SLA warnings

4. **Report Scheduling**
   - Cron-based scheduling
   - Distribution list management
   - Report gate: only APPROVED variances distributed

### Acceptance Criteria
- [ ] Excel export opens in Excel with correct formatting
- [ ] PDF renders with charts and narratives
- [ ] Teams notification fires on engine completion
- [ ] Scheduled reports auto-generate and distribute

---

## Sprint 5 — Auth + RBAC + Polish

**Goal:** Azure AD, persona-narrative filtering, theme, admin.
**Duration:** Week 11

### Deliverables

1. **Azure AD Integration**
   - OAuth 2.0 flow
   - JWT token validation
   - User profile extraction

2. **RBAC + Persona-Narrative Filtering**
   - BU Leaders: own BU only, REVIEWED/APPROVED
   - CFO: APPROVED only, summary level
   - HR Finance: HC domain only
   - Board Viewer: Board + Summary only

3. **Dark/Light Theme**
   - Tailwind semantic tokens
   - User toggle persisted
   - All components themed

4. **Admin View**
   - Threshold configuration
   - Model routing config
   - User role management
   - Audit log viewer

### Acceptance Criteria
- [ ] Login with Azure AD works
- [ ] BU Leader cannot see other BU data
- [ ] CFO sees only approved summaries
- [ ] Theme toggle works across all views
- [ ] Admin can adjust thresholds

---

## Sprint 6 — Testing + Hardening

**Goal:** Full test suite, performance, edge cases, UAT prep.
**Duration:** Week 12

### Deliverables

1. **Comprehensive Test Suite**
   - Unit tests: >80% coverage on shared + engine
   - Integration tests: Full pipeline, service-to-service
   - E2E tests: Key user journeys (Cypress/Playwright)
   - Performance tests: Engine <5min, API <100ms p95

2. **Edge Case Validation**
   - Budget=0 handling
   - Missing PY periods
   - New accounts (no history)
   - Empty hierarchy nodes
   - Missing FX rates
   - Negative budgets

3. **Documentation Finalization**
   - API reference (all 50 endpoints)
   - Architecture decision records
   - Deployment guide
   - User guide

4. **UAT Preparation**
   - Test data refresh
   - UAT environment setup
   - Test scripts for each persona

---

## Phase 2 Preview (Weeks 13–24)

- BS, HC, KPI agents
- Databricks SQL fallback
- Netting checks 5–6, Trend rules 3–4
- PPTX templates, Excel add-in
- Isolation Forest, linear regression, STL seasonality
- Teams @mention agent integration

---

## Key Dependencies

| Sprint | Depends On |
|--------|-----------|
| Sprint 1 | Sprint 0 (data + engine) |
| Sprint 2 | Sprint 1 (revenue vertical) |
| Sprint 3 | Sprint 2 (full P&L + workflow) |
| Sprint 4 | Sprint 3 (narratives exist to export) |
| Sprint 5 | Sprint 1+ (UI exists to protect) |
| Sprint 6 | All sprints (integration testing) |

---

## Risk Register

| Risk | Impact | Mitigation |
|------|--------|-----------|
| LLM latency in Pass 4/5 | Engine >5min | Async batching, concurrent calls, fast model for oneliners |
| Ragged hierarchy edge cases | Incorrect rollup | Extensive unit tests, validation suite |
| FX decomposition complexity | Inaccurate splits | Fallback methods, manual override flag |
| RAG quality cold start | Poor early narratives | Seed knowledge base with template commentaries |
| Azure AD integration | Auth delays | Mock auth for development, real auth late sprint |
