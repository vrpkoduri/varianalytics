"""Factory functions for building the Variance Knowledge Graph.

Provides two entry points:
    1. ``build_variance_graph(context)`` — during engine pipeline, after Pass 4.
    2. ``build_variance_graph_from_data(data_dir, period_id)`` — from persisted files.

Both return a ``VarianceGraph`` instance (currently ``NetworkXGraph``).
The implementation can be swapped via config without changing callers.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

from shared.knowledge.graph_interface import VarianceGraph
from shared.knowledge.networkx_graph import NetworkXGraph

logger = logging.getLogger(__name__)


def build_variance_graph(context: dict[str, Any]) -> VarianceGraph:
    """Build a knowledge graph from the engine pipeline context.

    Called between Pass 4 and Pass 5 inside the engine runner.

    Args:
        context: Engine pipeline context dict containing all_variances,
            material_variances, correlations, netting_flags, trend_flags,
            decomposition, acct_meta, data_dir, period_id, etc.

    Returns:
        Populated VarianceGraph instance.
    """
    start = time.monotonic()
    graph = _create_graph_instance()
    graph.build_from_context(context)
    elapsed = time.monotonic() - start

    summary = graph.summary()
    logger.info(
        "Knowledge graph built from context in %.3fs — "
        "%d nodes (%s), %d edges (%s)",
        elapsed,
        summary["node_count"],
        ", ".join(f"{k}={v}" for k, v in sorted(summary["nodes_by_type"].items())),
        summary["edge_count"],
        ", ".join(f"{k}={v}" for k, v in sorted(summary["edges_by_type"].items())),
    )

    return graph


def build_variance_graph_from_data(
    data_dir: str = "data/output",
    period_id: Optional[str] = None,
) -> VarianceGraph:
    """Build a knowledge graph from persisted parquet/CSV files.

    Called outside engine runs — e.g. on API startup or for ad-hoc
    queries.

    Args:
        data_dir: Path to data output directory with parquet files.
        period_id: Optional period filter.  If set, only variances for
            this period are loaded (reduces graph size).

    Returns:
        Populated VarianceGraph instance.
    """
    start = time.monotonic()
    graph = _create_graph_instance()
    graph.build_from_data(data_dir, period_id=period_id)
    elapsed = time.monotonic() - start

    summary = graph.summary()
    logger.info(
        "Knowledge graph built from data in %.3fs — "
        "%d nodes, %d edges (period=%s)",
        elapsed,
        summary["node_count"],
        summary["edge_count"],
        period_id or "all",
    )

    return graph


def _create_graph_instance() -> VarianceGraph:
    """Create the appropriate graph implementation.

    Currently returns NetworkXGraph.  In future, reads a config setting
    (GRAPH_PROVIDER=networkx|neo4j) to select the implementation.
    """
    # Phase 3A: always NetworkX
    # Phase 4+: read from config and return Neo4jGraph if configured
    return NetworkXGraph()
