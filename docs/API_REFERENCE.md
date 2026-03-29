# API Reference — FP&A Variance Analysis Agent

**Version:** 1.0 | **Last Updated:** 2026-03-28 | **Total Endpoints:** 50

---

## Service 1: Gateway (Port 8000)

### Authentication — `/api/v1/auth`

| Method | Endpoint | Description | Sprint |
|--------|----------|-------------|--------|
| POST | `/login` | Authenticate user, return JWT | Sprint 5 |
| POST | `/logout` | Invalidate session | Sprint 5 |
| GET | `/me` | Get current user profile + persona | Sprint 5 |
| POST | `/refresh` | Refresh JWT token | Sprint 5 |

### Chat — `/api/v1/chat`

| Method | Endpoint | Description | Sprint |
|--------|----------|-------------|--------|
| POST | `/messages` | Send chat message, returns conversation_id | Sprint 1 |
| GET | `/stream/{conversation_id}` | SSE streaming response | Sprint 1 |
| GET | `/conversations` | List user conversations | Sprint 1 |
| DELETE | `/conversations/{conversation_id}` | Delete conversation | Sprint 1 |

### Dimensions — `/api/v1/dimensions`

| Method | Endpoint | Description | Sprint |
|--------|----------|-------------|--------|
| GET | `/hierarchies/{dimension_name}` | Get hierarchy tree (Geo, Segment, LOB, CC) | Sprint 1 |
| GET | `/business-units` | List all business units | Sprint 1 |
| GET | `/accounts` | Get account hierarchy | Sprint 1 |
| GET | `/periods` | List periods with status | Sprint 1 |

### Configuration — `/api/v1/config`

| Method | Endpoint | Description | Sprint |
|--------|----------|-------------|--------|
| GET | `/thresholds` | Get current threshold config | Sprint 5 |
| PUT | `/thresholds` | Update thresholds (admin) | Sprint 5 |
| GET | `/model-routing` | Get LLM model routing config | Sprint 5 |

### Review — `/api/v1/review`

| Method | Endpoint | Description | Sprint |
|--------|----------|-------------|--------|
| GET | `/queue` | Get review queue with filters | Sprint 1 |
| POST | `/actions` | Submit review action (confirm/edit/dismiss/escalate) | Sprint 1 |
| GET | `/stats` | Review queue statistics | Sprint 1 |

### Approval — `/api/v1/approval`

| Method | Endpoint | Description | Sprint |
|--------|----------|-------------|--------|
| GET | `/queue` | Get approval queue | Sprint 1 |
| POST | `/actions` | Bulk approve/hold/escalate | Sprint 1 |
| GET | `/stats` | Approval statistics | Sprint 1 |

### Notifications — `/api/v1/notifications`

| Method | Endpoint | Description | Sprint |
|--------|----------|-------------|--------|
| POST | `/test` | Send test notification | Sprint 4 |
| GET | `/config` | Get notification config | Sprint 4 |
| PUT | `/config` | Update notification config | Sprint 4 |

---

## Service 2: Computation (Port 8001)

### Dashboard — `/api/v1/dashboard`

| Method | Endpoint | Description | Sprint |
|--------|----------|-------------|--------|
| GET | `/summary` | Summary cards (Revenue, EBITDA, Costs, etc.) | Sprint 1 |
| GET | `/waterfall` | Waterfall chart data | Sprint 1 |
| GET | `/heatmap` | Variance heatmap data | Sprint 1 |
| GET | `/trends` | Trend chart data | Sprint 1 |

### Variances — `/api/v1/variances`

| Method | Endpoint | Description | Sprint |
|--------|----------|-------------|--------|
| GET | `/` | List material variances with filters | Sprint 1 |
| GET | `/{variance_id}` | Get single variance detail | Sprint 1 |
| GET | `/by-account/{account_id}` | Variances for an account | Sprint 1 |
| GET | `/by-bu/{bu_id}` | Variances for a BU | Sprint 1 |

### Drill-Down — `/api/v1/drilldown`

| Method | Endpoint | Description | Sprint |
|--------|----------|-------------|--------|
| GET | `/{node_id}` | Drill into hierarchy node | Sprint 2 |
| GET | `/decomposition/{variance_id}` | Get variance decomposition | Sprint 2 |
| GET | `/netting/{node_id}` | Get netting details for node | Sprint 2 |
| GET | `/correlations/{variance_id}` | Get correlated variances | Sprint 3 |

### P&L — `/api/v1/pl`

| Method | Endpoint | Description | Sprint |
|--------|----------|-------------|--------|
| GET | `/statement` | Full P&L with hierarchy | Sprint 1 |
| GET | `/account/{account_id}/detail` | Account detail view | Sprint 2 |

### Synthesis — `/api/v1/synthesis`

| Method | Endpoint | Description | Sprint |
|--------|----------|-------------|--------|
| POST | `/trigger/{variance_id}` | Trigger narrative synthesis | Sprint 3 |
| GET | `/status/{variance_id}` | Get synthesis status | Sprint 3 |

---

## Service 3: Reports (Port 8002)

### Reports — `/api/v1/reports`

| Method | Endpoint | Description | Sprint |
|--------|----------|-------------|--------|
| POST | `/generate` | Trigger report generation | Sprint 4 |
| GET | `/status/{job_id}` | Check generation status | Sprint 4 |
| GET | `/download/{job_id}` | Download generated report | Sprint 4 |
| GET | `/templates` | List available templates | Sprint 4 |
| GET | `/history` | Past generated reports | Sprint 4 |

### Scheduling — `/api/v1/scheduling`

| Method | Endpoint | Description | Sprint |
|--------|----------|-------------|--------|
| GET | `/schedules` | List report schedules | Sprint 4 |
| POST | `/schedules` | Create new schedule | Sprint 4 |
| PUT | `/schedules/{schedule_id}` | Update schedule | Sprint 4 |
| DELETE | `/schedules/{schedule_id}` | Delete schedule | Sprint 4 |

### Distribution — `/api/v1/distribution`

| Method | Endpoint | Description | Sprint |
|--------|----------|-------------|--------|
| POST | `/send` | Distribute report | Sprint 4 |
| GET | `/recipients` | List distribution lists | Sprint 4 |
| POST | `/recipients` | Create distribution list | Sprint 4 |

---

## Common Patterns

### Health Check
All services expose `GET /health` returning:
```json
{"status": "ok", "service": "<name>", "version": "0.1.0"}
```

### Error Responses
```json
{"error": "Not Found", "detail": "Variance abc123 not found", "code": "VARIANCE_NOT_FOUND"}
```

### Pagination
Query params: `page` (default 1), `page_size` (default 50, max 500)

### Filtering
Standard query params: `period_id`, `bu_id`, `account_id`, `geo_node_id`, `segment_node_id`, `lob_node_id`, `costcenter_node_id`, `view` (MTD/QTD/YTD), `base` (BUDGET/FORECAST/PRIOR_YEAR)

### SSE Event Types
```
event: token        data: {"text": "..."}
event: data_table   data: {"columns": [...], "rows": [...]}
event: mini_chart   data: {"type": "waterfall", ...}
event: suggestion   data: {"text": "..."}
event: confidence   data: {"score": 0.85}
event: netting_alert data: {"node_id": "...", ...}
event: review_status data: {"status": "ANALYST_REVIEWED"}
event: done         data: {}
```
