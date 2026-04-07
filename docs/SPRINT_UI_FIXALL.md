# Sprint: UI Fix-All — Visual Issues from Docker QA

## Context

Visual review of the Docker deployment confirmed 10 items are now working. However, 10 items remain broken across Chat, P&L, Review, Admin, and Dashboard. This sprint fixes all remaining visual/functional issues in one pass.

**Key finding from code audit:** Most issues are CSS/layout problems, not missing code. The components render correctly but are invisible, clipped, or overflowed due to theme variables, grid constraints, or flex conflicts.

---

## Shared Components & Reuse

| Existing | Location | Reuse |
|----------|----------|-------|
| CSS theme variables | `frontend/src/index.css` | Fix `--card`/`--border` contrast |
| Glass-card pattern | `frontend/src/index.css` | overflow behavior |
| `PLGrid` + row components | `frontend/src/components/pl/` | Column visibility |
| `ReviewSortBar` | `frontend/src/components/review/ReviewSortBar.tsx` | Sort button |
| `SuccessMetricsBar` | `frontend/src/components/dashboard/SuccessMetricsBar.tsx` | Metrics overflow |

No new shared components needed — all fixes are targeted CSS/layout changes.

---

## Chunks (4 logical groups)

### Chunk 1: Chat Fixes (D4, D5, D6)

**1a: Chat user message bubble invisible (D5)**

