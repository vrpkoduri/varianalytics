# Deep Functional Test — Issues Found

**Date:** 2026-04-05
**Test method:** Live backend (gateway:8000 + computation:8001) + Vite frontend, tested via preview tool
**Tested by:** Claude Code deep visual + functional walkthrough

---

## Critical Issues (9 found)

### ISSUE 1: BU sidebar counts don't update on selection
- **Page:** Dashboard (sidebar)
- **Severity:** Medium
- **Steps:** Click "Mercer" in BU list
- **Expected:** Mercer shows "6" (its own count), other BUs show their counts
- **Actual:** Mercer shows "50" (the global total). All BU items show the same total count regardless of selection
- **Root cause:** `BUList` component displays the variance count per BU from the global dataset, but when a BU is selected, the counts don't refresh to show filtered sub-counts
- **File:** `frontend/src/components/sidebar/BUList.tsx`

### ISSUE 2: BU breadcrumb uses lowercase
- **Page:** Dashboard
- **Severity:** Low
- **Steps:** Select "Mercer" BU
- **Expected:** Breadcrumb shows "Dashboard > Mercer"
- **Actual:** Shows "Dashboard > mercer" (lowercase)
- **Root cause:** The `bu_id` value from the API is lowercase; frontend doesn't title-case it
- **File:** `frontend/src/components/common/Breadcrumb.tsx` or `GlobalFiltersContext.tsx`

### ISSUE 3: Exec Summary page ignores BU filter
- **Page:** Executive Summary
- **Severity:** High
- **Steps:** Select "Mercer" BU in sidebar, navigate to Exec Summary
- **Expected:** KPIs and narrative reflect Mercer-only data
- **Actual:** Shows full company data ($938K Revenue, $158K EBITDA) — same as "All" BU
- **Root cause:** `useExecutiveSummary` hook doesn't pass `bu_id` from GlobalFilters to the `/dashboard/executive-summary` and `/dashboard/section-narratives` API calls
- **File:** `frontend/src/hooks/useExecutiveSummary.ts`

### ISSUE 4: Close Progress donut doesn't change with BU filter
- **Page:** Dashboard, all pages with sidebar
- **Severity:** Medium
- **Steps:** Select "Mercer" BU
- **Expected:** Donut shows review counts for Mercer only
- **Actual:** Always shows global 50/0/0 regardless of BU selection
- **Root cause:** `DonutProgress` reads from `ReviewStatsContext` which fetches `/review/stats` without passing the BU filter
- **File:** `frontend/src/context/ReviewStatsContext.tsx`, `frontend/src/components/sidebar/DonutProgress.tsx`

### ISSUE 5: Dimension hierarchy trees don't expand
- **Page:** All pages with sidebar
- **Severity:** High
- **Steps:** Click "expand" on Geography, Segment, LOB, or Cost Center
- **Expected:** Tree expands to show child nodes (e.g., NA > US > US MW for Geography)
- **Actual:** Nothing happens. The tree remains collapsed with just the "expand" button and `›` chevron
- **Root cause:** `HierarchyTree` component's expand/collapse logic may not be wired to click handler, or the API response format doesn't match the expected tree structure
- **File:** `frontend/src/components/sidebar/HierarchyTree.tsx`, `frontend/src/hooks/useDimensions.ts`

### ISSUE 6: Chat returns generic fallback instead of data-driven answers
- **Page:** Chat
- **Severity:** High
- **Steps:** Click "Top variances?" suggestion pill
- **Expected:** Response lists actual top variances with amounts from the computation service
- **Actual:** Returns: "I can help you analyze financial variances. Try asking about: Revenue performance, P&L summary, Variance trends, Review queue status" — a generic help message
- **Root cause:** The chat backend uses `keyword intent + template responses` when no LLM API key is configured. The template responses are generic help text instead of pulling actual data from the computation service APIs
- **File:** `services/gateway/agents/`, `services/gateway/api/chat.py`

### ISSUE 7: Chat hangs on second message — infinite typing indicator
- **Page:** Chat
- **Severity:** Critical
- **Steps:** Send first message (gets generic response), send second message "How did revenue perform this month?"
- **Expected:** Response appears
- **Actual:** Typing indicator (bouncing dots) shows indefinitely — the SSE stream for the second message never connects
- **Root cause:** Network trace shows the second `POST /chat/messages` returns 201 but no corresponding SSE stream GET is made. The `useChat`/`useSSE` hook may not be re-subscribing to the new message's stream_id
- **File:** `frontend/src/hooks/useChat.ts`, `frontend/src/hooks/useSSE.ts`

