# Frontend Issues — Comprehensive Audit (April 2026)

## Status: Issues identified, fix plan needed

---

## CRITICAL ISSUES

### 1. Routing Broken — Exec Summary 404
- **Location:** Navigation bar "Exec Summary" button
- **Issue:** Clicking "Exec Summary" stays on Dashboard. Direct URL `/exec-summary` returns 404.
- **Root Cause:** Likely nginx config doesn't handle SPA routes, or React Router path mismatch
- **Impact:** Exec Summary page inaccessible via direct URL or browser refresh
- **Fix:** Check nginx.conf for SPA fallback (`try_files $uri /index.html`), verify React Router paths

### 2. Dashboard Shows Mock Data in Variance Table
- **Location:** Dashboard → Material Variances table
- **Issue:** Table shows mock statuses (Approved, Reviewed) that don't match actual data (all AI_DRAFT)
- **Root Cause:** `useVariances` hook may fall back to mock when API shape doesn't match expected
- **Impact:** Users see fake data mixed with real data
- **Fix:** Verify useVariances transform handles actual API response correctly

### 3. EBITDA Bridge Chart Empty
- **Location:** Dashboard → EBITDA Bridge card
- **Issue:** Chart shows Y-axis labels ($0K-$4K) but no bars
- **Root Cause:** Waterfall API may return data in unexpected format, or chart component not rendering
- **Impact:** Key visual missing from dashboard

### 4. Variance Heatmap Shows Only "BU" Header
- **Location:** Dashboard → Variance Heatmap section
- **Issue:** Only shows "BU" text, no actual heatmap grid
- **Root Cause:** Heatmap data not loading or component collapsed
- **Impact:** Key cross-BU comparison tool missing

---

## HIGH PRIORITY

### 5. Font Issues — Playfair Display Not Readable
- **User Feedback:** "I really dont like the font on cards and P&L page - not really readable or easy on eyes"
- **Location:** KPI cards, P&L numbers, modal big numbers
- **Issue:** Playfair Display (serif) used for numbers — user finds it hard to read
- **Recommendation:** Switch to a professional sans-serif number font:
  - Option A: Use DM Sans for everything (consistent, readable)
  - Option B: Use Inter or Roboto Mono for numbers (modern, professional)
  - Option C: Keep Playfair only for titles, DM Sans for numbers
- **Files:** `tailwind.config.ts:36` (font-display definition), `KPICard.tsx`, `index.css`

### 6. Period Selector Shows "Dec 2026" But Data is "Jun 2026"
- **Location:** Dashboard header → period selector
- **Issue:** Period selector shows "Dec 2026" but the executive summary says "June close"
- **Root Cause:** Period defaults may not match the data we generated (Jun 2026 was the LLM period)
- **Impact:** Confusing — user sees different periods in different parts of the page

### 7. Netting Alerts Shows "0 pairs" On Dashboard
- **Location:** Dashboard → Netting Alerts card
- **Issue:** Shows "0 pairs" — but we have 123 netting flags in the data
- **Root Cause:** Netting alerts API may be filtering to current period differently, or data not matching the selected period
- **Fix:** Verify netting alerts API endpoint with the correct period_id

### 8. Close Progress Shows "7 approved, 7 reviewed, 6 draft"
- **Location:** Dashboard sidebar → Close Progress donut
- **Issue:** Shows mock numbers (7/7/6 = 20 total) not actual data (106,590 AI_DRAFT)
- **Root Cause:** Close Progress uses mock data, not connected to review API
- **Fix:** Wire to actual review status counts

---

## MEDIUM PRIORITY

### 9. Trend Alerts Show "Pbt" Instead of "Pre-Tax Income"
- **Location:** Dashboard → Trend Alerts card
- **Issue:** Shows raw account ID abbreviation "Pbt" instead of human-readable "Pre-Tax Income"
- **Fix:** Map account IDs to display names in trend alerts

### 10. KPI Cards Missing Below Dashboard Header
- **Location:** Dashboard → between exec summary and netting alerts
- **Issue:** KPI cards ($938K, $389K, etc.) not visible in the current screenshot — may be scrolled past
- **Verify:** Check if KPI cards are rendering but above the fold

### 11. Light Mode Issues
- **User Feedback:** "I see many issues there [in light mode]"
- **Status:** Not yet reviewed — needs full light mode audit
- **Fix:** Toggle light mode and audit all pages

### 12. Approval Page Empty State
- **Status:** ✅ FIXED — now shows "No items pending approval" message
- **Previously:** Showed mock data with "cached/backend unavailable" banner

### 13. Review Queue Shows Template Narratives for Older Periods
- **Location:** Review Queue → items from Jul-Mar (template periods)
- **Issue:** Items show basic template oneliners ("$18 decreased") instead of rich narratives
- **Root Cause:** Only Apr-Jun 2026 have LLM narratives; older periods are template-generated
- **This is expected behavior** — but the quality difference is noticeable

### 14. Reports Page Nearly Empty
- **Status:** ✅ FIXED — now shows empty state message
- **Previously:** Showed blank page

---

## ALREADY FIXED (Recent Commits)

| Issue | Fix | Commit |
|-------|-----|--------|
| Review Queue narrative_detail missing | Added to Pydantic model + review_store | `5f43a3b` |
| Approval page mock fallback | Empty state instead of mock | `98f3678` |
| Dashboard variance table narrative | Added narrativeDetail to transformer | `e30f044` |
| P&L narrative data flow | Added to service.py + transformer | `6705a5b` |
| Summary cards narrative | Added narrative_oneliner | `6705a5b` |
| KPI font (Playfair) | Added font-display class | `e30f044` |
| Reports empty state | Added message | `e30f044` |
| Trend alerts duplicate "projected" | Smart text detection | `e30f044` |

---

## NEXT STEPS

1. **Fix routing** — Critical: SPA route handling for all pages
2. **Font decision** — Get user approval on replacement font
3. **Fix EBITDA Bridge + Heatmap** — Chart data flow
4. **Wire Close Progress** — Connect to real review data
5. **Light mode audit** — Full review needed
6. **Period selector default** — Should match latest data period
