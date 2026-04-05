# Sprint: Deep Fixes + Light Mode Overhaul + Chat SSE

## Status: PLAN READY — awaiting approval

**Date:** 2026-04-05
**Previous sprint:** Font replacement, Persona RBAC, SPA routing, dashboard data fixes (COMPLETE)
**Input:** Deep functional test (15 issues) + Light mode visual audit (21 issues) + code exploration
**Scope:** 36 issues total, ~14 actionable functional + 7 root-cause light mode fixes

---

## Issue Inventory (Complete)

### Functional Issues (from deep test — `docs/DEEP_TEST_ISSUES.md`)

| # | Issue | Severity | Root Cause |
|---|-------|----------|------------|
| F1 | BU sidebar counts don't update on selection | Medium | Sidebar's `useVariances` fetches with global BU filter, so per-BU counts collapse |
| F2 | BU breadcrumb lowercase | Low | `Breadcrumb.tsx` line 12 — no title-case transform |
| F3 | Exec Summary ignores BU filter | High | `useExecutiveSummary.ts` line 56 — missing `bu_id` in params |
| F4 | Close Progress donut ignores BU filter | Medium | Donut computes from same filtered variance data as sidebar |
| F5 | Dimension hierarchy trees don't expand | High | `Sidebar.tsx` initializes `expandedMap` with hardcoded IDs that don't match API node IDs |
| F6 | Chat returns generic fallback even with LLM | High | Keyword intent classifier doesn't recognize variance queries; falls back to help template |
| F7 | Chat hangs on second message (CRITICAL) | Critical | `useSSE` hook doesn't reconnect — same `conversationId` means effect deps don't change |
| F8 | Review/Approval raw account IDs | High | `review_store.py` lines 166, 423 — uses `account_id` as display name, no `dim_account` lookup |
| F9 | Sidebar dimension filters on irrelevant pages | Medium | `Sidebar.tsx` renders trees unconditionally; no route awareness |
| F10 | Chat intent too simplistic | High | `orchestrator.py` keyword classifier misses common queries like "top variances" |
| F11 | Heatmap cell click doesn't filter variance table | Medium | `DashboardView.tsx` heatmap filter may have BU name case mismatch |
| F12 | Notification dropdown text truncated | Low | Dropdown too narrow, no `min-w` |
| F13 | Notification dropdown won't close on outside click | Medium | `mousedown` listener not capturing events correctly |
| F14 | Approval Approve action doesn't visually update | High | Post-action queue refresh missing `persona` param; confetti not firing |
| F15 | API calls doubled in dev (Strict Mode) | Low | React 18 StrictMode — benign in production |

### Light Mode Issues (from visual audit — `docs/LIGHT_MODE_AUDIT.md`)

| # | Issue | Severity | Root Cause |
|---|-------|----------|------------|
| L1 | Persona/context strip dark band | High | `bg-[rgba(0,26,77,.35)]` — 35% dark navy on light bg |
| L2 | Inactive filter buttons invisible | High | `color: rgba(255,255,255,0.3)` — white text on dark strip |
| L3 | Subtitle/context text invisible | Medium | `--tx-tertiary: #8B9AB5` too light on white |
| L4 | Glass cards have no visual weight | High | `--card` = `--surface` = `#FFFFFF`; no shadow; `--glass-border` at 8% |
| L5 | Status badges (AI Draft) invisible | Medium | Pale gray on white |
| L6 | Chart axis labels low contrast | Medium | `--tx-tertiary` too light |
| L7 | Heatmap loses heat effect | Medium | Cell tints at 5-20% opacity invisible on white |
| L8-L21 | Various per-page issues | Low-Med | All stem from same root palette problems |

---

## Build Plan (6 Phases)

### Phase 0: Light Mode Palette Overhaul (resolves ~80% of L1-L21)

**Rationale:** Instead of fixing 21 individual component issues, fix the 5 root CSS variables + 3 component-level rules. This is the highest-ROI change in the sprint.

**File: `frontend/src/index.css`** — light theme overrides (lines 40-63)

```css
.light {
  --bg: #F0F3F8;              /* was #F4F7FC — slightly darker for depth */
  --surface: #FFFFFF;
  --card: #FFFFFF;
  --card-alt: #F7F8FC;        /* was #F0F4FA */
  --border: #C8D1E0;          /* was #D4DCE8 — stronger borders */
  --border-hover: #A0ADBE;    /* was #B8C4D6 */
  --tx-primary: #0A1628;
  --tx-secondary: #4A5B74;    /* was #5A6B84 — slightly darker */
  --tx-tertiary: #6B7A90;     /* was #8B9AB5 — MUCH darker, WCAG AA compliant */
  --glass: rgba(255,255,255,.92);     /* was .7 */
  --glass-border: rgba(0,44,119,.15); /* was .08 — doubled */
  /* Data semantics — boost tint opacity */
  --gold-surface: rgba(191,135,0,.12);
  --emerald-surface: rgba(13,147,115,.10);
  --coral-surface: rgba(207,34,46,.10);
  --amber-surface: rgba(202,138,4,.10);
  --purple-surface: rgba(124,58,237,.10);
}
```