### ISSUE 8: Review/Approval queue shows raw account IDs instead of display names
- **Page:** Review Queue, Approval Queue
- **Severity:** High
- **Steps:** View any item in Review or Approval queue
- **Expected:** Shows "Revenue", "Operating Income", "Pre-Tax Income"
- **Actual:** Shows `acct_revenue`, `acct_operating_income`, `acct_pbt`
- **Root cause:** `ReviewStore.get_review_queue()` at line 154 sets `account_name` to the raw `account_id` field. Needs `dim_account` lookup (same fix as `get_trend_alerts()`)
- **File:** `shared/data/review_store.py` (lines 154, 371)

### ISSUE 9: Sidebar dimension filters shown on pages where they're not relevant
- **Page:** Review, Approval, Chat, Reports, Admin
- **Severity:** Medium
- **Steps:** Navigate to Review, Chat, Reports, or Admin page
- **Expected:** Sidebar hides dimension trees (Geography, Segment, LOB, Cost Center) since these pages don't filter by dimensions
- **Actual:** Dimension trees always show on every page
- **Root cause:** `Sidebar` component renders all sections unconditionally. It should check the current route and hide dimension filters on non-data pages
- **File:** `frontend/src/components/layout/Sidebar.tsx`

---

---

## Additional Issues Found in Second Deep Test (with backends running + .env loaded)

### ISSUE 10: Chat keyword intent doesn't route to domain agents
- **Page:** Chat
- **Severity:** High
- **Steps:** Send "Top variances?" or "Show me revenue performance" with LLM available (provider=anthropic confirmed in logs)
- **Expected:** Agent classifies intent, routes to revenue/variance domain agent, returns data-driven response
- **Actual:** Returns generic help template: "I can help you analyze financial variances. Try asking about..."
- **Root cause:** The keyword intent classifier in `orchestrator.py` doesn't recognize these phrases as actionable intents. Even with LLM available, the intent classification falls back to the generic template
- **File:** `services/gateway/agents/orchestrator.py` (intent classification + agent routing)

### ISSUE 11: Heatmap cell click doesn't filter variance table
- **Page:** Dashboard
- **Severity:** Medium
- **Steps:** Click a heatmap cell (e.g., Mercer/Canada +1.4%)
- **Expected:** Variance table filters to show only that BU × Geography intersection
- **Actual:** Variance table continues showing all 50 items unfiltered
- **Root cause:** Either the `onCellClick` handler isn't propagating the filter to `DashboardView`, or the filter comparison `v.bu === heatmapFilter.bu` has a case/format mismatch
- **File:** `frontend/src/views/DashboardView.tsx`, `frontend/src/components/dashboard/Heatmap.tsx`

### ISSUE 12: Notification dropdown text truncated
- **Page:** All pages (header)
- **Severity:** Low
- **Steps:** Click notification bell (shows "3" badge)
- **Expected:** Full notification text visible
- **Actual:** Text truncated: "Engine r...", "Sarah Che...", "SLA warn..."
- **Root cause:** Dropdown width too narrow, no `min-w` set
- **File:** `frontend/src/components/layout/NotificationDropdown.tsx`

### ISSUE 13: Notification dropdown doesn't close on outside click
- **Page:** All pages (header)
- **Severity:** Medium
- **Steps:** Open notification dropdown, click anywhere on main content
- **Expected:** Dropdown closes
- **Actual:** Dropdown stays open
- **Root cause:** The `mousedown` click-outside listener may not be targeting the right DOM element or the event doesn't bubble correctly
- **File:** `frontend/src/components/layout/NotificationDropdown.tsx`

### ISSUE 14: Approval action succeeds but queue doesn't visually update
- **Page:** Approvals
- **Severity:** High
- **Steps:** Click "Approve" on an item
- **Expected:** Item transitions to "Approved" state, confetti fires, report gate count decreases
- **Actual:** API returns 200 OK, but the item still shows Approve/Hold buttons. No visual state change. No confetti.
- **Root cause:** The post-action queue refresh (`GET /approval/queue?page_size=50`) is missing the `persona` param, so it may return different data. Also, the `approveItem()` function may not be triggering a proper re-render
- **File:** `frontend/src/hooks/useApprovalQueue.ts` (refresh after action missing persona param)

