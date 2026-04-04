# Knowledge Graph Architecture — Marsh Vantage

**Version:** 1.0 | **Last Updated:** 2026-04-04 | **Phase:** 3A

---

## Overview

The Variance Knowledge Graph is an in-memory directed graph that unifies ALL variance relationships into a single queryable structure. It replaces the ad-hoc dict/DataFrame lookups previously built in Pass 5's `_build_context_maps()` with a graph-based approach using NetworkX.

**Purpose:** Foundation for all 15 intelligence dimensions, cascade regeneration, and the engine orchestrator.

**Key Principles:**
1. The graph is a **derived view**, not a source of truth. Parquet/Postgres is authoritative.
2. **Rebuilt on every engine run** from pipeline context (after Pass 4).
3. **Cached in DataService** for API-time queries between engine runs.
4. **Abstract interface** (`VarianceGraph`) enables swapping NetworkX for Neo4j without changing consumers.

---

## Architecture

```
shared/knowledge/
├── graph_interface.py      # Abstract VarianceGraph ABC
├── networkx_graph.py       # NetworkX DiGraph implementation (Phase 3A)
├── graph_builder.py        # Factory: build_variance_graph(), build_variance_graph_from_data()
├── knowledge_store.py      # Existing — RAG vector store
├── embedding.py            # Existing — embeddings
├── rag.py                  # Existing — RAG retrieval
└── vector_store.py         # Existing — vector store abstraction
```

---

## Node Types (8)

| Node Type | ID Pattern | Example | Count (single period) |
|-----------|------------|---------|----------------------|
| `account` | `account_id` | `"A001"` | 38 |
| `dimension` | `{dim_type}:{node_id}` | `"geo:NA"` | 80 |
| `period` | `period_id` | `"2026-06"` | 36 |
| `business_unit` | `bu_id` | `"marsh"` | 5 |
| `variance` | `variance_id` (SHA256 hex) | `"a1b2c3d4e5f67890"` | ~10,695 |
| `narrative` | `narrative:{variance_id}` | — | Phase 3F |
| `hypothesis` | `hypothesis:{correlation_id}` | `"hypothesis:c001"` | ~60 |
| `section` | `section:{name}:{period}` | `"section:revenue:2026-06"` | 5 |

**Total nodes (single period):** ~10,919

---

## Edge Types (13)

| Edge Type | From | To | Count | Purpose |
|-----------|------|-----|-------|---------|
| `parent_of` | account/dimension | account/dimension | ~113 | Hierarchy |
| `calc_depends_on` | account | account | varies | EBITDA, GP dependencies |
| `belongs_to` | variance | account/BU/period | ~32,085 | Dimensional membership |
| `correlates_with` | variance | variance | ~40 | Pairwise correlation |
| `nets_with` | variance | variance | — | Netting pairs |
| `has_trend` | variance | period | — | Trend membership |
| `prior_period_of` | period | period | 35 | Temporal chain |
| `peer_of` | variance | variance | — | Same acct, diff BU |
| `section_member_of` | variance | section | ~7,875 | P&L section grouping |
| `has_narrative` | variance | narrative | — | Phase 3F |

**Total edges (single period):** ~40,148

---

## Query API

### Core Methods (Phase 3A)

| Method | Returns | Use Case |
|--------|---------|----------|
| `get_full_context(variance_id)` | dict with all 8 relationship types | Narrative enrichment |
| `get_cascade_chain(variance_id)` | list of IDs to regenerate | Cascade regeneration (legacy) |
| `get_cascade_chain_typed(variance_id)` | list of dicts with id, type, level | Enhanced cascade (Phase 3C) |
| `get_siblings(variance_id)` | list of sibling variances | Context for parent narratives |
| `get_correlations(variance_id)` | list of correlated variances | Root cause context |
| `get_account_ancestors(account_id)` | list of parent account IDs | Hierarchy traversal |
| `get_peer_variances(variance_id)` | list of same-acct, diff-BU variances | Peer comparison |
| `get_period_history(account_id, bu_id)` | list of prior period variances | Trend context |

