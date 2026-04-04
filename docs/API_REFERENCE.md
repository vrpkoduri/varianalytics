# API Reference — Marsh Vantage

**Version:** 2.0 | **Last Updated:** 2026-04-04 | **Total Endpoints:** ~80

See PRODUCT_SPECIFICATION.md for full feature context.

---

## Gateway Service (Port 8000)

### Auth (7 endpoints)
- `POST /auth/login` — Email/password → JWT pair
- `POST /auth/login/azure-ad` — Azure AD OAuth exchange
- `POST /auth/register` — Create account (dev mode)
- `POST /auth/logout` — Revoke session
- `GET /auth/me` — Current user profile
- `POST /auth/refresh` — Refresh access token
- `GET /auth/azure-ad/config` — Azure AD config for frontend

### Chat (4) — Any authenticated
- `POST /chat/messages` — Send message → agent
- `GET /chat/stream/{id}` — SSE response stream
- `GET /chat/conversations` — List conversations
- `DELETE /chat/conversations/{id}` — Delete conversation

### Dimensions (4) — Any authenticated
- `GET /dimensions/hierarchies/{name}` — Hierarchy tree
- `GET /dimensions/business-units` — 5 BUs
- `GET /dimensions/accounts` — 38 accounts
- `GET /dimensions/periods` — 36 periods

### Config (3) — Read: any auth. Write: admin
- `GET /config/thresholds` — Read thresholds.yaml
- `PUT /config/thresholds` — Write thresholds.yaml (admin)
- `GET /config/model-routing` — Read model_routing.yaml

### Review (9) — Analyst/Admin
- `GET /review/queue?fiscal_year=2026` — FY-filterable queue
- `POST /review/actions` — Submit action (edit/approve/escalate/dismiss)
- `GET /review/stats` — Queue statistics
- `POST /review/lock/{id}` — Acquire 30-min edit lock
- `DELETE /review/lock/{id}` — Release lock
- `GET /review/lock/{id}` — Check lock status
- `GET /review/{id}/history` — Version history
- `POST /review/{id}/regenerate` — Regenerate parent from children (director+)

### Approval (3) — Director/CFO/Admin
- `GET /approval/queue` — Items pending approval
- `POST /approval/actions` — Bulk approve/reject
- `GET /approval/stats` — Approval statistics

### Admin (8) — Admin only
- `GET/POST/PUT/DELETE /admin/users` — User CRUD
- `POST/DELETE /admin/users/{id}/roles` — Role management
- `GET /admin/roles` — List system roles
- `GET /admin/audit-log` — Paginated audit log

### Notifications (3) — Admin only
- `POST /notifications/test` — Send test notification
- `GET/PUT /notifications/config` — Channel configuration

## Computation Service (Port 8001)

### Dashboard (8)
- `GET /dashboard/summary` — KPI cards
- `GET /dashboard/waterfall` — EBITDA bridge
- `GET /dashboard/heatmap` — BU × Geography matrix
- `GET /dashboard/trends` — 12-month trailing
- `GET /dashboard/alerts/netting` — Netting pairs
- `GET /dashboard/alerts/trends` — Trending alerts
- `GET /dashboard/section-narratives` — 5 P&L sections
- `GET /dashboard/executive-summary` — CFO headline + narrative

### Variances (3), Drilldown (4), P&L (2), Synthesis (2)
See full endpoint list in code: `services/computation/api/`

## Reports Service (Port 8002)
Reports (5), Scheduling (4), Distribution (3)
See: `services/reports/api/`

## Common Parameters
`period_id`, `base_id` (BUDGET/FORECAST/PRIOR_YEAR), `view_id` (MTD/QTD/YTD), `bu_id`, `page`, `page_size`, `fiscal_year`
