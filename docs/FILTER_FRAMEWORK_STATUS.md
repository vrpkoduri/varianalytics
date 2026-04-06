# Unified Filter Framework — Status & Next Steps

**Last Updated:** 2026-04-06
**Latest Commit:** `d2bf15f`
**Docker:** Needs rebuild to include latest fixes

---

## What's Done (Committed)

### Backend (Chunk 1)
- ✅ `_filter_variance()` extended with geo/seg/lob/cc params + BFS hierarchy resolver
- ✅ All 12 computation API endpoints accept dimension query params
- ✅ `get_netting_alerts()` filters by BU via child_details cross-reference
- ✅ `get_trend_alerts()` parses `dimension_key` for BU filtering
- ✅ `get_executive_summary()` and `get_section_narratives()` accept `bu_id` (company-wide only)

### Frontend (Chunks 2-4)
- ✅ `useFilterParams()` hook — canonical source of all filter params
- ✅ `buildFilterQuery()` utility — consistent URL param builder
- ✅ `useDashboard`, `useExecutiveSummary`, `useVariances`, `usePL` — all rewired to useFilterParams
- ✅ Period selector view-type-aware (QTD=quarter-end, YTD=years)
- ✅ Auto-snap period on view type change
- ✅ Client-side dimension filtering removed from DashboardView
- ✅ `ScopeLabel` component created

### Config & UX (Chunks 5-6)
- ✅ `PAGE_FILTER_CONFIG` — centralized filter relevance per page
- ✅ Sidebar hides dimension trees on non-data pages
- ✅ ContextStrip dims irrelevant filter buttons per page

---

## Known Gaps — RESOLVED (Sprint 2026-04-06)

### Gap 1: Persona filtering ✅ FIXED
- Persona now controls narrative level selection (analyst→detail, CFO→summary, etc.)
- New: `shared/config/persona_config.py` — NARRATIVE_LEVEL_MAP + select_narrative()
- Variances API endpoint accepts `persona` param, DataService selects correct narrative level
- Fallback chain ensures graceful degradation if preferred level is empty

### Gap 2: Executive Summary / Section Narratives BU-filtered ✅ FIXED
- Engine (pass5_narrative.py) now generates per-BU + company-wide section narratives and executive summaries
- New `bu_id` column added to SectionNarrativeRecord and ExecutiveSummaryRecord models
- DataService filters by bu_id when provided (None = company-wide)
- Dashboard API endpoints now pass bu_id through

### Gap 3: Dashboard endpoint wiring ✅ FIXED
- `/dashboard/executive-summary` now passes `bu_id` to DataService
- `/dashboard/section-narratives` now passes `bu_id` to DataService

### Gap 4: Root Cause % metric ✅ FIXED
- New `get_success_metrics()` method in DataService
- Computes decomposition coverage % (material variances with decomposition data / total)
- Included in `/dashboard/summary` response under `metrics` key
- Frontend needs wiring (SuccessMetricsBar → real API data instead of mock)

### Gap 5: Revenue Trend period anchoring ✅ FIXED
- `get_trends()` now accepts `period_id` parameter
- Trailing window anchors to selected period (filters to <= period_id, then takes last N)
- Dashboard `/trends` endpoint now accepts and passes `period_id`

### Gap 6: MTD vs Forecast for June 2026 — BY DESIGN
- Synthetic data generator returns `forecast_amount=None` for current/future periods
- This is intentional: forecasts only exist for closed periods
- Frontend should handle gracefully (show "No forecast data for current period")

### Gap 7: Close Progress donut ✅ PARTIALLY FIXED
- Sidebar already wires DonutProgress to filtered variance counts via useVariances
- Needs Docker verification to confirm end-to-end

### Gap 8: Dimension filter wiring ✅ FIXED
- Netting flags now carry dimension columns (bu_id, geo/seg/lob/cc_node_id)
- Trend flags now carry dimension columns + latest_period_id
- DataService alert methods filter on new columns instead of silently ignoring
- Trend alerts now filter by period_id (latest_period_id >= selected period)

---

## Comprehensive Audit Needed (Next Session)

### For EVERY page (Dashboard, Exec Summary, P&L, Review, Approval, Chat, Reports, Admin):

1. **List every section/component** on the page
2. **For each section × each filter dimension**, trace:
   - Does the frontend hook send this filter to the API? (check useFilterParams wiring)
   - Does the API endpoint accept this param? (check FastAPI function signature)
   - Does the API endpoint pass it to the DataService method? (check the call)
   - Does the DataService method actually filter by it? (check the logic)
   - Does the data table have the column needed? (check parquet schema)
3. **Build the complete matrix** showing ✅/❌ for each cell
4. **Fix ALL ❌ cells** in one pass
5. **Write tests** for each filter path

### Test Plan
- Unit tests: `_filter_variance()` with every param combination
- Integration tests: API endpoint returns correctly filtered data
- E2E tests: Select filter in UI → verify all sections update
- Visual tests: Screenshot comparison before/after filter change
- Regression tests: Existing functionality not broken

---

## User's 11 Observations (from PDF)

| # | Observation | Status |
|---|-------------|--------|
| 1 | Persona switch doesn't change dashboard | ✅ FIXED — persona→narrative level selection |
| 2 | Should other personas be hidden? | ✅ ContextStrip dims per PAGE_FILTER_CONFIG |
| 3a | Period→Exec Summary narrative | ✅ FIXED — endpoint passes period + bu_id |
| 3b | Root Cause 0% | ✅ FIXED — decomposition coverage % via get_success_metrics() |
| 3c | Trend Alerts not changing by period | ✅ FIXED — period filter via latest_period_id |
| 3d | Revenue Trend not changing | ✅ FIXED — get_trends() anchors to selected period |
| 3e | Heatmap coloring | ✅ Boosted in previous sprint |
| 4 | MTD vs Forecast broken for Jun 2026 | ℹ️ BY DESIGN — forecasts only for closed periods |
| 5 | MTD vs PY same issues | ℹ️ Investigate PY data availability separately |
| 6 | QTD quarter-end periods only | ✅ usePeriods filters by viewType |
| 7 | YTD year selector | ✅ usePeriods shows years for YTD |
| 8a | BU→Exec Summary | ✅ FIXED — per-BU narratives in engine + service + API |
| 8b | BU→Netting Alerts | ✅ Fixed (now also has bu_id column in fact table) |
| 8c | BU→Trend Alerts | ✅ Fixed (now also has bu_id column in fact table) |
| 9 | Geography filter breaks dashboard | ✅ Client-side removed, backend filtering added |
| 10 | Segment/LOB/CC don't filter | ✅ Backend _filter_variance extended + alert dim columns |
| 11 | Close Progress donut | ✅ Sidebar wires donut to filtered counts — needs Docker verify |
