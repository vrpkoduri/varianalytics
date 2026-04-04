# Testing Framework — Marsh Vantage

**Version:** 2.0 | **Last Updated:** 2026-04-04 | **Total Tests:** 1,067

---

## Overview

This document defines the testing strategy, tools, conventions, and execution instructions for the Variance Analysis Agent. Tests are organized by type and scope, with a consolidated structure under `tests/`.

---

## Test Structure

```
tests/
├── conftest.py                      # Shared fixtures (hierarchies, sample data, config)
├── pytest.ini                       # Pytest configuration + markers
├── unit/                            # Fast, isolated, no external deps
│   ├── shared/
│   │   ├── test_hierarchy.py        # Tree traversal, rollup paths, leaf nodes
│   │   ├── test_models.py           # Pydantic schema validation
│   │   └── test_formatting.py       # Currency, percentage, variance formatters
│   ├── computation/
│   │   ├── test_pass1_variance.py   # Raw variance calculation
│   │   ├── test_pass15_netting.py   # Netting detection checks
│   │   ├── test_pass2_threshold.py  # Threshold filtering
│   │   ├── test_pass25_trend.py     # Trend detection rules
│   │   ├── test_pass3_decomp.py     # Decomposition methods
│   │   └── test_calculated_rows.py  # EBITDA, Gross Profit, etc.
│   ├── gateway/
│   │   ├── test_chat.py             # Chat message processing
│   │   └── test_review.py           # Review/approval logic
│   └── reports/
│       ├── test_xlsx_generator.py   # Excel generation
│       └── test_pdf_generator.py    # PDF generation
├── integration/
│   ├── test_engine_pipeline.py      # Full 5.5-pass pipeline
│   ├── test_synthetic_data.py       # Data generation + validation
│   ├── test_api_endpoints.py        # FastAPI endpoint testing
│   └── test_service_communication.py # Cross-service calls
├── e2e/
│   ├── test_revenue_flow.py         # Revenue variance end-to-end
│   ├── test_review_workflow.py      # AI_DRAFT → APPROVED flow
│   └── test_report_generation.py    # Generate + export flow
└── performance/
    ├── test_engine_timing.py        # Engine within 5-min budget
    └── test_api_latency.py          # API <100ms p95
```

---

## Test Categories

### 1. Unit Tests (`tests/unit/`)
- **Scope:** Single function/class, no I/O, no network
- **Speed:** <100ms each
- **Marker:** `@pytest.mark.unit`
- **When to run:** Every code change, pre-commit
- **Coverage target:** >80%

### 2. Integration Tests (`tests/integration/`)
- **Scope:** Multiple components, may use file I/O, mock services
- **Speed:** <10s each
- **Marker:** `@pytest.mark.integration`
- **When to run:** Before merge, CI pipeline
- **Coverage target:** Key data flows covered

### 3. End-to-End Tests (`tests/e2e/`)
- **Scope:** Full user journey through UI + API + engine
- **Speed:** <60s each
- **Marker:** `@pytest.mark.e2e`
- **When to run:** Before release, nightly CI
- **Tool:** Playwright (browser automation)

### 4. Performance Tests (`tests/performance/`)
- **Scope:** Timing and throughput
- **Marker:** `@pytest.mark.slow`
- **When to run:** Weekly, before release

### 5. Regression Tests
- Added to unit/integration as bugs are found
- Each bug fix accompanied by a test that would have caught it

---

## Tools

| Tool | Purpose |
|------|---------|
| **pytest** | Test runner, fixtures, markers |
| **pytest-cov** | Coverage reporting |
| **pytest-asyncio** | Async test support (FastAPI) |
| **httpx** | Async HTTP client for API tests |
| **pytest-mock** | Mocking library |
| **Playwright** | Browser E2E testing |
| **factory-boy** | Test data factories (Phase 2) |

---

## Running Tests

```bash
# All unit tests
pytest tests/ -m unit

# All tests (unit + integration)
pytest tests/ -m "unit or integration"

# Specific test file
pytest tests/unit/shared/test_hierarchy.py

# With coverage
pytest tests/ -m unit --cov=shared --cov-report=html

# Only fast tests (exclude slow/e2e)
pytest tests/ -m "not slow and not e2e"

# Verbose with full output
pytest tests/ -v --tb=long
```

