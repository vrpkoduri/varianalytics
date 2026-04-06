# Sprint: Filter Wiring + Functional Fix-All — Detailed Plan

## Context

The Filter Framework backend changes (Chunks 1-6) are committed but the engine hasn't been re-run to regenerate fact tables. Additionally, there are 22 Docker QA issues (D1-D22) and 15 functional issues (ISSUE 1-15) from prior testing. This sprint completes frontend wiring, fixes all remaining functional issues, and verifies everything in Docker.

**Code audit findings**: Several "broken" issues are actually working in code (heatmap click, BU counts, breadcrumb, notification dropdown, Expand All button) — they likely need Docker rebuild + re-test, not code changes. The real code issues are: dimension tree expand, approval buttons, chat SSE/markdown, P&L columns, responsive overflow, and metrics wiring.

---

## Shared Components & Utilities (Defined Upfront)

**Existing (reuse):**

| Component | Location | Used By |
|-----------|----------|---------|
| `useFilterParams()` | `frontend/src/hooks/useFilterParams.ts` | All data hooks |
| `useDashboard()` | `frontend/src/hooks/useDashboard.ts` | DashboardView |
| `renderMarkdown()` | `frontend/src/utils/markdown.tsx` | AgentMessage |
| `transformHierarchyTree()` | `frontend/src/utils/transformers.ts` | useDimensions |
| `_account_lookup` | `shared/data/service.py` | All name resolution |

**New shared additions this sprint:**

| Component | Location | Purpose |
|-----------|----------|---------|
| `useClickOutside()` hook | `frontend/src/hooks/useClickOutside.ts` (NEW) | Reusable click-outside handler for dropdowns |
| Responsive utility classes | `frontend/src/index.css` | `overflow-x-auto`, responsive grid breakpoints |

---

## Phases (6 phases, sequential)

### Phase 1: Engine Re-run + Frontend Wiring (Completes Filter Sprint)

**Why:** Backend changes from Chunks 1-6 added new columns and methods, but fact tables haven't been regenerated. Frontend needs 3 small wiring changes to use the new API data.

**1a: Re-run computation engine**
- Run `python3 scripts/run_engine.py` to regenerate all parquet files
- Verify new columns exist in output: `fact_netting_flags` has `bu_id`, `geo_node_id`, etc.
- Verify `fact_section_narrative` and `fact_executive_summary` have `bu_id` column
- Verify `fact_trend_flags` has `latest_period_id`

**1b: Wire SuccessMetricsBar to API metrics**

**File:** `frontend/src/views/DashboardView.tsx`
- Lines 71-82: Currently computes metrics client-side, overriding API data
- Change: Use `summary.metrics` from API (which now includes `root_cause_pct`, `commentary_pct`, `close_pct`)
- Map API fields to component props: `rootCause: summary.metrics.root_cause_pct`
- Keep client-side fallback if API metrics not available

**File:** `frontend/src/components/dashboard/SuccessMetricsBar.tsx`
- Update `MockMetrics` type to match API response fields (or create proper type)

**1c: Pass period_id to trends endpoint**

**File:** `frontend/src/hooks/useDashboard.ts`
- The `/dashboard/trends` call needs to include `period_id` in the query params
- Currently uses `buildQuery({ periods: 12 })` — add `period_id` from filter params

**1d: Handle MTD vs Forecast gracefully**

**File:** `frontend/src/views/DashboardView.tsx` or `frontend/src/components/dashboard/KPICard.tsx`
- When all summary cards return empty for FORECAST + current period, show "No forecast data for current period" message
- Alternative: Disable FORECAST option in ContextStrip when period is current

**Tests:**
- Unit: SuccessMetricsBar renders API metrics correctly
- Unit: useDashboard passes period_id to trends endpoint
- Integration: `/dashboard/summary` returns `metrics` object with real values after engine re-run

---

### Phase 2: Dimension Trees + Approval Buttons (High-Impact Interaction Fixes)

