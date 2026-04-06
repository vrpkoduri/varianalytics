# Sprint: LLM Health & Narrative Quality Monitoring

## Context

The app generates narratives via two paths: **LLM** (AI-generated, rich, context-aware) and **template** (deterministic, pattern-based). When the LLM API key is missing, misconfigured, or the endpoint is unreachable, the engine silently falls back to templates. There's currently no visibility into which path was used, whether the LLM is healthy, or what quality of narratives users are seeing.

**Goal:** Full monitoring dashboard + API validation + alerting so operators and admins always know the LLM health status and narrative quality.

---

## What Already Exists

| Component | Location | What It Does |
|-----------|----------|-------------|
| `narrative_source` column | `fact_variance_material` | Per-variance: `"llm"` or `"template"` |
| `llm_count` / `template_count` | `pass5_narrative.py` | Engine logs LLM vs template counts per run |
| `audit_log` table | `data/output/audit_log.parquet` | Records engine runs with method field |
| `commentary_pct` metric | `get_success_metrics()` | % of non-template narratives (already in API) |
| `LLMClient.is_available` | `shared/llm/client.py` | Boolean: is any API key configured |
| `model_routing.yaml` | `shared/config/` | Active provider + model per task |
| Admin page | `frontend/src/views/AdminView.tsx` | 5 tabs (Engine Control, Thresholds, Model Routing, Users & Roles, Audit Log) |

---

## What We're Building

### 1. Backend: LLM Health API

**New endpoint:** `GET /api/v1/admin/llm-health`

Returns:
```json
{
  "status": "healthy | degraded | unavailable",
  "provider": "azure",
  "models": {
    "chat_intent": { "model": "mmc-tech-gpt-4o-mini-...", "status": "ok", "latency_ms": 230 },
    "chat_response": { "model": "mmc-tech-gpt-4o-...", "status": "ok", "latency_ms": 450 },
    "narrative_generation": { "model": "mmc-tech-gpt-4o-...", "status": "ok", "latency_ms": 380 }
  },
  "last_check": "2026-04-06T21:30:00Z",
  "endpoint": "https://stg1.mmc-dallas-int-non-prod-ingress.mgti.mmc.com/...",
  "api_key_configured": true,
  "app_id_configured": true
}
```

**Implementation:**
- File: `services/gateway/api/admin.py` — new endpoint
- Sends a minimal test prompt to each configured model
- Measures latency
- Returns structured health status
- Caches result for 5 minutes (no need to test on every call)

### 2. Backend: Narrative Quality API

**New endpoint:** `GET /api/v1/admin/narrative-quality`

Returns:
```json
{
  "current_period": "2026-06",
  "total_material_variances": 846,
  "narrative_breakdown": {
    "llm_generated": 0,
    "template_generated": 846,
    "no_narrative": 0,
    "llm_pct": 0.0,
    "template_pct": 100.0
  },
  "by_level": {
    "detail": { "populated": 846, "empty": 0 },
    "midlevel": { "populated": 0, "empty": 846 },
    "summary": { "populated": 846, "empty": 0 },
    "oneliner": { "populated": 846, "empty": 0 },
    "board": { "populated": 0, "empty": 846 }
  },
  "last_engine_run": {
    "run_id": "8e66b9e9-...",
    "timestamp": "2026-04-06T21:28:55Z",
    "method": "template",
    "llm_count": 0,
    "template_count": 10695,
    "duration_seconds": 78.2
  },
  "history": [
    { "run_id": "...", "timestamp": "...", "llm_pct": 0.0, "total": 10695 },
    { "run_id": "...", "timestamp": "...", "llm_pct": 85.0, "total": 10695 }
  ]
}
```

**Implementation:**
- File: `shared/data/service.py` — new `get_narrative_quality()` method
- Reads `narrative_source` column from `fact_variance_material`
- Reads audit_log for engine run history
- Checks each narrative level for population

### 3. Backend: LLM Connectivity Test

**New endpoint:** `POST /api/v1/admin/llm-test`

Sends a test prompt and returns the response:
```json
{
  "success": true,
  "provider": "azure",
  "model": "mmc-tech-gpt-4o-mini-128k-2024-07-18",
  "response": "Test successful. I can generate financial narratives.",
  "latency_ms": 280,
  "tokens": { "prompt": 25, "completion": 12, "total": 37 }
}
```

**Implementation:**
- File: `services/gateway/api/admin.py`
- Sends a simple financial prompt: "Summarize: Revenue increased $50K (5%) vs Budget."
- Returns raw response + latency + token usage
- Button in Admin UI triggers this

### 4. Frontend: Admin LLM Monitoring Tab

**New component:** `AdminLLMMonitoringTab`

