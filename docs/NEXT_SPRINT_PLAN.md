# Next Sprint: Frontend Polish + Persona RBAC + UX Fixes

## Status: Plan needed — start in fresh session

## What Needs to Be Done (Prioritized)

### Tier 1: CRITICAL

**1. SPA Routing Fix**
- Exec Summary returns 404 on direct URL / browser refresh
- All client-side routes break on refresh because nginx doesn't have `try_files $uri /index.html`
- File: `infra/nginx/nginx.conf`
- Fix: Add SPA fallback for all routes

**2. Persona RBAC Enforcement**
- Backend endpoints don't filter by persona (review.py, approval.py)
- Frontend doesn't pass persona to API calls
- BU scope enforced client-side only (bypassable)
- CFO sees AI_DRAFT items (should only see APPROVED)
- BU Lead can access all BUs via API
- Narrative level filtering missing (CFO sees DETAIL, should only see SUMMARY)
- Files: `shared/auth/rbac.py` (maps exist), `services/gateway/api/review.py`, `services/gateway/api/approval.py`, `shared/data/review_store.py`, frontend hooks

**3. Font Replacement**
- Replace Playfair Display + DM Sans with **Inter** across entire app
- User confirmed: current fonts not readable/professional enough
- Files: `frontend/src/index.css`, `frontend/tailwind.config.ts`, all components using `font-display`

### Tier 2: HIGH

**4. Dashboard Data Issues**
- EBITDA Bridge chart empty (no bars)
- Variance Heatmap not rendering
- Close Progress donut shows mock data (7/7/6) instead of real counts
- Period selector defaults to Dec 2026 but LLM data is Jun 2026
- Netting alerts shows 0 pairs (should show data)

**5. Dashboard Variance Table Shows Mock Data**
- Mock statuses (Approved, Reviewed) mixed with real API data
- useVariances hook may fall back to mock incorrectly

**6. Account Name Formatting**
- Trend alerts show "Pbt" instead of "Pre-Tax Income"
- Netting alerts show raw account IDs

### Tier 3: MEDIUM

**7. Light Mode Audit**
- User reports many issues in light mode — full audit needed
- Toggle theme and check all pages

**8. Visual Polish**
- Consistent card spacing
- Narrative column width in tables
- Modal persona tab switching (Detail/Midlevel/Summary)

## Architecture Notes

### Persona → Status Mapping (from shared/auth/rbac.py)
```
Analyst:     AI_DRAFT, ANALYST_REVIEWED, APPROVED, ESCALATED, DISMISSED, AUTO_CLOSED
BU Leader:   ANALYST_REVIEWED, APPROVED
Director:    ANALYST_REVIEWED, APPROVED
CFO:         APPROVED only
Board:       APPROVED only
```

### Persona → Narrative Level Mapping
```
Analyst:     DETAIL, MIDLEVEL, SUMMARY, ONELINER
BU Leader:   MIDLEVEL, SUMMARY, ONELINER
Director:    MIDLEVEL, SUMMARY, ONELINER
CFO:         SUMMARY, ONELINER
Board:       BOARD, SUMMARY
```

### Files to Touch (~20+)
- `infra/nginx/nginx.conf` — SPA routing
- `frontend/src/index.css` — font imports
- `frontend/tailwind.config.ts` — font family definitions
- `frontend/src/context/UserContext.tsx` — persona validation
- `frontend/src/hooks/useReviewQueue.ts` — pass persona to API
- `frontend/src/hooks/useApprovalQueue.ts` — pass persona to API
- `frontend/src/hooks/useDashboard.ts` — persona filtering
- `services/gateway/api/review.py` — accept persona, apply RBAC
- `services/gateway/api/approval.py` — accept persona, apply RBAC
- `shared/data/review_store.py` — accept allowed_statuses + bu_scope
- Multiple frontend components for font updates
- Dashboard chart components for data flow fixes

## Test Plan
- Persona RBAC tests: 12+ (each persona × each endpoint)
- Routing tests: verify all 8 pages load on direct URL
- Font: visual verification
- Dashboard: chart data flow tests
- Light mode: visual audit

## Session Context
- Phase 3 (Intelligence Engine): COMPLETE (3A-3I all done)
- Framework Completion Sprint: DONE
- Engine Run: 47K LLM calls, 12 periods, 106,590 narratives
- All backend APIs now return narrative_detail
- Docker: 8/8 healthy
- Last commit: `e21dfe0`