**File: `frontend/src/index.css`** — add light-mode card shadow (after `.glass-card` block)

```css
.light .glass-card {
  box-shadow: 0 1px 3px rgba(0,0,0,.08), 0 1px 2px rgba(0,0,0,.04);
  border: 1px solid var(--border);
}
```

**File: `frontend/src/components/layout/ContextStrip.tsx`** — fix dark band

- Change `bg-[rgba(0,26,77,.35)]` to use a CSS variable or conditional class
- Light mode: `bg-[rgba(0,44,119,.06)]` with `text-tx-primary` (dark text)
- Dark mode: keep current `bg-[rgba(0,26,77,.35)]` with light text

**File: `frontend/src/components/layout/ContextStrip.tsx`** — fix filter button colors

- Inactive filter buttons use inline `rgba(255,255,255,.3)` — change to `text-tx-tertiary` (which adapts per theme)
- Active filter buttons use `text-teal` which works in both themes

**File: `frontend/src/components/dashboard/Heatmap.tsx`** — boost cell tint

- `getCellColor()` function returns classes like `bg-emerald/5` — change to `bg-emerald/10` minimum for light mode visibility (or use `bg-emerald-surface` which now has 10% opacity)

**Tests:**
- Vitest: Snapshot render of glass-card in light mode — verify `box-shadow` present
- Visual: All 8 pages in light mode — no invisible text, cards have edges, heatmap shows heat

**Resolves:** L1, L2, L3, L4, L5, L6, L7, L8, L9, L10, L11, L12, L13, L14, L15, L16, L17, L18, L19, L20, L21 (all light mode issues)

---

### Phase 1: Critical Chat SSE Fix (F7)

**File: `frontend/src/hooks/useChat.ts`**
- Add `const [sseKey, setSseKey] = useState(0)`
- In `sendMessageReal()`, after setting conversationId: `setSseKey(prev => prev + 1)`
- Export `sseKey` in return object

**File: `frontend/src/hooks/useSSE.ts`**
- Add 4th parameter `reconnectKey: number = 0`
- Add to effect dependency array: `[conversationId, enabled, reconnectKey]`
- This forces EventSource teardown + reconnect on each new message

**File: `frontend/src/views/ChatView.tsx`**
- Destructure `sseKey` from `useChat()`
- Pass to `useSSE(..., sseKey)`

**Tests:**
- Unit: `useSSE` with changed `reconnectKey` — verify old EventSource closed, new one opened
- E2E: Send 2 messages in chat — both get responses (no hang)

**Resolves:** F7

---

### Phase 2: Data Display Fixes (F3, F8, F14)

**2A: Exec Summary BU Filter (F3)**

File: `frontend/src/hooks/useExecutiveSummary.ts`
- Line 56: Add `bu_id: businessUnit || undefined` to `buildParams()`
- Line 62-63: Add `bu_id` to netting/trend alert params
- Line 71: Add `businessUnit` to dependency array

**2B: Account Name Lookup in ReviewStore (F8)**

File: `shared/data/review_store.py`
- In `__init__()` after line 58: Load `dim_account`, build `self._account_lookup` dict
- Line 166: Replace `str(row.get("account_id", ""))` with lookup
- Line 423: Same for approval queue

**2C: Approval Action Visual Update (F14)**

File: `frontend/src/hooks/useApprovalQueue.ts`
- In `approveItem()` line 75: The refresh call `api.gateway.get('/approval/queue?page_size=50')` is missing the persona param
- Fix: Use the same persona-aware URL: `/approval/queue?page_size=50&persona=${persona}`
- Same fix in `approveAllReviewed()`, `bulkApproveGroup()`, `holdItem()` — all refresh calls

**Tests:**
- Unit: `useExecutiveSummary` with `businessUnit='marsh'` — verify `bu_id=marsh` in API URL
- Unit: `ReviewStore.get_review_queue()` returns "Revenue" not "acct_revenue"
- Unit: `useApprovalQueue` refresh after action includes persona param

**Resolves:** F3, F8, F14

---

### Phase 3: Sidebar & Tree Fixes (F1, F4, F5, F9)

**3A: Sidebar BU Counts + Donut (F1, F4)**

File: `frontend/src/hooks/useVariances.ts`
- Add `ignoreGlobalBU?: boolean` to filter params
- When set, omit `bu_id` from API call so sidebar gets ALL variances for per-BU counting

