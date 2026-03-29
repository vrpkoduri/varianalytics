# Architecture — FP&A Variance Analysis Agent

**Version:** 1.0 | **Last Updated:** 2026-03-28

---

## System Overview

```
┌─────────────┐     ┌──────────────────────────────────────────────────┐
│   Frontend   │────▶│                    Nginx (80)                    │
│  React + TS  │     │  /api/v1/gateway/*  /api/v1/compute/*  /reports │
│  Vite (3000) │     └──────┬──────────────────┬──────────────┬────────┘
└─────────────┘            │                  │              │
                    ┌──────▼──────┐    ┌──────▼──────┐ ┌─────▼─────┐
                    │   Gateway   │    │ Computation  │ │  Reports  │
                    │   (8000)    │    │   (8001)     │ │  (8002)   │
                    │ Auth, Chat  │    │ 5.5-Pass     │ │ PDF, PPTX │
                    │ Review/Appr │    │ Engine       │ │ XLSX, DOCX│
                    │ Dimensions  │    │ Dashboard    │ │ Scheduling│
                    └──────┬──────┘    └──────┬───────┘ └─────┬─────┘
                           │                  │               │
                    ┌──────▼──────────────────▼───────────────▼──────┐
                    │              Redis (6379)                       │
                    │        Cache + Pub/Sub + Session                │
                    └────────────────────────────────────────────────┘
                           │
                    ┌──────▼──────────────────────────────────┐
                    │          Data Layer                      │
                    │  MVP: Parquet/CSV in data/output/        │
                    │  Prod: Databricks Unity Catalog          │
                    └─────────────────────────────────────────┘
```

---

## Architecture Decision Records

### ADR-001: Microservice Boundaries

**Decision:** 3 services (Gateway, Computation, Reports) rather than monolith.

**Rationale:**
- Computation is CPU-intensive; isolate scaling
- Reports generate large files; separate memory profile
- Gateway handles real-time chat/SSE; different latency requirements
- Clear team ownership boundaries for future growth

**Trade-offs:**
- More operational complexity vs. monolith
- Inter-service communication overhead
- Mitigated by: shared library, Docker Compose for local dev

### ADR-002: LLM-Thin Agent Design

**Decision:** LLM handles only intent classification and NL generation. All computation, routing, data access, and threshold logic is deterministic code.

**Rationale:**
- Predictable, testable computation pipeline
- LLM costs controlled (50–200 calls per engine run, not thousands)
- No hallucination risk in financial calculations
- Model-agnostic via LiteLLM — swap providers without changing logic

### ADR-003: Materiality-First Computation

**Decision:** Compute variances at ALL intersections first, then filter by materiality threshold.

**Rationale:**
- Enables netting detection (needs below-threshold data)
- Enables trend detection (needs historical non-material data)
- Pre-computed results serve 85% of queries in <100ms
- On-demand computation for remaining 15% in 2–5s

### ADR-004: Parent-Child with Materialized Paths

**Decision:** Ragged hierarchies stored as parent-child with pre-computed rollup_path strings.

**Rationale:**
- Supports irregular depth (ragged)
- O(1) ancestor/descendant checks via string prefix
- No recursive CTEs at runtime
- App cache at startup (~20MB) for fast traversal
- Recomputed only on hierarchy changes

### ADR-005: Pandas MVP, PySpark Production

**Decision:** MVP uses pandas DataFrames. Production migrates to PySpark on Databricks.

**Rationale:**
- Faster development cycle with pandas
- Same logic, different execution engine
- Synthetic data fits in memory (~100K rows)
- Production data (millions of rows) needs distributed compute

### ADR-006: No LangChain

**Decision:** Direct LiteLLM SDK calls. No LangChain or similar frameworks.

**Rationale:**
- Simpler dependency tree
- Full control over prompt construction
- Easier debugging and testing
- LiteLLM provides model-agnostic routing natively
- Agent tools are thin wrappers around Service 2 APIs

### ADR-007: Context + useReducer (No Redux)

**Decision:** React state management via Context API + useReducer.

**Rationale:**
- Sufficient for this app's state complexity
- No additional dependency
- Simpler mental model
- Global filters, user context, theme, review stats — 4 contexts
- SSE streaming handled by custom hook, not global state

### ADR-008: Review-Status-Aware Responses

**Decision:** All agent responses and UI views filter by review status based on user persona.

**Rationale:**
- BU Leaders should not see unreviewed AI drafts
- CFO should only see approved numbers
- Prevents premature action on unvalidated analysis
- Status displayed inline: "Reviewed by [analyst]" or "AI draft, pending review"

### ADR-009: RAG Few-Shot Commentary Learning

**Decision:** MVP uses RAG retrieval of approved commentaries as few-shot examples in LLM prompts. No fine-tuning.

**Rationale:**
- Works with zero training data (cold start)
- Quality improves naturally as analysts approve commentaries
- No model training infrastructure needed
- Weighted similarity: 70% semantic + 15% account match + 15% magnitude
- Phase 2 adds XGBoost for hypothesis ranking

### ADR-010: Bottom-Up Narrative Synthesis

**Decision:** Parent narratives are synthesized from approved child commentaries, not generated independently.

**Rationale:**
- Ensures consistency between detail and summary levels
- Leverages analyst-approved content
- Triggered automatically by approval workflow
- Cascades upward through hierarchy
- Reduces LLM calls (synthesize from existing, not generate from scratch)

---

## Data Flow

### Engine Pipeline
```
fact_financials → Pass 1 (Raw Variance)
                    → Pass 1.5 (Netting Detection) → fact_netting_flags
                    → Pass 2 (Threshold Filter)
                    → Pass 2.5 (Trend Detection) → fact_trend_flags
                    → Pass 3 (Decomposition) → fact_decomposition
                    → Pass 4 (Correlation) → fact_correlations
                    → Pass 5 (Narratives) → fact_variance_material
                                           → fact_review_status
                                           → audit_log
```

### Review Workflow
```
AI_DRAFT → [Analyst Review] → ANALYST_REVIEWED → [Director Approve] → APPROVED
                                                                         ↓
                                                               [Synthesis Trigger]
                                                                         ↓
                                                            Parent narrative updated
                                                                         ↓
                                                            knowledge_commentary_history
```

### Chat Flow
```
User Message → Gateway → Intent Classification (LLM)
                          → Tool Selection (Code)
                          → Service 2 API Call
                          → Response Generation (LLM)
                          → SSE Stream → Frontend
```

---

## Security Boundaries

- **No raw data to LLM:** Only metadata, aggregates, and variance context
- **PII stripped:** No employee names in LLM prompts
- **RBAC enforced at API layer:** Every endpoint checks persona + BU scope
- **Audit trail:** Every action logged to audit_log
- **Secrets in env vars:** Never in code or config files

---

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend | React 18 + TypeScript | SPA |
| Styling | Tailwind CSS + shadcn/ui | Component library |
| Charts | Recharts + D3.js | Data visualization |
| Backend | FastAPI (Python 3.11) | REST API |
| LLM | LiteLLM | Model-agnostic routing |
| Data (MVP) | pandas + Parquet/CSV | Local computation |
| Data (Prod) | Databricks | Distributed compute |
| Cache | Redis | Session + query cache |
| Vector Store | Qdrant | RAG similarity search |
| Auth | Azure AD (Entra ID) | OAuth 2.0 |
| Hosting | Azure Container Apps | Production deployment |
| Dev | Docker Compose | Local development |