---

## Fixtures (tests/conftest.py)

### Hierarchy Fixtures
- `sample_geo_tree_data` — Minimal geo hierarchy dict
- `sample_geo_tree` — Built HierarchyNode tree
- `sample_account_tree_data` — Minimal account hierarchy with calculated rows
- `sample_account_tree` — Built account HierarchyNode tree

### Data Fixtures
- `synthetic_data_spec_path` — Path to spec JSON
- `synthetic_data_spec` — Loaded spec dict

### Service Fixtures (added per sprint)
- `test_client_gateway` — FastAPI TestClient for gateway
- `test_client_computation` — FastAPI TestClient for computation
- `sample_fact_financials` — Sample fact data DataFrame
- `sample_variance_material` — Sample material variance data

---

## Conventions

1. **Naming:** `test_<module>_<function>_<scenario>` or class-based `TestClassName`
2. **One assertion per test** when practical
3. **Docstrings** on all test classes and complex test functions
4. **Fixtures over setup/teardown** — Prefer pytest fixtures
5. **No test interdependencies** — Each test runs in isolation
6. **Deterministic** — Use fixed seeds, mock time, avoid flaky tests
7. **Mark appropriately** — Every test gets `@pytest.mark.unit/integration/e2e`

---

## CI Integration (Future)

```yaml
# GitHub Actions (planned)
jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install -r shared/requirements.txt
      - run: pytest tests/ -m unit --cov=shared

  integration-tests:
    runs-on: ubuntu-latest
    services:
      redis:
        image: redis:7-alpine
    steps:
      - run: pytest tests/ -m integration

  e2e-tests:
    runs-on: ubuntu-latest
    steps:
      - run: docker compose -f infra/docker-compose.yml up -d
      - run: pytest tests/ -m e2e
```

---

## Adding New Tests

When adding a feature or fixing a bug:

1. Write the test first (TDD when practical)
2. Place in the correct directory (unit/integration/e2e)
3. Add appropriate marker
4. Use shared fixtures from conftest.py
5. Run the full test suite before pushing
6. Update this document if adding a new test category or tool

---

## Filter & Interaction Test Matrix

### Dashboard Filter Scenarios
| Scenario | BU Filter | View Filter | Base Filter | Expected Behavior |
|----------|-----------|------------|-------------|-------------------|
| Default (no filters) | All | MTD | BUDGET | Full dataset, all BUs |
| Single BU | Marsh | MTD | BUDGET | Marsh-only KPIs, variances, heatmap |
| View switch | All | QTD | BUDGET | Quarterly totals (>= MTD) |
| Base switch | All | MTD | FORECAST | Forecast comparators |
| Combined | Marsh | QTD | BUDGET | Marsh quarterly data |
| Combined | Mercer | YTD | PRIOR_YEAR | Mercer YTD vs PY |
| Reset | All | MTD | BUDGET | Returns to default |

### Cross-Page Filter Persistence
| Action | Dashboard | P&L | Chat | Review | Approval |
|--------|-----------|-----|------|--------|----------|
| Select BU Marsh | Filters | Filters | In context | Client | Client |
| Switch to QTD | Refetch | Refetch | In context | N/A | N/A |
| Switch to Forecast | Refetch | Refetch | In context | N/A | N/A |

### Interaction Test Checklist
- [ ] BU click -> all dashboard sections filter
- [ ] BU click -> P&L page filters when navigated
- [ ] View toggle -> all endpoints refetch
- [ ] Base toggle -> all endpoints refetch
- [ ] Persona switch -> chat clears, variances filter
- [ ] Heatmap cell click -> variance table filters
- [ ] Variance table search -> filters rows
- [ ] Variance table sort -> reorders rows
- [ ] Variance row click -> modal opens
- [ ] P&L expand/collapse -> works with real data
- [ ] P&L leaf click -> modal opens
- [ ] Chat send -> response streams
- [ ] Review confirm -> status changes + confetti
- [ ] Approval approve -> report gate updates + confetti
- [ ] Geography tree expand -> shows real nodes
- [ ] Geography node click -> dimension filter banner

