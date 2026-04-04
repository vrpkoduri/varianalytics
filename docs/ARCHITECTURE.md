# Architecture — Marsh Vantage

**Version:** 2.0 | **Last Updated:** 2026-04-04

---

## 1. System Overview

```
┌─────────────────────────────────────────────────────────────┐
│  FRONTEND (React 18 + TypeScript + Tailwind)                │
│  Port 3000 (Docker) / Port 80 (Nginx reverse proxy)        │
│  9 views: Exec Summary, Dashboard, P&L, Chat, Review,      │
│  Approval, Reports, Admin, Login                            │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP/SSE
┌────────────────────────▼────────────────────────────────────┐
│  NGINX REVERSE PROXY (Port 80)                              │
│  /api/gateway/*    → Gateway :8000                          │
│  /api/computation/* → Computation :8001                     │
│  /api/reports/*    → Reports :8002                          │
│  /*                → Frontend :3000                         │
└────┬───────────────────┬───────────────────┬────────────────┘
     │                   │                   │
┌────▼────┐        ┌─────▼─────┐       ┌─────▼────┐
│ Gateway │        │Computation│       │ Reports  │
│  :8000  │───────▶│  :8001    │       │  :8002   │
│ Auth    │ HTTP   │ Engine    │       │ PDF/XLSX │
│ Chat    │        │ Dashboard │       │ PPTX/DOCX│
│ Review  │        │ Variances │       │ Schedule │
│ Admin   │        │ P&L       │       │          │
│ Notify  │        │ Synthesis │       │          │
└────┬────┘        └───────────┘       └──────────┘
     │
┌────▼──────────────────────────────────────────────┐
│  PostgreSQL :5432 │ Redis :6379 │ Qdrant :6333    │
└───────────────────────────────────────────────────┘
```

## 2. Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, TypeScript, Tailwind CSS, Recharts, Vite |
| Backend | FastAPI (Python 3.11+), Uvicorn |
| LLM | LiteLLM (model-agnostic), Anthropic Claude / Azure OpenAI |
| Database | PostgreSQL 16 (auth, workflow), Pandas DataFrames (analytics) |
| Vector Store | Qdrant (RAG embeddings) |
| Cache | Redis 7 |
| Auth | JWT (HS256), Azure AD optional |
| Containers | Docker Compose (8 services) |

## 3. Engine Pipeline

### Process A: Variance Analysis (no LLM)
Pass 1 → 1.5 → 2 → 2.5 → 3 (raw variance, netting, threshold, trends, decomposition)

### Process B: Intelligence & Narratives (LLM or template)
Pass 4 → 5 (correlation, narratives in 4 stages: leaf → parent → section → executive)

### Deterministic IDs
`variance_id = SHA256(period|account|bu|dims|view|base)[:16]`

## 4. Data Model

15 analytical tables (parquet) + auth tables (PostgreSQL) + 7 YAML configs.
See PRODUCT_SPECIFICATION.md §11 for full schema.

## 5. Frontend Component Tree

See PRODUCT_SPECIFICATION.md §3 for page descriptions.
Design tokens: Cobalt #002C77, Teal #00A8C7, glassmorphism cards, Playfair Display + DM Sans.

## 6. Key Decisions

| Decision | Choice | Rationale |
|---|---|---|
| DataFrames for analytics | Pandas in-memory | Sub-second on 100K rows |
| PostgreSQL for workflow | Relational | ACID for auth/review |
| JWT over sessions | Stateless | Scales without session store |
| LiteLLM | Model-agnostic | Swap providers without code changes |
| Deterministic IDs | SHA256 hash | Narratives survive re-runs |
| Template + LLM fallback | Dual mode | Always works without API key |
