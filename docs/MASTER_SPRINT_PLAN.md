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

## Sprint 2 — Full P&L + Workflow [COMPLETE]

**Goal:** Wire real engine data to dashboard alerts, complete review workflow with persistence, add PostgreSQL durability.
**Duration:** Week 5–6
**Dependencies:** Sprint 1 complete (527 tests, 120+ components, real data flowing)

### Build Plan (3 Checkpoints)

#### CP-1: Wire Real Data to Existing UI [COMPLETE]
- **D1: Netting/Trend Alert API** — Add `get_netting_alerts()` + `get_trend_alerts()` to DataService, expose via 2 new dashboard endpoints, wire to AlertCards on frontend
- **D4: Modal Decomposition** — Fetch `/drilldown/decomposition/{id}` when modal opens, transform components for display
- Tests: 13 new tests (6 alert service + 4 alert API + 3 drilldown)

#### CP-2: Complete Workflow Actions [COMPLETE]
- **D2: NarrativeEditor Persistence** — POST edited narrative to `/review/actions`, extract shared `useReviewAction` hook
- **D5: Hypothesis Feedback** — POST ✓/✗ feedback to `/review/actions`
- **Bug fix:** `useReviewQueue` sends 'confirm' (invalid) → fix to 'approve'
- **Bug fix:** `review_store.py` accepts hypothesis_feedback but never stores it
- Tests: 3 new review action tests

#### CP-3: PostgreSQL Persistence [COMPLETE]
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

## Sprint 3 — Narratives + Learning [PLANNED]

**Goal:** RAG pipeline, LLM-enhanced narratives, synthesis, knowledge base.
**Duration:** Week 7–8
**Dependencies:** Sprint 2 complete (593 tests, LLMClient ready, API key configured)

### Build Plan (3 Checkpoints)

#### CP-1: RAG Infrastructure
- EmbeddingService (LiteLLM → 1536-dim vectors)
- VectorStore (Qdrant MVP + InMemory fallback)
- RAGRetriever (70% semantic + 15% account + 15% magnitude)
- KnowledgeStore facade (embed + upsert + delete)
- Qdrant Docker service in docker-compose
- 13 new tests

#### CP-2: LLM Narrative Generation
- Pass 5 enhancement: LLM-first with RAG few-shot + template fallback
- Pass 4 enhancement: batch hypothesis generation for correlations
- Board narrative on-demand endpoint
- Engine runner injects LLM + RAG into context
- 8 new tests

#### CP-3: Synthesis + Knowledge Base
- Approval triggers: embed → store → populate knowledge_commentary_history
- Synthesis execution: children approved → parent narrative generated
- Synthesis trigger hook in AsyncReviewStore
- KnowledgeCommentaryRecord ORM model
- 9 new tests

### Acceptance Criteria
- [ ] AI-generated narratives via LLM for material variances (narrative_source="llm")
- [ ] RAG retrieval returns relevant prior commentaries (weighted 70/15/15)
- [ ] Synthesis produces parent-level narratives from approved children
- [ ] CFO gets summary-level, analyst gets detail-level automatically
- [ ] Knowledge base grows with each approval cycle
- [ ] Template fallback always available when LLM unavailable
- [ ] Qdrant Docker runs locally; InMemory fallback if unavailable
- [ ] All tests pass (target: 620+)

---

## Sprint 4 — Reports + Notifications [IN PROGRESS]

**Goal:** Real report generation (4 formats), notifications (3 channels), scheduling.
**Duration:** Week 9–10
**Dependencies:** Sprint 3 complete (645 tests, LLM narratives, RAG pipeline)

### Build Plan (3 Checkpoints)

#### CP-1: Report Generators + API [IN PROGRESS]
- **Data Provider** — fetch report context from computation service
- **Storage Abstraction** — LocalStorage (MVP) + AzureBlobStorage (production)
- **XLSX Generator** — Summary, variances, per-BU tabs, P&L with Marsh branding
- **PDF Generator** — Executive Flash (1-page) + Period-End (multi-page)
- **PPTX Generator** — 5 slides with KPIs, variances, risk items
- **DOCX Generator** — Board narrative with Financial Performance, Recommendations
- **API Wiring** — generate/status/download with background tasks
- Tests: 18 new