### Regression Test Commands
```bash
# Full test suite (all tests)
PYTHONPATH=. pytest tests/ -q

# Filter-specific E2E tests
PYTHONPATH=. pytest tests/e2e/test_filter_scenarios.py -v

# API contract tests
PYTHONPATH=. pytest tests/unit/test_api_contracts.py -v

# Interaction wiring tests
PYTHONPATH=. pytest tests/integration/test_interaction_wiring.py -v

# Frontend API integration
PYTHONPATH=. pytest tests/integration/test_frontend_api.py -v

# Filter validation integration
PYTHONPATH=. pytest tests/integration/test_filter_validation.py -v
```

## Sprint 1+2 Comprehensive Regression Test Suite

### Test Suites (5 categories, ~44 tests)

| Suite | File | Tests | What It Validates |
|-------|------|-------|-------------------|
| Cross-Service | `tests/integration/test_cross_service.py` | 10 | Gateway + computation work together |
| Workflow | `tests/integration/test_workflow_roundtrip.py` | 8 | Full analyst -> director lifecycle |
| Pipeline | `tests/integration/test_data_pipeline_integrity.py` | 12 | Mathematical correctness of calculations |
| Scenarios | `tests/integration/test_scenario_validation.py` | 6 | 4 deliberate variance scenarios surface |
| Regression | `tests/integration/test_persona_regression.py` | 8 | Persona filters, field contracts |

### Run Commands

```bash
# Individual suites
PYTHONPATH=. pytest tests/integration/test_cross_service.py -v
PYTHONPATH=. pytest tests/integration/test_workflow_roundtrip.py -v
PYTHONPATH=. pytest tests/integration/test_data_pipeline_integrity.py -v
PYTHONPATH=. pytest tests/integration/test_scenario_validation.py -v
PYTHONPATH=. pytest tests/integration/test_persona_regression.py -v

# All integration tests
PYTHONPATH=. pytest tests/integration/ -v

# Full regression (all ~595 tests)
PYTHONPATH=. pytest tests/ -q

# Quick smoke test (cross-service only)
PYTHONPATH=. pytest tests/integration/test_cross_service.py -v --tb=short
```

### When to Run

| Event | Command |
|-------|---------|
| After any backend change | `pytest tests/integration/ -q` |
| After any frontend API change | `pytest tests/integration/test_cross_service.py -v` |
| After engine re-run | `pytest tests/integration/test_data_pipeline_integrity.py -v` |
| Before Sprint release | `pytest tests/ -q` (full regression) |
| After filter changes | `pytest tests/e2e/test_filter_scenarios.py -v` |

## Sprint 5 Auth & RBAC Test Suite

### Test Suites (6 categories, ~139 new tests)

| Suite | File | Tests | What It Validates |
|-------|------|-------|-------------------|
| JWT | `tests/unit/shared/test_jwt.py` | 15 | Token create/validate/expire/refresh |
| RBAC | `tests/unit/shared/test_rbac.py` | 23 | Persona mapping, BU scope, variance filtering |
| UserStore | `tests/unit/shared/test_user_store.py` | 23 | User CRUD, role assign/remove, password verify |
| Auth Endpoints | `tests/unit/gateway/test_auth_endpoints.py` | 12 | Login/logout/refresh/register/me |
| Admin API | `tests/unit/gateway/test_admin_api.py` | 10 | User/role CRUD, audit log, admin-only access |
| Auth Middleware | `tests/integration/test_auth_middleware.py` | 18 | JWT validation, role checks, dev fallback |
| RBAC Enforcement | `tests/integration/test_rbac_enforcement.py` | 21 | Endpoint protection per role |
| Persona Data Access | `tests/integration/test_persona_data_access.py` | 17 | CFO/BU Leader/Board data isolation |

### Run Commands

```bash
# Sprint 5 unit tests only
PYTHONPATH=. pytest tests/unit/shared/test_jwt.py tests/unit/shared/test_rbac.py tests/unit/shared/test_user_store.py tests/unit/gateway/test_auth_endpoints.py tests/unit/gateway/test_admin_api.py -v

# Sprint 5 integration tests only
PYTHONPATH=. pytest tests/integration/test_auth_middleware.py tests/integration/test_rbac_enforcement.py tests/integration/test_persona_data_access.py -v

# Full regression (all ~816 tests)
PYTHONPATH=. pytest tests/ -q

# Quick auth smoke test
PYTHONPATH=. pytest tests/unit/shared/test_jwt.py tests/integration/test_auth_middleware.py -v --tb=short
```