File: `frontend/src/components/layout/Sidebar.tsx`
- Line 28: Call `useVariances({ ignoreGlobalBU: true })` for sidebar data
- This ensures BU counts always reflect global totals regardless of BU filter selection
- Donut (lines 32-36) then correctly filters from full data to selected BU

**3B: Dimension Hierarchy Tree Expand (F5)**

File: `frontend/src/components/layout/Sidebar.tsx`
- Lines 57-62: The `expandedMap` is initialized with hardcoded IDs (`'global'`, `'all_seg'`, etc.)
- These don't match API data where root IDs are `'geo_global'`, `'seg_all'`, etc.
- Fix: Add `useEffect` that watches `hierarchies` and pre-expands root nodes from actual data:
  ```typescript
  useEffect(() => {
    const newExpanded: Record<string, Set<string>> = {}
    for (const [dim, tree] of Object.entries(hierarchies)) {
      newExpanded[dim] = new Set(tree.map(n => n.id))
    }
    setExpandedMap(prev => {
      // Merge: keep user's manual expansions, add new root IDs
      const merged = { ...prev }
      for (const [dim, ids] of Object.entries(newExpanded)) {
        merged[dim] = new Set([...(prev[dim] || []), ...ids])
      }
      return merged
    })
  }, [hierarchies])
  ```

**3C: Sidebar Route Awareness (F9)**

File: `frontend/src/components/layout/AppLayout.tsx`
- Pass `pathname={location.pathname}` to Sidebar component

File: `frontend/src/components/layout/Sidebar.tsx`
- Add `pathname?: string` to props
- Define data pages: `['/', '/pl', '/executive']`
- Conditionally render dimension trees only on data pages:
  ```typescript
  const showDimensionTrees = !pathname || ['/', '/pl', '/executive'].includes(pathname)
  ```

**Tests:**
- Unit: Sidebar with `pathname="/review"` — dimension trees not rendered
- Unit: Sidebar with `pathname="/"` — dimension trees rendered
- Unit: `useVariances({ ignoreGlobalBU: true })` — API call has no `bu_id`
- Visual: Click "expand" on Geography tree — children appear

**Resolves:** F1, F4, F5, F9

---

### Phase 4: Chat Intent & Routing (F6, F10)

**4A: Keyword Intent Classifier Enhancement**

File: `services/gateway/agents/orchestrator.py`

The keyword classifier needs to recognize common financial queries. Currently it only matches exact keywords. Add pattern matching for:

| Pattern | Intent | Route To |
|---------|--------|----------|
| "top variance", "biggest variance", "material variance" | `variance_summary` | Revenue/Variance agent |
| "revenue", "revenue performance" | `revenue_analysis` | Revenue agent |
| "p&l", "income statement", "profit and loss" | `pl_summary` | P&L agent |
| "review", "what needs review", "pending review" | `review_status` | Review agent |
| "ebitda", "ebitda bridge" | `ebitda_analysis` | Revenue agent |
| "heatmap", "variance heatmap" | `heatmap_view` | Dashboard tools |
| "trend", "emerging risk" | `trend_analysis` | Revenue agent |

**4B: Data-Driven Fallback Responses**

When the orchestrator classifies an intent but the LLM narrative generator is unavailable, the domain agents should still:
1. Call the computation API tool to fetch data
2. Format a structured template response with the data
3. Emit as SSE tokens

File: `services/gateway/agents/domain_agents.py`
- Each agent's `handle()` method should have a `_template_response()` fallback path
- This path calls `self.tool_executor.execute(tool_name, params)` to get data
- Then formats it via string templates (no LLM needed)

**Tests:**
- Unit: Keyword classifier maps "top variances" → `variance_summary` intent
- Unit: Keyword classifier maps "how is revenue" → `revenue_analysis` intent
- Integration: Send "top variances" via chat API — response includes actual variance data (not help text)

**Resolves:** F6, F10

---

### Phase 5: Interaction Polish (F2, F11, F12, F13)

**5A: Breadcrumb Capitalization (F2)**

File: `frontend/src/components/common/Breadcrumb.tsx`
- Line 12: Add title-case transform: `.replace(/\b\w/g, c => c.toUpperCase())`
- Or use the BU name lookup from `transformers.ts`

**5B: Heatmap Cell Click Filter (F11)**

File: `frontend/src/views/DashboardView.tsx`
- Line ~104: Change BU comparison to case-insensitive:
  `v.bu.toLowerCase() === heatmapFilter.bu.toLowerCase()`

**5C: Notification Dropdown Width + Close (F12, F13)**

File: `frontend/src/components/layout/NotificationDropdown.tsx`
- Add `min-w-[320px]` to dropdown container to prevent truncation
- Fix click-outside: verify `useEffect` mousedown listener targets `document` and checks `ref.current.contains(e.target)`

