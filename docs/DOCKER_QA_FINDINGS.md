# Docker QA — Complete Findings

**Date:** 2026-04-05
**Environment:** Docker stack on port 80 (8/8 containers healthy)
**Build:** Commit `9deeff5` — includes all sprint fixes
**Tested:** All 8 pages in dark + light mode via Chrome browser

---

## What's WORKING (confirmed in Docker)

| Feature | Status | Notes |
|---------|--------|-------|
| Account names in Review queue | ✅ FIXED | "Non-Operating Items", "OPERATING INCOME" etc. |
| Account names in Approval queue | ✅ FIXED | "Advisory & Brokerage Fees", "Consulting Fees" etc. |
| Trend alerts proper names | ✅ WORKING | "OPERATING INCOME", "PRE-TAX INCOME" etc. |
| Chat LLM responding | ✅ WORKING | Returns real data-driven analysis from Anthropic |
| Chat intent routing | ✅ WORKING | "Top variances?" routes to Revenue agent |
| Period defaults to Jun 2026 | ✅ WORKING | Latest period with data selected |
| Light mode palette improved | ✅ IMPROVED | Cards have shadows, borders visible, text readable |
| Context strip light mode | ✅ IMPROVED | No more dark band, filter buttons readable |
| Persona switching | ✅ WORKING | Analyst/Director/CFO/BU Lead all switch |
| Filter switching (MTD/QTD/YTD) | ✅ WORKING | Data changes correctly |
| Comparison base (Budget/Fcst/PY) | ✅ WORKING | Data changes correctly |
| P&L income statement | ✅ WORKING | Full hierarchy with expand/collapse |
| P&L margin gauges | ✅ WORKING | 4 gauges visible |
| Variance table with narratives | ✅ WORKING | Account, BU, Geo, Variance, %, Trend, Status, Narrative columns |
| Exec Summary headline + KPIs | ✅ WORKING | Real data, section narratives with driver chips |
| Profitability section light mode | ✅ VISIBLE | Gauge rings faint but visible |
| Netting alerts (count) | ✅ WORKING | 5 pairs showing |
| Trend alerts (count) | ✅ WORKING | 5 trends showing |
| Logo M | ✅ FIXED | Clean bold M on cobalt circle |

## What's BROKEN (needs next sprint)

### Critical / High

| # | Issue | Page | Details |
|---|-------|------|---------|
| D1 | **Dimension trees don't expand** | All pages | Geography, Segment, LOB, Cost Center show "expand" but clicking does nothing. Root node expansion fix didn't work in Docker. |
| D2 | **Sidebar dimensions showing on all pages** | Review, Approval, Reports, Admin | Route-awareness fix (F9) didn't take effect in Docker build. Trees should be hidden on non-data pages. |
| D3 | **Netting alerts show raw account IDs** | Dashboard, Exec Summary | `acct_revenue`, `acct_direct_comp`, `acct_cor` — the netting alerts code in `service.py` uses child_details which has raw IDs, NOT the `_account_lookup` |
| D4 | **Chat markdown not rendered** | Chat | LLM response shows raw `**bold**`, `##` headers, `*` bullets as plain text instead of rendered markdown |
| D5 | **Chat user message bubble missing** | Chat | "Top variances?" sent by user doesn't appear as a sent message bubble |
| D6 | **Chat SSE reconnect** | Chat | Needs verification — didn't test second message in Docker (previously confirmed broken, fix deployed but untested) |
| D7 | **Approval Approve/Hold buttons missing** | Approval | Items show account name + variance + narrative but NO action buttons |
| D8 | **Approval "Approve all reviewed" button missing** | Approval | Report gate banner has no action button |

### Medium

| # | Issue | Page | Details |
|---|-------|------|---------|
| D9 | **P&L missing BUD/VAR$/% columns** | P&L | Only ACCOUNT and ACT columns visible. Budget comparison columns not showing. |
| D10 | **P&L missing "EXPAND ALL" and "Compare" buttons** | P&L | Header controls absent |
| D11 | **Admin "Audit Log" tab cut off** | Admin | Only 4 of 5 tabs visible, 5th tab off-screen |
| D12 | **Admin "Multi-period" checkbox truncated** | Admin | Text shows "M..." cut off on right |
| D13 | **Admin "Estimated Time" missing** | Admin | Cost Estimate card only shows AI Agent Calls and Estimated Cost, not time |
| D14 | **Review "TOTAL" counter card cut off** | Review | 4th status card partially visible on right |
| D15 | **Review sort button missing** | Review | "Impact ↓" sort toggle not showing |
| D16 | **Heatmap column headers missing/cut off** | Dashboard | Geography column labels not visible |
| D17 | **KPI values inconsistent on reload** | Dashboard | Sometimes shows per-BU values instead of totals after theme toggle |
| D18 | **Exec Summary "JUN 2026 VS BUDGET" subtitle cut off** | Exec Summary | Right-aligned text truncated |
| D19 | **Cost of Revenue narrative truncated** | Exec Summary | Right edge cut off |

### Low

| # | Issue | Page | Details |
|---|-------|------|---------|
| D20 | **Profitability gauge rings faint in light mode** | Exec Summary | Donut arcs barely visible against white |
| D21 | **Reports show "No reports generated"** | Reports | Docker Reports API has empty database — previously showed mock data |
| D22 | **Success Metrics bar truncated** | Dashboard | Right side cut off ("ROOT CAUSE", "COMMENTARY" not visible) |

---

## Root Cause Analysis

### Why some fixes didn't work in Docker:

1. **Sidebar route awareness (D2)**: The `AppLayout.tsx` passes `pathname` but the Docker build used the OLD nginx config that may serve cached static assets. Also, the `Sidebar.tsx` component may not be receiving the prop correctly after the build.

2. **Dimension trees (D1)**: The `useEffect` that pre-expands root nodes depends on `hierarchies` data. In Docker, the API data format may differ from the local dev format. Need to debug the actual API response shape vs what `useDimensions` returns.

3. **Approval buttons missing (D7/D8)**: The `useApprovalQueue` hook's data flow may have broken. The approval queue items may be coming back in a different format from the Docker gateway that doesn't match the `ApprovalVariance` type — specifically the `status` field that controls whether buttons render.

4. **P&L columns missing (D9)**: The P&L table responsive layout may be breaking at the Docker viewport. Or the `Compare` toggle state defaults to off, hiding budget columns.

5. **Many "cut off" issues (D11, D12, D14, D16, D18, D19, D22)**: These are all horizontal overflow / responsive layout issues. The Docker-served app may have slightly different viewport behavior than Vite dev.

---

## Recommended Next Sprint Approach

**Stop fixing individual issues. Instead:**

1. **Fix the horizontal overflow/truncation pattern** — a single responsive layout pass will fix D11, D12, D14, D16, D18, D19, D22 (7 issues)
2. **Debug dimension tree API data** in Docker — inspect actual API response, fix data transform
3. **Debug approval queue data flow** — inspect what the API returns vs what the component expects
4. **Add markdown rendering to chat** — install `react-markdown` and render LLM responses
5. **Fix netting alerts account names** — same `_account_lookup` pattern in `service.py`
6. **Always test in Docker** after every change — no more local-only verification