### When to Run (Auth-specific)

| Event | Command |
|-------|---------|
| After auth changes | `pytest tests/unit/shared/test_jwt.py tests/integration/test_auth_middleware.py -v` |
| After RBAC changes | `pytest tests/unit/shared/test_rbac.py tests/integration/test_rbac_enforcement.py -v` |
| After user store changes | `pytest tests/unit/shared/test_user_store.py tests/unit/gateway/test_admin_api.py -v` |
| After endpoint protection | `pytest tests/integration/test_rbac_enforcement.py -v` |

## Sprint 6 Testing + Hardening Suite

### Overview (121 new tests across 5 categories)

Sprint 6 added edge case validation, performance benchmarks, Playwright browser E2E, automated UAT persona scenarios, and config persistence tests.

### Test Suites

| Suite | File | Tests | What It Validates |
|-------|------|-------|-------------------|
| Edge Cases | `tests/unit/computation/test_edge_cases.py` | 20 | Budget=0, negative budgets, missing PY/FX, empty nodes, 4 scenarios |
| Config Thresholds | `tests/unit/shared/test_config_thresholds.py` | 21 | Resolution hierarchy, OR logic, netting/trend properties |
| Intent Agents | `tests/unit/gateway/test_agents.py` | 13 | Keyword intent classification, entity extraction |
| Config Persistence | `tests/unit/gateway/test_config_persistence.py` | 10 | YAML read/write for thresholds + model routing |
| Engine Timing | `tests/performance/test_engine_timing.py` | 6 | Full pipeline < 20s, per-pass SLAs |
| API Latency | `tests/performance/test_api_latency.py` | 8 | Dashboard < 200ms, P&L < 500ms, etc. |
| DB Performance | `tests/performance/test_db_performance.py` | 4 | User lookup < 50ms, role query < 50ms |
| Playwright Auth | `tests/e2e/browser/test_auth_journey.py` | 5 | Login/logout/redirect in real browser |
| Playwright Dashboard | `tests/e2e/browser/test_dashboard_journey.py` | 5 | KPI cards, navigation, section labels |
| Playwright Review | `tests/e2e/browser/test_review_journey.py` | 5 | Review/approval tab navigation |
| Playwright Chat | `tests/e2e/browser/test_chat_journey.py` | 3 | Chat page load, input area |
| Playwright Admin | `tests/e2e/browser/test_admin_journey.py` | 3 | Admin tabs, threshold editor |
| Persona UAT | `tests/e2e/test_persona_scenarios.py` | 18 | 6 personas × endpoint access/denial |

### Run Commands

```bash
# Edge case + coverage tests
PYTHONPATH=. pytest tests/unit/computation/test_edge_cases.py tests/unit/shared/test_config_thresholds.py tests/unit/gateway/test_agents.py tests/unit/gateway/test_config_persistence.py -v

# Performance benchmarks
PYTHONPATH=. pytest tests/performance/ -v

# Playwright browser E2E (requires Docker stack on port 80)
PYTHONPATH=. pytest tests/e2e/browser/ -v

# Persona UAT scenarios
PYTHONPATH=. pytest tests/e2e/test_persona_scenarios.py -v

# Full regression (non-browser, ~920 tests)
PYTHONPATH=. pytest tests/unit/ tests/integration/ tests/performance/ tests/e2e/test_filter_scenarios.py tests/e2e/test_persona_scenarios.py -q

# Full regression (all ~947 tests, requires Docker stack)
PYTHONPATH=. pytest tests/ -q
```

### Final Test Count

| Category | Tests |
|----------|-------|
| Unit (shared, computation, gateway, reports) | ~540 |
| Integration (cross-service, pipeline, auth, RBAC, LLM, RAG, Postgres) | ~240 |
| Performance (engine, API, DB) | 18 |
| E2E — API-level (filters, persona scenarios) | ~76 |
| E2E — Browser (Playwright auth, dashboard, review, chat, admin) | 21 |
| **TOTAL** | **~947** |
