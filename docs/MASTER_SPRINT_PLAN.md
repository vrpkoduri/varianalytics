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

## Sprint 1 — Revenue Vertical Slice

**Goal:** Revenue variance end-to-end with chat, dashboard, and review workflow.
**Duration:** Week 3–4
**Dependencies:** Sprint 0 complete

### Deliverables

1. **Revenue Agent (Gateway)**
   - Chat intent classification for revenue queries
   - Tool calls to Computation Service
   - SSE streaming response
   - Review-status-aware responses

2. **Dashboard — Revenue Focus**
   - SummaryCards: Revenue, EBITDA
   - Waterfall chart: Revenue vs Budget by BU
   - Heatmap: Geo × BU variance intensity
   - Trend line: Revenue by month

3. **P&L Deep Dive — Revenue**
   - Recursive PLTable for Revenue section
   - Ragged hierarchy expand/collapse
   - Narrative detail panel
   - "Preview as CFO" button

4. **Chat Interface**
   - Message input + SSE streaming display
   - Context inference (current filters)
   - Conversation history
   - Typed SSE events (token, data_table, suggestion)

5. **Review Queue**
   - StatusBar with counts
   - ReviewTable with sorting + SLA indicators
   - ReviewDetailPanel stub
   - NarrativeEditor stub (view mode)

6. **Approval Queue**
   - Pending grouped by analyst
   - Bulk approve action
   - Report gate enforcement

### Acceptance Criteria
- [ ] User can ask "How did revenue perform?" and get a streamed answer
- [ ] Dashboard shows revenue waterfall with real computed data
- [ ] P&L view shows revenue hierarchy with expand/collapse
- [ ] Analyst can see AI_DRAFT variances in review queue
- [ ] Director can approve reviewed variances

---

## Sprint 2 — Full P&L + Workflow

**Goal:** All P&L account types, decomposition, netting, NarrativeEditor.
**Duration:** Week 5–6

### Deliverables

1. **Full P&L Engine**
   - COGS decomposition (Rate × Volume × Mix)
   - OpEx decomposition (Rate × Volume × Timing × One-time)
   - Non-Operating items
   - All calculated rows (EBITDA, Gross Profit, Operating Income, etc.)

2. **Netting Detection (MVP Checks 1–4)**
   - Gross offset check
   - Dispersion check
   - Directional split check
   - Cross-account check
   - Alert banners in dashboard

3. **Trend Detection (MVP Rules 1–2)**
   - Consecutive direction rule
   - Cumulative YTD breach rule
   - Trend indicators in P&L view

4. **NarrativeEditor**
   - Edit mode with rich text
   - Diff view (AI original vs analyst edit)
   - Hypothesis feedback (thumbs up/down)
   - Save + submit for approval

5. **P&L View — Full**
   - All account categories
   - Calculated row styling
   - Drill-down to decomposition
   - Netting/trend indicators

### Acceptance Criteria
- [ ] Full P&L renders with all 36 account nodes
- [ ] Decomposition available for Revenue, COGS, OpEx
- [ ] Netting detected for APAC offset scenario
- [ ] Trend detected for technology cost creep
- [ ] Analyst can edit narrative and submit for review

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
