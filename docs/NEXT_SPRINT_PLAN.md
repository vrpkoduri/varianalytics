# Sprint: Unified Filter Framework — All Pages

## Context

User tested Dashboard thoroughly (11 observations in PDF). Core finding: **filters don't work in tandem across sections.** This is NOT a Dashboard-only issue — it affects every page. The same filter architecture (GlobalFiltersContext → hooks → API → backend) powers Dashboard, Exec Summary, P&L, Review, Approval, and Chat. The framework fix must be applied universally.

## What's Broken (Per Page)

### Dashboard
- Persona switch doesn't change content
- Period change doesn't update: Exec Summary narrative, Trend Alerts, Revenue Trend
- MTD vs Forecast/PY broken for some periods
- QTD/YTD period selector shows wrong options
- BU filter doesn't update: Exec Summary, Netting Alerts, Trend Alerts
- Geography/Segment/LOB/CC filters break dashboard or do nothing
- Close Progress donut ignores all filters

### Exec Summary Page
- Same filter issues as Dashboard (period, BU, view/base)
- BU filter doesn't change narrative or KPIs
- Dimension filters not applicable (company-wide) — needs scope label

### P&L Page
- BU filter works ✓ but dimension filters don't
- View/base/period work ✓
- No scope labels when filters aren't applicable

### Review Page
- Doesn't respond to period/view/base filters (uses only persona)
- BU filter client-side only (should be server RBAC)
- Dimension filters irrelevant — should be hidden

### Approval Page
- Same as Review — persona-only filtering
- BU/period/view/base not wired

### Chat Page
- Chat context includes period/BU/view/base ✓ but dimension filters not passed
- Persona affects narrative level but not data scope

---

## Shared Components & Utilities (Defined Upfront)

| Component/Utility | Location | Used By |
|-------------------|----------|---------|
| `useFilterParams()` hook | `frontend/src/hooks/useFilterParams.ts` | ALL data-fetching hooks |
| `buildFilterQuery()` util | `frontend/src/utils/filterParams.ts` | useFilterParams — builds URLSearchParams |
| `ScopeLabel` component | `frontend/src/components/common/ScopeLabel.tsx` | Dashboard, Exec Summary, P&L sections |
| `_filter_variance()` extended | `shared/data/service.py` | ALL DataService query methods |
| `_resolve_hierarchy_descendants()` | `shared/data/service.py` | Dimension filter resolution |
| `FilterConfig` per page | `frontend/src/utils/filterConfig.ts` | Defines which filters apply to which page/section |

### FilterConfig Pattern (NEW — centralized filter relevance)
```typescript
// Which filters are relevant per page
export const PAGE_FILTER_CONFIG = {
  dashboard: { period: true, bu: true, view: true, base: true, dimensions: true, persona: true },
  executive: { period: true, bu: true, view: true, base: true, dimensions: 'scope-label', persona: true },
  pl:        { period: true, bu: true, view: true, base: true, dimensions: true, persona: true },
  review:    { period: true, bu: 'rbac', view: false, base: false, dimensions: false, persona: true },
  approval:  { period: true, bu: 'rbac', view: false, base: false, dimensions: false, persona: true },
  chat:      { period: true, bu: true, view: true, base: true, dimensions: true, persona: true },
  reports:   { period: false, bu: false, view: false, base: false, dimensions: false, persona: true },
  admin:     { period: false, bu: false, view: false, base: false, dimensions: false, persona: true },
}
```

---

## Build Chunks (Logical, Sequential, Low Risk)

### Chunk 1: Backend Foundation (no frontend changes — zero visual risk)

**What:** Extend backend to accept and process ALL filter params. Nothing breaks because new params are optional with defaults.

**Files:**
- `shared/data/service.py` — extend `_filter_variance()` with `geo_node_id`, `segment_node_id`, `lob_node_id`, `costcenter_node_id`; add `_resolve_hierarchy_descendants()` helper; add `bu_id` to `get_executive_summary()` and `get_section_narratives()`
- `services/computation/api/dashboard.py` — add optional query params (`bu_id`, `geo_node_id`, `segment_node_id`, `lob_node_id`, `costcenter_node_id`) to ALL endpoints
- `services/computation/api/variances.py` — add dimension query params
- `services/computation/api/pl.py` — add dimension query params

**Tests:** Unit tests for `_filter_variance()` with dimension params. Unit tests for `_resolve_hierarchy_descendants()`.

**Risk:** Zero — all new params are optional with backward-compatible defaults.

---

### Chunk 2: Frontend Filter Plumbing (internal refactor — no visual change)

**What:** Create shared filter hook and utility. Rewire all hooks to use it. No visual changes — just internal param wiring.

**Files:**
- `frontend/src/hooks/useFilterParams.ts` — NEW: reads GlobalFiltersContext + UserContext, returns canonical params
- `frontend/src/utils/filterParams.ts` — NEW: `buildFilterQuery()` converts params to URLSearchParams string
- `frontend/src/hooks/useDashboard.ts` — rewire to use `useFilterParams()`; pass ALL params to ALL 6 API calls
- `frontend/src/hooks/useExecutiveSummary.ts` — rewire; pass `bu_id` + dimensions
- `frontend/src/hooks/useVariances.ts` — rewire; pass dimensions
- `frontend/src/hooks/usePL.ts` — rewire; pass dimensions

**Tests:** Vitest: `useFilterParams` returns correct params for various filter combinations. Vitest: each hook calls API with expected params.

