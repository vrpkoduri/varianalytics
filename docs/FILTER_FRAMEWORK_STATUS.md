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

## Known Gaps (Need Audit & Fix)

### Gap 1: Persona filtering not implemented
- Frontend sends `persona` via useFilterParams
- Backend endpoints do NOT accept or use `persona` param
- `_filter_variance()` does not filter by persona
- Need: Add persona param to endpoints, call RBACService for narrative level selection

### Gap 2: Executive Summary / Section Narratives not BU-filtered
- Methods accept `bu_id` but the underlying tables (`fact_executive_summary`, `fact_section_narrative`) don't have a BU column
- Data is company-wide only
- Need: Either generate per-BU summaries (engine change) OR show scope label "Company-wide"

### Gap 3: Dashboard endpoint wiring gaps
- `/dashboard/executive-summary` endpoint — does it pass `bu_id` to the DataService method? Need to verify.
- `/dashboard/section-narratives` endpoint — same question.

### Gap 4: Root Cause % metric
- Shows 0% — unclear what drives this metric
- Need to investigate `get_summary_cards()` to understand root_cause computation

### Gap 5: Revenue Trend period anchoring
- Revenue Trend uses trailing 12 periods — does it anchor to the selected period or always show latest?
- Need to verify `get_trends()` method logic

### Gap 6: MTD vs Forecast for June 2026
- User reports this combination shows no data
- Need to check `fact_variance_material` for rows with `base_id='FORECAST'` + `period_id='2026-06'`

### Gap 7: Close Progress donut
- `ReviewStatsContext` not wired to any filters
- Donut always shows global counts
- Need to wire to period + BU + dimension filters

### Gap 8: Verification of dimension filter wiring
- Backend `_filter_variance()` extension is done but UNTESTED in Docker
- Need to verify: select "Americas" → KPIs, variance table, P&L all filter correctly

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
| 1 | Persona switch doesn't change dashboard | ❌ Backend doesn't use persona |
| 2 | Should other personas be hidden? | ✅ ContextStrip dims per PAGE_FILTER_CONFIG |
| 3a | Period→Exec Summary narrative | ❓ Need to verify endpoint passes period |
| 3b | Root Cause 0% | ❌ Not investigated |
| 3c | Trend Alerts not changing by period | ❌ get_trend_alerts has no period filter |
| 3d | Revenue Trend not changing | ❓ May be by design (trailing window) |
| 3e | Heatmap coloring | ✅ Boosted in previous sprint |
| 4 | MTD vs Forecast broken for Jun 2026 | ❌ Not investigated |
| 5 | MTD vs PY same issues | ❌ Same root cause as #4 |
| 6 | QTD quarter-end periods only | ✅ usePeriods filters by viewType |
| 7 | YTD year selector | ✅ usePeriods shows years for YTD |
| 8a | BU→Exec Summary | ❌ Backend method doesn't filter by BU |
| 8b | BU→Netting Alerts | ✅ Fixed (cross-reference filtering) |
| 8c | BU→Trend Alerts | ✅ Fixed (dimension_key parsing) |
| 9 | Geography filter breaks dashboard | ✅ Client-side removed, backend filtering added |
| 10 | Segment/LOB/CC don't filter | ✅ Backend _filter_variance extended |
| 11 | Close Progress donut | ❌ Not wired to filters |