#### CP-2: Notifications
- Teams adaptive cards, Slack Block Kit, SMTP email with attachments
- Notification dispatcher: `notify_event()` → all configured channels
- Tests: 6 new

#### CP-3: Scheduling + Frontend
- APScheduler cron-based scheduling
- Frontend: replace mock data with real API calls
- Tests: 8 new

### Acceptance Criteria
- [ ] XLSX opens in Excel with Summary, Variance, BU tabs, P&L sheets
- [ ] PDF renders with KPI boxes, narratives, variance table
- [ ] PPTX has 5 slides with correct content
- [ ] DOCX has Financial Performance, Recommendations sections
- [ ] Storage abstraction allows swap to Azure Blob without code changes
- [ ] Teams/Slack/Email notifications configurable via .env
- [ ] Scheduled reports auto-generate at configured times
- [ ] All tests pass (target: 677+)

---

## Sprint 5 — Auth + RBAC + Polish [IN PROGRESS]

**Goal:** JWT auth (Azure AD swap-in), DB-driven RBAC, persona-narrative filtering, full admin panel, theme polish.
**Duration:** Week 11
**Dependencies:** Sprint 4 complete (677 tests, 3 services, 120+ components)

### Key Decisions
- **Auth:** Dev JWT system with Azure AD swap-in via env vars (no Azure credentials needed now)
- **Role storage:** PostgreSQL tables (users, roles, permissions, user_roles) for maximum flexibility
- **Admin:** Full admin panel with threshold editing, model routing config, user/role management, audit log viewer

### Build Plan (5 Checkpoints)

#### CP-1: Auth Infrastructure (Backend) [IN PROGRESS]

**D1: Database Tables** (`shared/database/models.py`)
- `UserRecord`: id, user_id, email, display_name, password_hash, is_active, created/updated_at
- `RoleRecord`: id, role_name, description, persona_type, narrative_level, is_system
- `UserRoleRecord`: id, user_id (FK), role_id (FK), bu_scope (JSON), assigned_by/at
- `PermissionRecord`: id, role_id (FK), resource, action, scope_type
- Seed: 6 system roles + 1 admin + 5 demo users (one per persona)

**D2: JWT Service** (`shared/auth/jwt.py`)
- `create_access_token()` / `create_refresh_token()` / `decode_token()`
- HS256 signing, configurable expiry (access=1hr, refresh=24hr)
- Payload: `{sub, email, roles, bu_scope, persona, exp, iat, jti}`

**D3: Azure AD Provider** (`shared/auth/azure_ad.py`)
- OAuth code exchange, Microsoft Graph user info, token refresh
- Only activates when `AZURE_AD_TENANT_ID` set in env
- Falls back to local credentials when not configured

**D4: Auth Middleware** (`shared/auth/middleware.py`)
- `get_current_user()` — FastAPI Depends: JWT extraction + validation
- `require_role(*roles)` / `require_bu_access(bu_id)` / `require_admin()`
- Dev mode: returns default dev user when no token + ENVIRONMENT=development

**D5: Auth Endpoints Rewrite** (`services/gateway/api/auth.py`)
- `POST /auth/login` — Azure AD mode OR dev mode (email/password)
- `POST /auth/logout` — Invalidate refresh token
- `GET /auth/me` — Full user profile with roles/permissions
- `POST /auth/refresh` — New token pair from refresh token
- `POST /auth/register` — Dev mode only

**D6: RBAC Service** (`shared/auth/rbac.py`)
- Role checks, BU scope resolution, narrative level mapping
- `filter_by_persona()` — data-level persona enforcement

**D7: UserStore** (`shared/auth/user_store.py`)
- User CRUD, role assignment/removal, permission queries, bulk operations

