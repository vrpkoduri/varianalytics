# FP&A Variance Analysis Agent

An AI-powered, model-agnostic agentic platform for automated variance detection, root cause analysis, and financial narrative generation.

## Quick Start

```bash
git clone <repo-url> && cd variance-agent
docker-compose up
# Frontend: http://localhost:3000
# Gateway:  http://localhost:8000
# Compute:  http://localhost:8001
# Reports:  http://localhost:8002
```

## Documentation

| Document | Description |
|----------|-------------|
| [CLAUDE.md](./CLAUDE.md) | Project context for Claude Code |
| [Master Spec](./docs/FPA_Master_Spec_v1.docx) | Single source of truth: product + solution design + workflow + commentary learning (15 sections, 15 tables, 50 endpoints) |
| [Synthetic Data Spec](./docs/synthetic-data-spec.json) | Dimension hierarchies and data generation rules |

## Architecture

Three microservices (50 endpoints total):
- **Gateway + Chat** (8000) — Auth, SSE chat, review/approval, notifications
- **Computation** (8001) — 5.5-pass engine, dashboard, variances, synthesis
- **Reports** (8002) — PDF/PPTX/DOCX/XLSX generation, scheduling

## Key Features

- **Materiality-first computation:** 5.5-pass engine computes everywhere, stores only above-threshold
- **Model-agnostic:** LiteLLM supports 100+ LLM providers
- **RAG-enhanced narratives:** Learns from analyst feedback, improves over time
- **Persona-aware:** 4-level narratives (detail → mid → summary → board) adapted to viewer role
- **Full workflow:** Review Queue → Approval Queue → gated distribution
- **Zero ML for MVP:** All deterministic + LLM reasoning; ML in Phase 2-3

## License

Proprietary — All rights reserved.