### ISSUE 15: Every API call made twice (React 18 Strict Mode)
- **Page:** All pages
- **Severity:** Low (dev only)
- **Steps:** Load any page, observe network tab
- **Expected:** Each API call made once
- **Actual:** Every API call is duplicated (e.g., `/dashboard/summary` called twice, `/variances/` called twice)
- **Root cause:** React 18 Strict Mode in development double-mounts components, triggering all `useEffect` hooks twice. This is expected dev behavior but wastes API calls
- **Note:** This is benign in production (Strict Mode disabled) but makes dev debugging harder
- **File:** `frontend/src/main.tsx` (React.StrictMode wrapper)

---

## Complete Summary (15 issues)

| # | Issue | Severity | Category | Pass/Fail |
|---|-------|----------|----------|-----------|
| 1 | BU sidebar counts don't update | Medium | Data flow | FAIL |
| 2 | BU breadcrumb lowercase | Low | Display | FAIL |
| 3 | Exec Summary ignores BU filter | High | Data flow | FAIL |
| 4 | Close Progress donut ignores BU filter | Medium | Data flow | FAIL |
| 5 | Dimension trees don't expand | High | Interaction | FAIL |
| 6 | Chat returns generic fallback (even with LLM) | High | Feature gap | FAIL |
| 7 | Chat hangs on second message | Critical | Bug | FAIL |
| 8 | Review/Approval raw account IDs | High | Display | FAIL |
| 9 | Sidebar filters on irrelevant pages | Medium | UX | FAIL |
| 10 | Chat intent classification too simplistic | High | Feature gap | FAIL |
| 11 | Heatmap cell click doesn't filter table | Medium | Interaction | FAIL |
| 12 | Notification dropdown text truncated | Low | UX | FAIL |
| 13 | Notification dropdown won't close | Medium | Interaction | FAIL |
| 14 | Approval action doesn't visually update | High | Bug | FAIL |
| 15 | API calls doubled (Strict Mode) | Low | Dev only | KNOWN |

## Tests That Passed

| Test | Status |
|------|--------|
| P&L row expand/collapse (Revenue children) | PASS |
| Review search filter | PASS |
| Review sort toggle (Impact → SLA → Account) | PASS |
| Review checkbox select + batch action bar | PASS |
| Review item expand (narrative + decomposition) | PASS |
| Theme toggle (dark ↔ light via header button) | PASS |
| Notification bell opens dropdown | PASS |
| Reports sub-tabs (Reports/Schedules/Templates) | PASS |
| Report Preview overlay (full-screen, Escape to close) | PASS |
| Admin sub-tabs (all 5 accessible) | PASS |
| Admin Thresholds (real data from API) | PASS |
| Persona switching (Analyst/Director/CFO/BU Lead) | PASS |
| View type switching (MTD/QTD/YTD) | PASS |
| Comparison base switching (Budget/Fcst/PY) | PASS |
| BU filter propagation to Dashboard KPIs | PASS |
| BU filter propagation to P&L | PASS |

## Priority for Next Sprint

### Tier 1: Critical
1. **ISSUE 7** — Chat SSE reconnect (typing indicator hangs forever)

### Tier 2: High
2. **ISSUE 8** — Account name lookup in ReviewStore
3. **ISSUE 3** — Exec Summary BU filter
4. **ISSUE 5** — Hierarchy tree expand
5. **ISSUE 6 + 10** — Chat intent + data-driven responses
6. **ISSUE 14** — Approval action visual update

### Tier 3: Medium
7. **ISSUE 1 + 4** — BU counts + donut filter
8. **ISSUE 9** — Sidebar relevance per page
9. **ISSUE 11** — Heatmap cell click filter
10. **ISSUE 13** — Notification close on outside click

### Tier 4: Low
11. **ISSUE 2** — Breadcrumb capitalization
12. **ISSUE 12** — Notification text truncation
13. **ISSUE 15** — Strict Mode double-fetch (dev only, leave for prod)