**Layout:**
```
┌─────────────────────────────────────────────────────┐
│  LLM STATUS                          [Test Now]     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐            │
│  │ Provider │ │ Status   │ │ Endpoint │            │
│  │ Azure    │ │ ● Healthy│ │ mmc-...  │            │
│  └──────────┘ └──────────┘ └──────────┘            │
├─────────────────────────────────────────────────────┤
│  NARRATIVE QUALITY                                  │
│  ┌─────────────────────────────────────┐            │
│  │  ██████████████████░░░  85% LLM     │  ← Bar    │
│  │  ████░░░░░░░░░░░░░░░░  15% Template │            │
│  └─────────────────────────────────────┘            │
│                                                     │
│  By Level:                                          │
│  Detail:    846/846 (100%)  ████████████            │
│  Midlevel:  720/846 (85%)   █████████░░            │
│  Summary:   846/846 (100%)  ████████████            │
│  Oneliner:  846/846 (100%)  ████████████            │
│  Board:       0/846 (0%)    ░░░░░░░░░░░            │
├─────────────────────────────────────────────────────┤
│  MODEL ROUTING                                      │
│  Task              │ Model                │ Latency │
│  chat_intent       │ gpt-4o-mini          │ 230ms   │
│  chat_response     │ gpt-4o               │ 450ms   │
│  narrative_gen     │ gpt-4o               │ 380ms   │
│  hypothesis_gen    │ gpt-4o               │ 340ms   │
│  oneliner_gen      │ gpt-4o-mini          │ 180ms   │
├─────────────────────────────────────────────────────┤
│  ENGINE RUN HISTORY                                 │
│  Run ID    │ Time         │ LLM% │ Total │ Duration│
│  8e66b...  │ Apr 6 21:28  │  0%  │ 10695 │ 78s     │
│  a3f21...  │ Apr 5 18:15  │ 85%  │ 10695 │ 240s    │
└─────────────────────────────────────────────────────┘
```

**Implementation:**
- File: `frontend/src/components/admin/AdminLLMMonitoringTab.tsx` (NEW)
- Add to AdminView.tsx as 6th tab: "AI Monitoring"
- Uses glass-card styling consistent with existing admin tabs
- "Test Now" button triggers `POST /admin/llm-test`
- Auto-refreshes health status every 60 seconds

### 5. Success Metrics Bar Integration

**Update:** `SuccessMetricsBar` to show LLM indicator

- Add a 5th metric: **AI SOURCE** — shows "LLM" (green) or "Template" (amber)
- Uses the `commentary_pct` from `get_success_metrics()` API
- Tooltip shows: "85% of narratives generated by AI, 15% template fallback"

### 6. Notification: LLM Fallback Alert

**When engine runs with 0 LLM narratives:**
- Log warning: "Engine run completed with 0 LLM narratives — all template fallback"
- If notification webhooks configured: send Teams/Slack alert
- Admin UI: show banner at top of dashboard "Narratives generated from templates — AI not connected"

**Implementation:**
- File: `services/computation/engine/pass5_narrative.py` — add fallback detection
- File: `services/gateway/notifications/` — send webhook on fallback
- File: `frontend/src/components/layout/Header.tsx` — show warning banner

---

## Shared Components

| Component | Location | Purpose |
|-----------|----------|---------|
| `get_narrative_quality()` | `shared/data/service.py` | Reusable quality metrics |
| `LLMHealthChecker` | `shared/llm/health.py` (NEW) | Centralized health check logic |
| `AdminLLMMonitoringTab` | `frontend/src/components/admin/` (NEW) | Admin UI tab |
| `LLMStatusBadge` | `frontend/src/components/common/` (NEW) | Reusable status indicator |

---

## Build Chunks

### Chunk 1: Backend APIs (no frontend)
- `GET /admin/llm-health` — provider status + model latency
- `GET /admin/narrative-quality` — source breakdown + level population
- `POST /admin/llm-test` — connectivity test with sample prompt
- `shared/llm/health.py` — centralized health check class

### Chunk 2: Admin LLM Monitoring Tab
- New component: `AdminLLMMonitoringTab`
- Add as 6th tab in AdminView
- Wire to 3 new APIs
- "Test Now" button

### Chunk 3: Dashboard Integration
- Update SuccessMetricsBar with AI source indicator
- Add template fallback banner to Header
- Wire to narrative quality API

### Chunk 4: Alerting
- Engine fallback detection in pass5_narrative
- Teams/Slack webhook notification
- Audit log entry for LLM status

### Chunk 5: Tests + Documentation
- Unit tests: health check, quality metrics, API endpoints
- Integration tests: full LLM → narrative → quality pipeline
- E2E: Admin tab renders, test button works
- Update TESTING_FRAMEWORK.md

---

## Test Plan

| File | Type | Count | What |
|------|------|-------|------|
| `tests/unit/shared/test_llm_health.py` | pytest | 6 | Health check logic, caching, timeout |
| `tests/unit/shared/test_narrative_quality.py` | pytest | 5 | Source breakdown, level population |
| `tests/unit/gateway/test_admin_llm_api.py` | pytest | 8 | All 3 endpoints, error handling |
| `frontend/src/components/admin/__tests__/LLMMonitoring.test.tsx` | Vitest | 4 | Tab rendering, test button |
| **Total** | | **~23** | |

---

## Estimated Effort

| Chunk | Effort | Dependencies |
|-------|--------|-------------|
| Chunk 1: Backend APIs | 2-3 hours | None |
| Chunk 2: Admin Tab | 2-3 hours | Chunk 1 |
| Chunk 3: Dashboard | 1-2 hours | Chunk 1 |
| Chunk 4: Alerting | 1-2 hours | Chunk 1 |
| Chunk 5: Tests + Docs | 2-3 hours | All |
| **Total** | **8-13 hours** | |

---

## Decision Points

1. **Health check frequency:** Auto-check every 60s, or only on demand (button click)?
2. **Template fallback banner:** Show on dashboard for all users, or admin-only?
3. **Engine re-run trigger:** Should the admin tab have a "Re-run Engine with LLM" button?