**Why:** Trees and approval buttons are the two most broken interactive features. Trees affect every page with sidebar; approval buttons block the review workflow.

**2a: Fix dimension tree expand (D1/ISSUE 5)**

**Root cause from audit:** `expandedIds` Set in HierarchyTree.tsx is initialized empty. No root nodes are pre-expanded. The tree structure arrives correctly from the API, but everything starts collapsed and the toggle may not be working.

**File:** `frontend/src/components/sidebar/HierarchyTree.tsx`
- Lines 42-45: `expandedIds` starts as empty Set
- Fix: Initialize with root node IDs expanded (auto-expand first level)
- Add useEffect to auto-expand roots when `nodes` prop changes

**File:** `frontend/src/hooks/useDimensions.ts`
- Verify that hierarchy API response shape matches `transformHierarchyTree()` expectations
- Log the raw API response for debugging if transform fails silently

**2b: Fix approval buttons (D7/D8)**

**Root cause from audit:** Buttons render when `status !== 'approved'`. The issue is likely that API returns `status='APPROVED'` (uppercase) but the component checks for lowercase `'approved'`.

**File:** `frontend/src/utils/transformers.ts`
- Lines 328-345: Status transformation — verify case mapping
- Ensure `'ANALYST_REVIEWED'` maps to `'reviewed'` (not `'approved'`)

**File:** `frontend/src/components/approval/ApprovalItem.tsx`
- Lines 50-69: Button rendering conditional on `isApproved`
- Verify the status value at runtime via console logging

**File:** `frontend/src/views/ApprovalView.tsx`
- Check if "Approve all reviewed" button exists in the report gate banner component

**Tests:**
- Unit: HierarchyTree auto-expands root nodes
- Unit: Approval item renders Approve/Hold buttons when status is 'reviewed'
- Unit: Status transformer maps ANALYST_REVIEWED → reviewed correctly
- E2E: Click Geography expand → children appear
- E2E: Approval page shows Approve/Hold buttons on reviewed items

---

### Phase 3: Chat Fixes (SSE Reconnect + Markdown + User Bubble)

**Why:** Chat is currently non-functional for multi-turn conversations. Three fixes needed.

**3a: Chat SSE reconnect (D6/ISSUE 7)**

**From audit:** The `sseKey` mechanism in useChat.ts looks correct — it increments on each message to force useSSE to re-subscribe. But the issue may be that:
1. The SSE EventSource URL doesn't include the new message ID
2. The gateway may not emit events for subsequent messages in the same conversation

**File:** `frontend/src/hooks/useSSE.ts`
- Lines 18-72: Verify EventSource URL includes conversation_id correctly
- Check if 'done' event properly clears `isStreaming` flag

**File:** `frontend/src/hooks/useChat.ts`
- After `sendMessageReal()` succeeds, verify `isStreaming` is set to `true`
- After SSE 'done' event, verify `isStreaming` is set to `false`

**File:** `frontend/src/views/ChatView.tsx`
- Verify SSE event handler properly updates message state

**3b: Fix chat keyword intent classifier (ISSUE 6/10)**

**Root cause:** The `KeywordIntentClassifier` in `intent.py` has good coverage for specific queries ("decomposition", "waterfall", "p&l") but common phrases like "top variances?" and "how did we perform?" match `REVENUE_OVERVIEW` or fall through to `GENERAL`, which returns a static help template instead of data.

**File:** `services/gateway/agents/intent.py`
- Lines 58-101: Add patterns for common queries:
  - "top variances", "biggest variances", "material variances" → `VARIANCE_DETAIL`
  - "how did we do", "how did we perform", "performance" → `REVENUE_OVERVIEW`
  - "what happened", "what changed" → `REVENUE_OVERVIEW`

**File:** `services/gateway/agents/templates.py`
- Lines 67-80: Make `GENERAL` intent fallback smarter — instead of static help text, call `get_dashboard_summary` tool and format a brief overview