**Tests:**
- Unit: Breadcrumb with `bu='guy_carpenter'` renders "Guy Carpenter"
- Visual: Click heatmap Mercer/Canada cell → variance table shows only Mercer items
- Visual: Notification dropdown shows full text, closes on outside click

**Resolves:** F2, F11, F12, F13

---

### Phase 6: Test Suite + Verification

**New test files:**

| File | Type | Count | Covers |
|------|------|-------|--------|
| `tests/unit/shared/test_review_store_account_names.py` | Unit | 4 | F8 account name lookup |
| `tests/unit/gateway/test_chat_intent_classifier.py` | Unit | 10 | F6/F10 intent patterns |
| `frontend/src/hooks/__tests__/useSSE.test.ts` | Vitest | 3 | F7 SSE reconnect |
| `frontend/src/hooks/__tests__/useExecutiveSummary.test.ts` | Vitest | 2 | F3 BU filter |
| `frontend/src/components/__tests__/Sidebar.test.tsx` | Vitest | 4 | F5/F9 tree expand + route awareness |
| `tests/e2e/browser/test_light_mode.py` | E2E | 8 | Light mode visual per page |
| `tests/e2e/browser/test_chat_flow.py` | E2E | 3 | F7 multi-message chat |

**Total new tests: ~34**

**Regression run:**
- `pytest tests/unit/ tests/integration/ -q` — existing ~1072 tests
- `cd frontend && npx vitest run` — existing 8 + new ~9 = 17 tests
- `npm run build` — TypeScript + production build
- `grep -r "Playfair\|DM Sans" frontend/src/` — font check (should stay 0)

---

## Shared Components / Utilities

| Component | Location | Used By |
|-----------|----------|---------|
| Light mode CSS palette | `frontend/src/index.css` | All pages |
| Card shadow rule | `frontend/src/index.css` | All glass-card components |
| `usePersonaParams` hook | `frontend/src/hooks/usePersonaParams.ts` | Review, Approval, Dashboard hooks |
| Account name lookup | `shared/data/review_store.py` `_account_lookup` | Review queue, Approval queue |
| Keyword intent patterns | `services/gateway/agents/orchestrator.py` | Chat agent routing |
| `formatAccountName()` | `frontend/src/utils/accountNames.ts` | Variance table, Review items (fallback) |

---

## Execution Order & Dependencies

```
Phase 0: Light Mode Palette (independent, no code deps)
  ↓
Phase 1: Chat SSE Fix (independent, CRITICAL priority)
  ↓
Phase 2: Data Display Fixes (F3, F8, F14 — independent of each other)
  ↓
Phase 3: Sidebar & Tree Fixes (depends on Phase 0 for visual verification)
  ↓
Phase 4: Chat Intent (depends on Phase 1 for SSE to work)
  ↓
Phase 5: Interaction Polish (independent small fixes)
  ↓
Phase 6: Test Suite + Full Verification
```

Phases 0, 1, 2 can run in parallel. Phases 3-5 are sequential but small.

---

## Verification Checklist (Definition of Done)

### Functional
- [ ] Chat: Send "Top variances?" → receives data-driven response with actual amounts
- [ ] Chat: Send second message → response streams normally (no hang)
- [ ] Dashboard: Select "Mercer" BU → sidebar counts remain correct (Marsh 25, etc.)
- [ ] Dashboard: Click heatmap cell → variance table filters to that intersection
- [ ] Exec Summary: Select "Mercer" BU → KPIs show Mercer-only data ($187K Revenue)
- [ ] Review Queue: Account column shows "Revenue" not "acct_revenue"
- [ ] Approval: Click "Approve" → item visually transitions, confetti fires
- [ ] Sidebar: Click "expand" on Geography → tree shows Americas, EMEA, Asia Pacific
- [ ] Sidebar: On /review page → no dimension trees shown
- [ ] Notification: Dropdown shows full text, closes on outside click
- [ ] Breadcrumb: Shows "Guy Carpenter" not "guy_carpenter"

### Light Mode (all 8 pages)
- [ ] Cards have visible edges (shadow + border)
- [ ] All label text readable (subtitle, context, tertiary text)
- [ ] Persona strip blends with light background (no dark band)
- [ ] Inactive filter buttons visible (dark text on light strip)
- [ ] Heatmap cells show color tints (heat visible)
- [ ] Chart axis labels readable
- [ ] Status badges (AI Draft, Material) visible
- [ ] Review items have clear visual separation

### Build
- [ ] TypeScript: 0 errors
- [ ] Production build: success
- [ ] All existing tests pass (regression)
- [ ] All new tests pass (~34)
- [ ] No old font references remain