**Risk:** Low — same data flows, just consistent param passing. All endpoints accept the new params from Chunk 1.

---

### Chunk 3: Period Selector Intelligence (visible UX improvement)

**What:** Make period dropdown view-type-aware. QTD shows quarter-end months only. YTD shows years only. Auto-snap period on view switch.

**Files:**
- `frontend/src/hooks/usePeriods.ts` — accept `viewType` param; filter periods accordingly
- `frontend/src/components/layout/ContextStrip.tsx` — pass viewType to usePeriods; update dropdown rendering
- `frontend/src/context/GlobalFiltersContext.tsx` — add auto-snap logic when SET_VIEW_TYPE dispatched
- `frontend/src/utils/filterConfig.ts` — NEW: PAGE_FILTER_CONFIG + period formatting per view type

**Tests:** Unit: usePeriods with viewType='QTD' returns only quarter-end months. Unit: auto-snap logic.

**Verification:** Switch to QTD → dropdown shows Q1/Q2/Q3/Q4 labels. Switch to YTD → shows 2024/2025/2026. Switch back to MTD → shows all months.

---

### Chunk 4: Dimension Filter Wiring (biggest feature addition)

**What:** Wire dimension tree selections through to backend. Remove client-side dimension filtering.

**Files:**
- `frontend/src/hooks/useFilterParams.ts` — map `dimensionFilter.dimension` + `dimensionFilter.nodeId` to correct param name
- `frontend/src/views/DashboardView.tsx` — REMOVE client-side dimension filtering (lines ~111-124)
- `frontend/src/components/common/ScopeLabel.tsx` — NEW: shows scope pills like "Americas" or "Company-wide"
- All dashboard section components — add ScopeLabel where dimensions aren't filterable

**Tests:** E2E: Select Geography "Americas" → KPI cards show Americas-only totals. Select Segment "Commercial" → variance list filters.

**Verification:** Docker rebuild. Select "Americas" → ALL sections respond (KPIs change, variance table filters, P&L filters). Exec Summary shows "Company-wide narrative" scope label.

---

### Chunk 5: Alerts + Close Progress + Scope Labels (completeness)

**What:** Wire netting/trend alerts to filters. Fix Close Progress donut. Add scope labels everywhere.

**Files:**
- `shared/data/service.py` — parse `dimension_key` in `get_trend_alerts()` for BU/dimension filtering; filter netting alerts via child_details join
- `frontend/src/context/ReviewStatsContext.tsx` — wire to filtered params
- `frontend/src/components/sidebar/DonutProgress.tsx` — use filtered review counts
- All section components — add ScopeLabel where filter isn't applicable

**Tests:** Unit: trend alerts filter by BU. Unit: netting alerts filter by BU. Visual: donut changes when BU selected.

---

### Chunk 6: Page-Level Sidebar + Filter Relevance (UX polish)

**What:** Apply PAGE_FILTER_CONFIG — hide irrelevant filters per page. Sidebar shows only relevant sections.

**Files:**
- `frontend/src/components/layout/Sidebar.tsx` — use `pathname` to determine which sidebar sections to show
- `frontend/src/components/layout/ContextStrip.tsx` — use PAGE_FILTER_CONFIG to disable/dim irrelevant filter buttons per page
- Review/Approval pages — hide dimension trees, dim period/view/base selectors

**Tests:** Visual: On Review page, dimension trees hidden. On Reports page, all data filters dimmed.

---

### Chunk 7: Full QA + Docker Verification + Documentation

**What:** Rebuild Docker. Test every page × every filter combination. Document results.

**Test matrix:**
- 8 pages × (dark + light mode) = 16 visual checks
- Dashboard: 3 views × 3 bases × 5 BUs × 3 dimension samples = 135 combinations (sample 20)
- Each page: verify all sections respond to each filter
- Edge cases: QTD with non-quarter period, YTD with year boundary, empty result sets

---

## Testing Framework

### New Test Files

| File | Type | Count | What it covers |
|------|------|-------|---------------|
| `tests/unit/shared/test_filter_variance_dimensions.py` | Unit | 10 | `_filter_variance()` with geo/seg/lob/cc params |
| `tests/unit/shared/test_hierarchy_resolution.py` | Unit | 5 | `_resolve_hierarchy_descendants()` BFS traversal |
| `tests/unit/computation/test_dashboard_filter_params.py` | Unit | 8 | All dashboard endpoints accept and pass dimension params |
| `frontend/src/hooks/__tests__/useFilterParams.test.ts` | Vitest | 6 | Canonical param generation from all filter combinations |
| `frontend/src/hooks/__tests__/usePeriods.test.ts` | Vitest | 4 | View-type-aware period filtering |
| `tests/e2e/browser/test_filter_framework.py` | E2E | 12 | Full filter propagation across pages |

**After each chunk:** run all tests + TypeScript check + production build.

---

## Key Decisions Captured

1. **Executive Summary filters by Period + View + Base + BU.** Shows "Company-wide" scope label when dimension filters active. Same behavior on Dashboard card and Exec Summary page.
2. **Close Progress donut reflects ALL active filters** (period + BU + dimension + persona).
3. **QTD dropdown shows quarter-end months only.** YTD shows years only. Auto-snap on switch.
4. **Dimension filters are server-side** (not client-side string matching). Backend resolves hierarchy descendants.
5. **Irrelevant filters are hidden/dimmed per page** (Review hides dimensions, Reports dims all data filters).
6. **All 7 chunks in one sprint**, built sequentially to minimize risk.