**File:** `services/gateway/agents/orchestrator.py`
- Lines 159-162: Route `GENERAL` intent to a summary response that pulls actual data instead of generic text

**3c: Chat markdown rendering (D4)**

**From audit:** `renderMarkdown()` in `markdown.tsx` exists and handles bold, headers, lists. The issue is that `isStreaming` flag may not be cleared to `false` after SSE completes, so text stays in raw pre-wrap mode.

**File:** `frontend/src/views/ChatView.tsx`
- Verify SSE 'done' event handler sets the message's `isStreaming = false`

**File:** `frontend/src/utils/markdown.tsx`
- Verify renderMarkdown handles LLM output patterns (may need `###` headers, `---` separators, `>` blockquotes)

**3c: Chat user message bubble (D5)**

**From audit:** `UserMessage.tsx` component is correctly structured. The issue may be:
1. CSS variables `bg-card` or `border-border` not resolving in Docker
2. Message not being added to state before SSE response arrives

**File:** `frontend/src/views/ChatView.tsx`
- Verify user message is added to state array before API call
- Check rendering loop includes `role === 'user'` case

**Tests:**
- Unit: useChat adds user message to state before API call
- Unit: SSE 'done' event clears isStreaming flag
- Unit: renderMarkdown handles `**bold**`, `## headers`, `- lists`
- E2E: Send message → user bubble appears → agent response streams → markdown rendered → send second message → response appears

---

### Phase 4: P&L Columns + Responsive Layout Pass

**Why:** P&L missing budget columns is a feature gap. Responsive truncation affects 8+ pages.

**4a: P&L Compare toggle (D9)**

**From audit:** The "Compare" button exists but is `disabled`. Budget columns exist in PLHeaderRow but the grid template only shows ACT column prominently.

**File:** `frontend/src/components/pl/PLGrid.tsx`
- Enable the Compare button
- Add state: `showCompare` toggle
- When `showCompare=true`: show BUD, VAR$, VAR% columns
- When `showCompare=false`: show only ACT column (current default)

**File:** `frontend/src/components/pl/PLHeaderRow.tsx`
- Already has 7 columns including BUD and VAR$ — verify they're rendering
- May need to conditionally show/hide columns based on Compare state

**File:** `frontend/src/components/pl/PLRow.tsx`
- Same — conditionally render budget comparison cells

**4b: Responsive layout pass (D11-D19, D22)**

**Single root cause:** No responsive breakpoints, `flex-1` on tabs, `grid-cols-4` without mobile fallbacks, `overflow-hidden` on glass-card clips content.

**Files to modify:**
- `frontend/src/index.css`: Add `overflow-x-auto` to scrollable containers
- `frontend/src/views/AdminView.tsx`: Change `flex-1` tabs to `flex-shrink-0` with `overflow-x-auto` wrapper
- `frontend/src/components/review/StatusCounterCards.tsx`: Add responsive breakpoint `grid-cols-2 lg:grid-cols-4`
- `frontend/src/components/dashboard/SuccessMetricsBar.tsx`: Add `overflow-x-auto` or `flex-wrap`
- `frontend/src/components/dashboard/Heatmap.tsx`: Add `overflow-x-auto` wrapper for column headers
- `frontend/src/views/ExecSummaryView.tsx`: Ensure subtitle doesn't truncate

**Pattern:** For each truncation issue, add either:
- `overflow-x-auto` for scrollable content
- `flex-wrap` for wrapping content
- `min-w-0` + `truncate` for text truncation with tooltip
- Responsive grid breakpoints (`grid-cols-2 md:grid-cols-4`)

**Tests:**
- Visual: Admin page shows all 5 tabs at 1280px width
- Visual: Review page shows all 4 counter cards
- Visual: Success Metrics bar shows all 4 metrics
- Visual: Heatmap column headers visible

---

### Phase 5: Small UX Fixes (Netting Names, Notification, BU Sidebar)

**Why:** These are individually small but collectively improve polish. Many may already work — confirm in Docker first.

**5a: Netting alerts account names (D3)**