### Stats Methods

| Method | Returns |
|--------|---------|
| `node_count()` | Total nodes |
| `edge_count()` | Total edges |
| `summary()` | dict with counts by type |
| `has_node(id)` | bool |
| `get_node(id)` | dict of attributes |
| `get_neighbors(id, edge_type, direction)` | list of neighbor IDs |

---

## Build Lifecycle

```
Engine Run (Passes 1-4)
    ↓
Pass 4 completes (correlations computed)
    ↓
build_variance_graph(context) → NetworkXGraph
    ↓
context["knowledge_graph"] = graph
    ↓
Pass 5 uses graph via _context_maps_from_graph()
    ↓
Graph cached in DataService for API queries
    ↓
Next engine run → cache invalidated → rebuild
```

### Build from Engine Context
```python
from shared.knowledge.graph_builder import build_variance_graph
graph = build_variance_graph(context)  # After Pass 4
```

### Build from Persisted Data
```python
from shared.knowledge.graph_builder import build_variance_graph_from_data
graph = build_variance_graph_from_data("data/output", period_id="2026-06")
```

### DataService Cache
```python
ds = DataService.get_instance()
graph = ds.get_graph("2026-06")  # Cached after first call
ds.invalidate_graph_cache()      # Clear after engine re-run
```

---

## Backward Compatibility

Pass 5's `_build_context_maps()` has a **dual-path design**:

1. **Graph path:** When `context["knowledge_graph"]` exists, delegates to `_context_maps_from_graph()`.
2. **Legacy path:** Falls back to `_build_context_maps_legacy()` (original dict-building logic).

Both paths produce identical 5-map output:
- `correlations` — variance_id -> [correlated partners]
- `netting` — parent_node_id -> netting details
- `trends` — account_id -> best trend
- `decomposition` — variance_id -> components
- `siblings` — parent_account -> [sibling summaries]

Downstream code (`_build_enriched_prompt`, template/LLM generators) is unaffected.

---

## Future: Neo4j Migration Path

### Phase 4+ Architecture

```
shared/knowledge/
├── graph_interface.py      # Abstract VarianceGraph ABC (unchanged)
├── networkx_graph.py       # In-memory implementation (unchanged)
├── neo4j_graph.py          # NEW — Neo4j driver implementation
├── graph_builder.py        # Factory reads GRAPH_PROVIDER config
```

### Docker Compose Addition
```yaml
varanalytics-neo4j:
  image: neo4j:5-community
  ports:
    - "7687:7687"
    - "7474:7474"
  environment:
    NEO4J_AUTH: neo4j/password
```

### Config-Driven Provider Selection
```python
# graph_builder.py
def _create_graph_instance() -> VarianceGraph:
    provider = os.getenv("GRAPH_PROVIDER", "networkx")
    if provider == "neo4j":
        from shared.knowledge.neo4j_graph import Neo4jGraph
        return Neo4jGraph(uri=os.getenv("NEO4J_URI"))
    return NetworkXGraph()
```

**No consumer code changes required.**

---

## Performance

| Operation | Dataset | Time |
|-----------|---------|------|
| Build from context (single period) | 10K variances | ~4.5s |
| Build from data (single period) | 10K variances | ~4.5s |
| Build from data (all 12 periods) | 106K variances | ~45s |
| `get_full_context()` query | — | <1ms |
| DataService cache hit | — | <1ms |

Memory: ~50-80 MB for full 12-period graph.

---

## Tests

| File | Tests | Category |
|------|-------|----------|
| `tests/unit/shared/test_graph_interface.py` | 5 | ABC contract |
| `tests/unit/shared/test_networkx_graph.py` | 50 | Node/edge/query correctness |
| `tests/integration/test_graph_engine_integration.py` | 17 | Engine + graph integration |
| **Total** | **72** | — |
