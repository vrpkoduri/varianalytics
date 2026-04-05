# Roadmap — Marsh Vantage

**Version:** 2.0 | **Last Updated:** 2026-04-04

---

## Completed Work

### MVP (Sprints 0-6, Weeks 1-12) — COMPLETE

| Sprint | What | Tests |
|---|---|---|
| 0 | Synthetic data (49K rows), 5.5-pass engine, project scaffolding | 193 |
| 1 | Revenue vertical slice, 3 microservices, 120+ React components, SSE chat | 280 |
| 2 | Full P&L, workflow persistence, PostgreSQL dual-write | 593 |
| 3 | RAG pipeline, LLM narratives (4,373 Claude-generated), synthesis | 645 |
| 4 | Reports (XLSX/PDF/PPTX/DOCX), notifications, scheduling | 677 |
| 5 | Auth/RBAC (JWT + Azure AD), admin panel, full Docker stack | 826 |
| 6 | Edge case tests, performance benchmarks, Playwright E2E, UAT personas | 947 |

### Phase 2: Narrative Intelligence (2A-2H) — COMPLETE

| Phase | What | Tests |
|---|---|---|
| 2A | Deterministic IDs, narrative persistence, version history, FY review | 964 |
| 2B | Layered leaf→parent narratives, guardrails, confidence scoring | 964 |
| 2C | Section narratives + executive summary (5 sections, 12 periods) | 976 |
| 2D | Executive Summary landing page (CFO/Board) | 993 |
| 2E | Carry-forward (cross-period intelligence) | 1,005 |
| 2F | Workflow enhancement (locking, edit intent, on-demand regen) | 1,013 |
| 2G | Report integration (all 4 formats pull from narrative pyramid) | 1,021 |
| 2H | Seasonality awareness + FX narrative framing | 1,039 |

**Current state: 1,067 tests, 106,590 variance rows, 12 periods, all features working.**

### Phase 3: Intelligence Engine — IN PROGRESS

| Phase | What | Tests |
|---|---|---|
| 3A | Knowledge Graph (NetworkX) + data lineage edges | 1,139 |
| 3B | Engine separation (Process A vs B) + stage independence + cost estimator | 1,071 |
| 3C | Cascade regeneration (auto on edit, debounced, topological) | 1,072 |
| 3D | Admin Engine Control panel + background task queue | 1,089 |

---

## Planned Work

### Phase 3: Intelligence Engine (~16 weeks)

| Sprint | What | Effort |
|---|---|---|
| **3A** | Variance Knowledge Graph (NetworkX) + data lineage edges | 2 weeks |
| **3B** | Engine separation (Process A vs B) + stage independence | 2 weeks |
| **3C** | Cascade regeneration (auto on edit, debounced, topological) | 1 week |
| **3D** | Admin Engine Control panel + background task queue | 2 weeks |
| **3E** | Hot-reload + period-level storage + Redis cache | 1 week |
| **3F** | Quick intelligence: materiality, risk, projection, persistence | 2 weeks |
| **3G** | Core intelligence: pivot, peer, causal, multi-year, lead/lag, DBSCAN | 3 weeks |
| **3H** | Quality: coherence, anomaly, budget validation, STL, market, LLM scoring | 2 weeks |
| **3I** | Model routing + provider flexibility | 1 week |

### Phase 4: Production Deployment (~8 weeks)

| Sprint | What |
|---|---|
| **4A** | Databricks integration (replace synthetic with live data) |
| **4B** | CI/CD pipeline (GitHub Actions) |
| **4C** | Azure Container Apps + TLS/HTTPS + encryption |
| **4D** | Observability (OpenTelemetry, Prometheus, Grafana) |
| **4E** | Security hardening (token revocation, session management, WAF) |
| **4F** | Data governance (DR, GDPR, retention, backup) |
| **4G** | Load testing |

### Phase 5: ML Intelligence (~8 weeks)

| Sprint | What |
|---|---|
| **5A** | XGBoost root cause ranking (trained on analyst feedback) |
| **5B** | Random Forest predictive variance |
| **5C** | DBSCAN clustering enhancement |
| **5D** | Isolation Forest anomaly enhancement |
| **5E** | STL seasonal auto-detection |
| **5F** | ML model governance (versioning, registry, A/B testing) |

### Phase 6: Extended Platform (~12 weeks)

| Sprint | What |
|---|---|
| **6A-C** | Balance Sheet, Headcount, KPI agents |
| **6D-E** | Teams @mention integration, Excel add-in |
| **6F-G** | Multi-entity + intercompany, multi-step approval chains |
| **6H-L** | Collaborative comments, external API, global search, SSO, mobile |

---

## Dependencies

```
Phase 3 (Intelligence) → Phase 5 (ML trains on same graph)
Phase 3 (Engine separation) → Phase 4 (Production needs hot-reload)
Phase 4 (Databricks) → Phase 6 (BS/HC agents need real data)
Phase 5 (ML) ↔ Phase 6 (Extended) — can run in parallel
```