**File:** `shared/data/service.py` → `get_netting_alerts()`
- Lines 1174-1181: Already uses `self._account_lookup` for left/right names
- May need to also apply lookup to `child_details` account names before building alert text
- Verify `_account_lookup` is populated when engine runs

**5b: Approval visual update (ISSUE 14)**

**From audit:** The `approveItem()` in `useApprovalQueue.ts` actually does re-fetch the queue (line 71), fire confetti (line 93), and has a fallback state update (lines 76-85). The issue may be:
1. The re-fetch URL includes `persona` param that returns different data
2. `transformApprovalItems()` may not correctly map the refreshed response
3. React state may not trigger re-render because item reference hasn't changed

**File:** `frontend/src/hooks/useApprovalQueue.ts`
- Lines 62-96: Debug the approval flow — add error handling for the re-fetch
- Ensure `setItems()` forces re-render by creating new array (not mutating)
- Verify `persona` param matches what was used in initial load

**File:** `frontend/src/views/ApprovalView.tsx`
- Verify the component re-renders when `items` state changes

**5c: Notification dropdown (ISSUE 12-13)**

**From audit:** Click-outside logic exists (line 15-23 in NotificationDropdown.tsx). The `containerRef` may not be passed correctly from the parent (Header component).

**File:** `frontend/src/components/layout/Header.tsx` or parent component
- Verify `containerRef` is created and passed to NotificationDropdown
- If not passed, the click-outside handler falls back to `dropdownRef` which may not include the bell icon

**File:** `frontend/src/components/layout/NotificationDropdown.tsx`
- Lines 32-33: Increase `min-w-[340px]` to `min-w-[380px]` for text truncation fix (ISSUE 12)

**5c: Verify in Docker — items that may already work**
- ISSUE 1: BU sidebar counts — code is correct, needs Docker verify
- ISSUE 2: BU breadcrumb — code correctly title-cases, needs Docker verify
- ISSUE 11: Heatmap click — code is fully wired, needs Docker verify
- D10: P&L Expand All — button exists and is wired, needs Docker verify

**Tests:**
- Unit: Netting alert names use account_lookup
- E2E: Notification dropdown closes on outside click

---

### Phase 6: Docker Rebuild + Full Verification + Documentation

**Why:** Every code change needs Docker verification. Many "issues" may resolve with a clean rebuild.

**6a: Docker rebuild**
- `docker-compose build --no-cache`
- Verify all 8 containers healthy
- Confirm engine data is loaded

**6b: Full verification matrix**

| Page | Filters to Test | Sections to Verify |
|------|-----------------|-------------------|
| Dashboard | BU, Period, View, Base, Geo, Persona | KPIs, Heatmap, Waterfall, Trends, Alerts, Exec Summary, Success Metrics |
| Exec Summary | BU, Period | Headline, Narrative, KPIs, Alerts, Profitability |
| P&L | BU, Period, Dimensions | Statement, Expand/Collapse, Compare toggle |
| Review | Persona | Queue items, Status cards, Sort, Search |
| Approval | Persona | Queue items, Approve/Hold buttons, Report gate |
| Chat | All filters | User bubble, Agent response, Markdown, SSE reconnect |
| Reports | — | Sub-tabs, Preview |
| Admin | — | All 5 tabs visible, Thresholds, Audit Log |

**6c: Documentation update**
- Update `docs/FILTER_FRAMEWORK_STATUS.md` — final status
- Update `docs/NEXT_SPRINT_PLAN.md` — mark all phases complete
- Create `docs/DOCKER_QA_RESOLUTION.md` — map D1-D22 to resolution status
- Update `docs/TESTING_FRAMEWORK.md` — add new test inventory

---

## Test Plan (Consolidated)

### New Test Files

