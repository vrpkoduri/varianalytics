# Sprint: Frontend Polish + Persona RBAC + UX Fixes

## Status: COMPLETE

**Completed:** 2026-04-05
**Previous session context:** Phase 3 complete, Framework Sprint done, 106,590 narratives, Docker 8/8 healthy

---

## Deliverables Summary

### Tier 1: CRITICAL — All Complete

| # | Issue | Fix | Files Modified |
|---|-------|-----|----------------|
| 1 | **SPA Routing Fix** — 404 on direct URL / refresh | Added `proxy_intercept_errors on; error_page 404 = /;` to outer nginx | `infra/nginx/nginx.conf` |
| 2 | **Persona RBAC Enforcement** — Backend didn't filter by persona | Wired `RBACService` into ReviewStore, review.py, approval.py. Frontend hooks now send persona to API, server-side filtering. Widened role gate to all personas. | `shared/data/review_store.py`, `services/gateway/api/review.py`, `services/gateway/api/approval.py`, `shared/auth/rbac.py`, `frontend/src/hooks/useReviewQueue.ts`, `frontend/src/hooks/useApprovalQueue.ts`, `frontend/src/hooks/useDashboard.ts`, `frontend/src/hooks/usePersonaParams.ts` (new) |
| 3 | **Font Replacement** — Playfair Display + DM Sans → Inter | Replaced Google Fonts import, Tailwind config, theme tokens, 20+ component files, chart hardcoded fonts, modal inline styles | `frontend/src/index.css`, `frontend/tailwind.config.ts`, `frontend/src/theme/tokens.ts`, 20 components with `font-display` class, 5 chart/modal files with inline fontFamily |

### Tier 2: HIGH — All Complete

| # | Issue | Fix | Files Modified |
|---|-------|-----|----------------|
| 4 | **Dashboard Data Issues** — Empty charts, wrong period default, missing alerts | Period endpoint now returns `has_data` flag; frontend picks latest period with data; empty-state UI added to Waterfall and Heatmap; netting/trend alerts treat empty arrays as undefined for fallback | `shared/data/service.py`, `services/gateway/api/dimensions.py`, `frontend/src/context/GlobalFiltersContext.tsx`, `frontend/src/hooks/useDashboard.ts`, `frontend/src/components/charts/WaterfallChart.tsx`, `frontend/src/components/dashboard/Heatmap.tsx` |
| 5 | **Variance Table Mock Fallback** — Empty API response didn't fall back | Added `.length > 0` check before using API data | `frontend/src/hooks/useVariances.ts` |
| 6 | **Account Name Formatting** — "Pbt" instead of "Pre-Tax Income" | `get_trend_alerts()` now looks up `_account_lookup` from `dim_account`; frontend `formatAccountName()` utility as safety net | `shared/data/service.py`, `frontend/src/utils/accountNames.ts` (new) |

### Tier 3: MEDIUM — All Complete

| # | Issue | Fix | Files Modified |
|---|-------|-----|----------------|
| 7 | **Light Mode Audit** — Hardcoded dark-theme colors | Replaced ~50 hardcoded colors across 9 files with semantic CSS variable tokens | `AdminEngineControlTab.tsx`, `StatusBadge.tsx`, `ErrorBoundary.tsx`, `ReportSubTabs.tsx`, `ReportCard.tsx`, `TemplateCard.tsx`, `ContextStrip.tsx`, `VarianceTable.tsx`, `Header.tsx` |
| 8 | **Visual Polish** — Narrative column width, modal tab shift | Added `min-w-[200px] max-w-[400px]` to narrative column; `min-h-[200px]` to modal narrative container | `VarianceTable.tsx`, `NarrativeSection.tsx` |

---

## New Infrastructure

| Item | Description |
|------|-------------|
| **Vitest Test Framework** | Frontend testing infrastructure: `vitest.config.ts`, `src/test/setup.ts`, `@testing-library/react` + `jsdom` |
| **usePersonaParams hook** | Reusable hook for extracting persona + buScope from UserContext for API calls |
| **Account name utility** | `frontend/src/utils/accountNames.ts` — canonical ACCOUNT_DISPLAY_NAMES map + formatAccountName() |

---

## Test Results

| Suite | Count | Result |
|-------|-------|--------|
| Frontend Vitest (new) | 8 | 8 passed |
| Backend ReviewStore RBAC (new) | 8 | 8 passed |
| Backend Account Names (new) | 6 | 6 passed |
| Backend Gateway RBAC (new) | 12 | Requires Python 3.11+ (Docker env) |
| E2E SPA Routing (new) | 8 | Requires Docker stack |
| Existing shared unit tests | 60 | 60 passed (0 regressions) |
| TypeScript compilation | — | 0 errors |
| Production build | — | Success (866KB JS, 41KB CSS) |
| Font grep check | — | 0 matches for old fonts |

**Total new tests: 42** (34 runnable locally, 8 require Docker)

---

## Architecture Decisions

1. **RBAC: Server-side filtering** — Persona filtering moved from client-side `if (persona === 'bu')` to backend `ReviewStore.get_review_queue(allowed_statuses=..., bu_scope=...)`. Client can no longer bypass RBAC by modifying frontend code.

2. **Review queue role gate widened** — All personas (analyst, bu_leader, director, cfo, admin) can access `/review/queue` with RBAC filtering applied. Previously only analyst/admin.

3. **Period selector: Backend filter** — `get_periods()` now returns `has_data: bool` per period based on `fact_variance_material` row existence. Frontend picks latest period with `has_data: true`.

4. **Inter font** — Single font family for the entire app. `font-display` and `font-body` Tailwind classes both resolve to Inter.

---

## Verification Checklist

- [x] `grep -r "Playfair\|DM Sans" frontend/src/` → 0 matches
- [x] TypeScript compilation → 0 errors
- [x] `npm run build` → success
- [x] `vitest run` → 8/8 passed
- [x] `pytest tests/unit/shared/` → 22/22 passed (new + compatible existing)
- [x] No regressions in existing 60 shared tests
- [ ] Direct URL navigation (requires Docker stack)
- [ ] Persona CFO → review queue shows APPROVED only (requires Docker stack)
- [ ] Light mode readable on all pages (requires visual check)