**Tests:** ~35 (JWT, RBAC, UserStore, auth endpoints, middleware integration)

#### CP-2: RBAC Enforcement (Backend)

**D8: Gateway Endpoint Protection**
- Apply `get_current_user` / `require_role` to all gateway endpoints
- Public: `/auth/login`, `/auth/register`. Admin: config writes, notifications. Role-specific: review (analyst), approval (director/cfo)

**D9: Computation Service Protection**
- Service-to-service token via `X-User-Context` header
- BU filter applied to data queries based on user context

**D10: Persona-Narrative Filtering**
- Analyst → all (detail). BU Leader → own BU, REVIEWED/APPROVED (midlevel). CFO → APPROVED (summary). Board → Board+Summary. HR Finance → HC domain only.

**D11: Audit Integration**
- Auth events: login, logout, failed_login, token_refresh
- RBAC events: unauthorized_access. Config events: threshold_update, role_assignment

**Tests:** ~25 (endpoint protection, RBAC enforcement, persona data access)

#### CP-3: Frontend Auth + Route Guards

**D12: AuthContext + useAuth** — Replace UserContext, JWT in-memory, auto-refresh
**D13: API Client Interceptor** — Auto-attach Bearer token, 401 refresh retry
**D14: Login Page** — Email/password + "Sign in with Microsoft" button
**D15: ProtectedRoute** — Auth + role checks, redirect to login/unauthorized
**D16: Router Update** — Role-gated routes for review, approval, admin
**D17: Persona-Aware UI** — Tab visibility, sidebar BU filtering, narrative level

**Tests:** ~15 (auth context, route guards, persona navigation)

#### CP-4: Admin View (Full)

**D18: Config + Admin API** — CRUD thresholds/routing/users/roles/audit-log
**D19: AdminView Rewrite** — 4 editable tabs (Thresholds, Model Routing, Users & Roles, Audit Log)
**D20: Admin Hooks** — `useAdminConfig`, `useAdminUsers`, `useAdminAuditLog`

**Tests:** ~20 (config CRUD, admin workflow)

#### CP-5: Theme + Polish + Docs

**D21: Theme Audit** — Verify all 120+ components use CSS variable tokens
**D22: Polish** — Login animations, session timeout warning, loading states
**D23: Documentation** — AUTH_GUIDE.md, API_REFERENCE.md update, ARCHITECTURE.md update
**D24: Full Regression** — All 770+ tests pass

**Tests:** ~5 (theme persistence, auth E2E flow)

### Shared Components Centralized

| Component | Location | Used By |
|-----------|----------|---------|
| JWTService | `shared/auth/jwt.py` | Gateway auth, middleware |
| AzureADProvider | `shared/auth/azure_ad.py` | Gateway auth (when configured) |
| RBACService | `shared/auth/rbac.py` | All protected endpoints |
| UserStore | `shared/auth/user_store.py` | Gateway auth, admin API |
| AuthMiddleware | `shared/auth/middleware.py` | All gateway routers |
| AuthContext | `frontend/src/context/AuthContext.tsx` | All frontend components |
| ProtectedRoute | `frontend/src/components/auth/ProtectedRoute.tsx` | Router |
| useAuth | `frontend/src/hooks/useAuth.ts` | Login/logout/refresh |

### Testing Plan

| Checkpoint | New Unit | New Integration | New E2E | Running Total |
|-----------|---------|----------------|---------|---------------|
| CP-1 | ~25 | ~10 | — | ~717 |
| CP-2 | ~10 | ~15 | — | ~742 |
| CP-3 | ~15 | — | — | ~757 |
| CP-4 | ~12 | ~8 | — | ~777 |
| CP-5 | — | — | ~5 | ~782 |