| File | Type | Count (est.) | What |
|------|------|-------------|------|
| `frontend/src/hooks/__tests__/useDashboard.test.ts` (extend) | Vitest | 4 | period_id in trends, metrics from API |
| `frontend/src/components/__tests__/SuccessMetricsBar.test.tsx` | Vitest | 3 | Renders API metrics, fallback to mock |
| `frontend/src/components/__tests__/HierarchyTree.test.tsx` | Vitest | 4 | Auto-expand roots, toggle, collapse |
| `frontend/src/components/__tests__/ApprovalItem.test.tsx` | Vitest | 3 | Buttons on reviewed, hidden on approved |
| `frontend/src/hooks/__tests__/useChat.test.ts` (extend) | Vitest | 3 | Dimension context, persona, user msg state |
| `tests/unit/shared/test_netting_account_names.py` | pytest | 3 | Account names resolved in alerts |
| `tests/unit/gateway/test_keyword_intent.py` | pytest | 8 | Keyword patterns match common queries |
| `tests/integration/test_engine_output_schema.py` | pytest | 6 | New columns in regenerated parquet files |
| `frontend/src/hooks/__tests__/useApprovalQueue.test.ts` (extend) | Vitest | 3 | Approve triggers refresh + confetti |
| `tests/e2e/browser/test_functional_fixes.py` | Playwright | 12 | Dimension expand, approval, chat, responsive |
| **Total new** | | **~46** | |

### Existing Tests (Run After Each Phase)

| File | Count | What |
|------|-------|------|
| `tests/unit/detection/test_netting_dimensions.py` | 6 | Netting dimension columns |
| `tests/unit/detection/test_trend_dimensions.py` | 7 | Trend dimension columns |
| `tests/unit/shared/test_persona_narrative.py` | 13 | Persona narrative selection |
| `tests/unit/shared/test_alert_dimension_filters.py` | 8 | Alert dimension filtering |
| `tests/unit/shared/test_trend_anchoring.py` | 4 | Trend period anchoring |
| `tests/unit/shared/test_hierarchy.py` | 19 | Hierarchy tree operations |
| `tests/unit/shared/test_hierarchy_cache.py` | 13 | Hierarchy cache |
| **Total existing** | **70** | |

### Test Execution After Each Phase

```
Phase 1 → run all backend tests + verify engine output
Phase 2 → run frontend Vitest + backend tests
Phase 3 → run frontend Vitest (chat tests)
Phase 4 → run frontend Vitest + visual checks
Phase 5 → run all backend + frontend tests
Phase 6 → full regression suite + Docker E2E
```

---

## Build Order & Dependencies

```
Phase 1 (Engine re-run + frontend wiring)
    ↓ must complete first — regenerates data for all other phases
Phase 2 (Dimension trees + Approval buttons)
    ↓ independent of Phase 3-5
Phase 3 (Chat SSE + Markdown + Bubble)
    ↓ independent of Phase 2, 4-5
Phase 4 (P&L columns + Responsive pass)
    ↓ independent of Phase 2-3, 5
Phase 5 (Small UX fixes)
    ↓ independent
Phase 6 (Docker rebuild + full verify + docs)
    ↓ depends on ALL above
```

Phases 2, 3, 4, 5 are independent and could be built in any order.

---

## Decisions (Confirmed by User)

1. **P&L Compare (D9):** DEFERRED — leave Compare button disabled this sprint
2. **Chat intent routing (ISSUE 6/10):** FIX keyword classifier — make it return real data without LLM key
3. **Approval visual update (ISSUE 14):** FIX NOW — wire post-action refresh + confetti

---

## Risk Assessment

| Risk | Mitigation |
|------|-----------|
| Engine re-run may fail with schema changes | Run locally first, verify output before Docker |
| Dimension tree fix may break existing tree behavior | Preserve backward compat: only auto-expand roots if no manual expansion |
| Chat SSE fix is hard to test without Docker | Add unit tests for state management, verify in Docker |
| Responsive changes may break existing layouts | Use additive CSS only (no removing existing styles), test at 1280px + 1440px |
| Node.js not available locally for frontend tests | Run Vitest inside Docker container, or install Node locally |
