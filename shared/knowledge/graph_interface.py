"""Abstract interface for the Variance Knowledge Graph.

Defines the query API that all graph implementations must satisfy.
MVP uses NetworkX (in-memory). Future: Neo4j, TigerGraph, etc.

The graph is a **derived view** of variance relationships, NOT a source
of truth.  It is rebuilt from engine output (parquet / Postgres) on every
engine run and cached (in-memory or Redis) for cross-service queries.

Node types: account, dimension, period, business_unit, variance,
            narrative, hypothesis, section
Edge types: parent_of, calc_depends_on, belongs_to, correlates_with,
            nets_with, has_trend, prior_period_of, peer_of,
            section_member_of, has_narrative
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional


class VarianceGraph(ABC):
    """Abstract interface for the variance knowledge graph.

    All consumer code (Pass 5, intelligence modules, APIs) programs
    against this interface --- never against a specific implementation.

    Implementations
    ---------------
    - ``NetworkXGraph``  (Phase 3A, in-memory, shared/knowledge/networkx_graph.py)
    - ``Neo4jGraph``     (future, shared/knowledge/neo4j_graph.py)
    """

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    @abstractmethod
    def build_from_context(self, context: dict[str, Any]) -> None:
        """Build the graph from an engine pipeline context dict.

        Called **during** an engine run, after Pass 4 completes.  The
        context dict contains DataFrames for all_variances,
        material_variances, correlations, netting_flags, trend_flags,
        decomposition, acct_meta, etc.

        Args:
            context: Engine pipeline context dictionary.
        """

    @abstractmethod
    def build_from_data(
        self,
        data_dir: str,
        period_id: Optional[str] = None,
    ) -> None:
        """Build the graph from persisted data files (parquet / CSV).

        Called **outside** an engine run --- e.g. on API startup --- to
        reconstruct the graph from the last saved engine output.

        Args:
            data_dir: Path to the data output directory.
            period_id: Optional period filter.  If provided, only
                variance nodes for this period are added.
        """

    # ------------------------------------------------------------------
    # Core queries (Phase 3A)
    # ------------------------------------------------------------------

    @abstractmethod
    def get_full_context(self, variance_id: str) -> dict[str, Any]:
        """Return all relationship data for a single variance.

        Returns a dict with keys:
            correlations   -- list[dict] with partner_id, score, hypothesis
            netting        -- dict or None (net/gross variance, ratio, check_type)
            trends         -- dict or None (direction, consecutive_periods, amount)
            decomposition  -- dict or None (method, components)
            siblings       -- list[dict] under same parent account
            peer_variances -- list[dict] same account across other BUs
            parent_chain   -- list[str] account ancestor IDs to root
            period_history -- list[dict] same account+BU over prior periods
        """

    @abstractmethod
    def get_cascade_chain(self, variance_id: str) -> list[str]:
        """Return IDs of narratives that must regenerate if this variance changes.

        Traverses parent_of and section_member_of edges upward:
        leaf variance -> parent account variance -> ... -> section -> executive.

        Returns:
            Ordered list of narrative/section/exec IDs to regenerate.
        """

    @abstractmethod
    def get_siblings(self, variance_id: str) -> list[dict[str, Any]]:
        """Return sibling variances under the same parent account.

        Args:
            variance_id: Target variance.

        Returns:
            List of dicts with account_id, account_name, variance_amount,
            variance_pct for each sibling.
        """

    @abstractmethod
    def get_correlations(self, variance_id: str) -> list[dict[str, Any]]:
        """Return correlated variances for a given variance.

        Args:
            variance_id: Target variance.

        Returns:
            List of dicts with partner_id, score, hypothesis.
        """

    @abstractmethod
    def get_account_ancestors(self, account_id: str) -> list[str]:
        """Return ancestor account IDs from immediate parent to root.

        Args:
            account_id: Starting account.

        Returns:
            List of account IDs ordered parent -> grandparent -> root.
        """

    @abstractmethod
    def get_peer_variances(self, variance_id: str) -> list[dict[str, Any]]:
        """Return peer variances: same account, same period, different BU.

        Primary purpose: detect systemic (all BUs) vs isolated (one BU)
        vs outlier (systemic + one extreme) patterns.

        Args:
            variance_id: Target variance.

        Returns:
            List of dicts with variance_id, bu_id, variance_amount,
            variance_pct for each peer.
        """

    @abstractmethod
    def get_period_history(
        self,
        account_id: str,
        bu_id: str,
        n_periods: int = 6,
    ) -> list[dict[str, Any]]:
        """Return variance history for an account+BU over prior periods.

        Uses the prior_period_of edge chain to walk backward in time.

        Args:
            account_id: Account to look up.
            bu_id: Business unit to filter.
            n_periods: Number of prior periods to return.

        Returns:
            List of dicts with period_id, variance_amount, variance_pct,
            ordered oldest-first.
        """

    # ------------------------------------------------------------------
    # Graph statistics
    # ------------------------------------------------------------------

    @abstractmethod
    def node_count(self) -> int:
        """Total number of nodes in the graph."""

    @abstractmethod
    def edge_count(self) -> int:
        """Total number of edges in the graph."""

    @abstractmethod
    def summary(self) -> dict[str, Any]:
        """Return a summary of graph contents.

        Returns a dict with:
            node_count, edge_count,
            nodes_by_type -- dict[str, int]  (e.g. {"account": 38, ...})
            edges_by_type -- dict[str, int]  (e.g. {"parent_of": 120, ...})
        """

    # ------------------------------------------------------------------
    # Node / edge access (for advanced queries)
    # ------------------------------------------------------------------

    @abstractmethod
    def has_node(self, node_id: str) -> bool:
        """Check if a node exists in the graph."""

    @abstractmethod
    def get_node(self, node_id: str) -> Optional[dict[str, Any]]:
        """Return node attributes, or None if not found."""

    @abstractmethod
    def get_neighbors(
        self,
        node_id: str,
        edge_type: Optional[str] = None,
        direction: str = "out",
    ) -> list[str]:
        """Return neighbor node IDs, optionally filtered by edge type.

        Args:
            node_id: Source node.
            edge_type: If set, only return neighbors connected by this
                edge type.
            direction: 'out' for successors, 'in' for predecessors,
                'both' for undirected neighbors.

        Returns:
            List of neighbor node IDs.
        """