**Root cause:** `bg-card` (#0F1D32) and `border-border` (#1A2A42) are nearly identical in dark mode, making the user bubble invisible against the chat background.

**File:** `frontend/src/components/chat/UserMessage.tsx`
- Line 8: Change `bg-card border border-border` to a more visible style
- Use `bg-[rgba(0,168,199,0.08)] border border-teal/20` — subtle teal tint that distinguishes from background
- Keep light mode working (teal tint works in both themes)

**1b: Chat markdown rendering (D4)**

**Root cause:** `isStreaming` flag may not clear properly after SSE completes, keeping text in raw `whitespace-pre-wrap` mode instead of running through `renderMarkdown()`.

**File:** `frontend/src/views/ChatView.tsx`
- Verify SSE 'done' event handler sets `isStreaming = false` on the message
- If mock fallback is used, ensure streaming flag clears after mock animation completes

**File:** `frontend/src/components/chat/AgentMessage.tsx`
- Line 103: Currently `{isStreaming ? text : renderMarkdown(text)}` — verify this conditional works

**1c: Chat SSE reconnect (D6/ISSUE 7)**

**Root cause from prior audit:** The `sseKey` mechanism in `useChat.ts` looks correct. The actual issue may be that the gateway LLM isn't configured (no API key in Docker), so the agent returns an error on first message and SSE never properly starts.

**Action:** Verify with working LLM on other machine. If SSE still hangs after LLM is configured, debug the EventSource lifecycle in `useSSE.ts`.

### Chunk 2: P&L Columns + Buttons (D9, D10)

**Root cause:** All 7 columns and both buttons ARE in the code and render unconditionally. The visual review showed only ACCOUNT + ACT columns visible. This is likely a **horizontal overflow issue** — the P&L grid is wider than the viewport but `overflow-hidden` on `.glass-card` clips the content.

**File:** `frontend/src/components/pl/PLGrid.tsx`
- Wrap the table in `overflow-x-auto` so columns can scroll horizontally
- Grid template: `'minmax(180px, 1fr) 70px 70px 70px 60px 45px 50px'` = ~535px minimum
- At narrow viewport with sidebar, content area may be <500px

**File:** `frontend/src/index.css`
- Check if `.glass-card` has `overflow-hidden` that clips the grid
- Change to `overflow-visible` or add `overflow-x-auto` to the P&L glass-card specifically

**For buttons (D10):** The Expand All and Compare buttons are at the top of PLGrid (lines 92-110). If the P&L content scrolls, they may be above the visible area. Verify after fixing overflow.

### Chunk 3: Review Sort Button + Admin Truncation (D12, D15)

**3a: Review sort button (D15)**

**Root cause:** `ReviewSortBar` renders but may be pushed off-screen by animation class `d3` or parent overflow.

**File:** `frontend/src/views/ReviewView.tsx`
- Check the container that holds `ReviewSortBar` — ensure no overflow clip
- Verify the `animate-fade-up d3` class isn't pushing content off-screen initially

**3b: Admin multi-period checkbox (D12)**

**Root cause:** Label text "Multi-period (12 months)" overflows at 2-column grid layout without wrapping.

**File:** `frontend/src/components/admin/AdminEngineControlTab.tsx`
- Line 123: Add `whitespace-nowrap` to the label, or shorten to "Multi-period"
- Or change the parent grid to accommodate the text

### Chunk 4: Success Metrics + Minor Polish (D13, D16-D19, D22)

**4a: Success Metrics clipping (D22)**

**Root cause:** `justify-between` + `flex-shrink-0` on inner container prevents proper scroll. Metrics pushed off right edge.

**File:** `frontend/src/components/dashboard/SuccessMetricsBar.tsx`
- Remove `justify-between` from outer container — use `gap-6` instead
- Remove `flex-shrink-0` from inner metrics container
- Add `min-w-0` to allow flex items to shrink
- Or: reduce `gap-6` to `gap-4` and make metric labels smaller

**4b: Responsive truncation pass (D16-D19)**

**Pattern fix:** Add `overflow-x-auto` wrapper to:
- Heatmap column headers (D16) — already has it, may need wider min-width
- Exec Summary subtitle (D18) — add `truncate` class
- Cost of Revenue narrative (D19) — add `line-clamp-2` or `truncate`

**4c: Admin estimated time (D13)**

**File:** `frontend/src/components/admin/AdminEngineControlTab.tsx`
- Cost Estimate section shows "AI Agent Calls" and "Estimated Cost" but not "Estimated Time"
- Add estimated time calculation or "N/A" placeholder

---

## Build Order

```
Chunk 1 (Chat: bubble + markdown + SSE)
  ↓
Chunk 2 (P&L: columns + buttons)
  ↓
Chunk 3 (Review sort + Admin checkbox)
  ↓
Chunk 4 (Success Metrics + polish)
  ↓
Frontend rebuild + Docker test + commit
```

---

## Files to Modify

| File | Changes |
|------|---------|
| `frontend/src/components/chat/UserMessage.tsx` | Fix bubble visibility in dark mode |
| `frontend/src/components/chat/AgentMessage.tsx` | Verify markdown rendering |
| `frontend/src/views/ChatView.tsx` | Verify SSE done clears isStreaming |
| `frontend/src/components/pl/PLGrid.tsx` | Add overflow-x-auto to table wrapper |
| `frontend/src/index.css` | Fix glass-card overflow for P&L |
| `frontend/src/views/ReviewView.tsx` | Fix sort bar visibility |
| `frontend/src/components/admin/AdminEngineControlTab.tsx` | Fix checkbox label + add est. time |
| `frontend/src/components/dashboard/SuccessMetricsBar.tsx` | Fix flex layout for metrics |
| `frontend/src/views/ExecSummaryView.tsx` | Fix subtitle truncation |

---

## Test Plan

**After each chunk:**
- Frontend `vite build` succeeds
- Docker rebuild + visual verification at localhost

**Visual verification checklist:**
- [ ] Chat: user bubble visible in dark mode
- [ ] Chat: send message → see user bubble + agent response with markdown
- [ ] P&L: all 7 columns visible (ACCOUNT, ACT, BUD, VAR$, %, FAV, TYPE)
- [ ] P&L: Expand All and Compare buttons visible at top
- [ ] Review: sort button visible
- [ ] Admin: "Multi-period (12 months)" text not truncated
- [ ] Dashboard: all 4 Success Metrics visible (CYCLE TIME, COVERAGE, ROOT CAUSE, COMMENTARY)
- [ ] Exec Summary: subtitle not truncated

**Regression checks:**
- [ ] BU filter still works (donut, KPIs, exec summary, variance table all update)
- [ ] Dimension trees still expand
- [ ] Admin AI Monitoring tab still renders
- [ ] All existing tests pass (74 pytest tests)

---

## Verification

1. After all chunks: `vite build` in Docker
2. Docker rebuild: `docker compose build frontend && docker compose up -d frontend && docker compose restart nginx`
3. Visual check: screenshot each page
4. Commit + push for other machine