### Acceptance Criteria
- [ ] Login with JWT works (dev mode email/password)
- [ ] Azure AD login activates when AZURE_AD_TENANT_ID configured
- [ ] Unauthenticated requests return 401
- [ ] BU Leader cannot see other BU data
- [ ] CFO sees only approved summaries
- [ ] Board Viewer sees board + summary only
- [ ] HR Finance sees HC domain only
- [ ] Review queue restricted to analysts
- [ ] Approval queue restricted to directors/CFO
- [ ] Admin panel restricted to admin role
- [ ] Admin can edit thresholds → YAML persisted
- [ ] Admin can edit model routing → YAML persisted
- [ ] Admin can manage users and roles
- [ ] Audit log viewer shows all auth/config events
- [ ] Theme toggle works across all views (persisted)
- [ ] All tests pass (target: 780+)

---

## Sprint 6 — Testing + Hardening [COMPLETE]

**Goal:** Full test suite, performance benchmarks, edge cases, Playwright E2E, UAT persona scenarios, documentation.
**Duration:** Week 12 (Final MVP Sprint)
**Dependencies:** Sprint 5 complete (826 tests, full Docker stack, auth/RBAC)
**Result:** **947 tests, 0 skips, 0 failures. MVP complete.**

### Key Decisions
- **E2E:** Playwright browser automation for 7 user journeys
- **UAT:** Automated persona isolation scenarios (not manual checklists)
- **Performance:** pytest-based benchmarks with SLA thresholds

### Build Plan (5 Checkpoints)

#### CP-1: Edge Case Tests + Coverage Gaps (~58 tests)

**D1: Engine Edge Cases** (`tests/unit/computation/test_edge_cases.py`)
- Budget=0 → variance_pct=NaN, flagged "unbudgeted"
- Negative budgets → sign convention applies
- Empty hierarchy nodes → parent skipped
- New accounts (1-2 periods) → trend detection skips
- Missing FX → proportional fallback with `is_fallback=True`
- Missing PY → comparison skipped
- 4 synthetic scenario isolation tests

**D2: Shared Library Tests** (`test_config_thresholds.py`, `test_pydantic_models.py`, `test_hierarchy_cache.py`)
**D3: Gateway Agent Tests** (`test_agents.py`)
**D4: Notification Tests** (`test_notifications.py`)

#### CP-2: Performance Tests (~18 tests)

**D5: Engine Timing** — Full pipeline < 10s, Pass 1 < 3s, Memory < 500MB
**D6: API Latency** — Dashboard < 200ms, Variance list < 300ms, P&L < 500ms
**D7: Database Queries** — User lookup < 10ms, Bulk read < 100ms

#### CP-3: Playwright E2E (~21 tests)

**D8:** Playwright setup (npm install, config)
**D9:** Auth journey (login/logout/redirect)
**D10:** Dashboard journey (filters, charts, modal)
**D11:** Review + Approval journey (edit → review → approve)
**D12:** Chat journey (send → stream → response)
**D13:** Admin journey (tabs, threshold edit)

#### CP-4: Automated UAT Persona Scenarios (~18 tests)

**D14:** 6 personas × data isolation:
- Analyst: review access, no approval/admin
- BU Leader: BU001 only, no other BU data
- CFO: APPROVED only, summary level
- Board: Dashboard+Reports only
- Director: approval queue, bulk approve
- Admin: full access

#### CP-5: Documentation + Config + Regression

**D15:** `docs/DEPLOYMENT_GUIDE.md`
**D16:** `docs/USER_GUIDE.md`
**D17:** Config persistence (read/write YAML)
**D18:** Update MASTER_SPRINT_PLAN, TESTING_FRAMEWORK, API_REFERENCE
**D19:** Final regression: 940+ tests, 0 skips, coverage >80%

### Acceptance Criteria
- [ ] All 6 edge cases have explicit isolated tests
- [ ] 4 synthetic scenarios verified in isolation
- [ ] Engine < 10 seconds (benchmarked)
- [ ] Dashboard APIs < 200ms p95 (benchmarked)
- [ ] Playwright: login → dashboard → review → approve lifecycle
- [ ] 6 personas: correct data isolation + correct 403s
- [ ] Deployment Guide + User Guide complete
- [ ] Config read/write YAML working
- [ ] Full regression: 940+ passed, 0 skipped

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
