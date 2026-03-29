"""Hierarchy cache — loaded at app startup (~20MB).

Caches dimension hierarchies and current fact_variance_material
for fast lookups without repeated data access.
"""

from __future__ import annotations

from typing import Any, Optional

from shared.hierarchy.tree import HierarchyNode, build_tree_from_dict, flatten_tree


class HierarchyCache:
    """In-memory cache for dimension hierarchies.

    Loaded once at service startup. Invalidated on hierarchy changes.
    """

    def __init__(self) -> None:
        self._trees: dict[str, HierarchyNode] = {}
        self._flat: dict[str, list[HierarchyNode]] = {}
        self._node_lookup: dict[str, HierarchyNode] = {}

    def load_dimension(self, dimension_name: str, tree_data: dict[str, Any]) -> None:
        """Load a dimension hierarchy from spec data.

        Args:
            dimension_name: e.g. 'Geography', 'Segment', 'LOB', 'CostCenter', 'Account'
            tree_data: Nested dict from synthetic-data-spec.json
        """
        root = build_tree_from_dict(tree_data)
        self._trees[dimension_name] = root
        flat = flatten_tree(root)
        self._flat[dimension_name] = flat
        for node in flat:
            self._node_lookup[node.node_id] = node

    def get_tree(self, dimension_name: str) -> Optional[HierarchyNode]:
        """Get root node of a dimension tree."""
        return self._trees.get(dimension_name)

    def get_flat(self, dimension_name: str) -> list[HierarchyNode]:
        """Get flat list of all nodes in a dimension."""
        return self._flat.get(dimension_name, [])

    def get_node(self, node_id: str) -> Optional[HierarchyNode]:
        """Look up any node by ID across all dimensions."""
        return self._node_lookup.get(node_id)

    def get_leaf_ids(self, dimension_name: str) -> list[str]:
        """Get all leaf node IDs for a dimension."""
        return [n.node_id for n in self._flat.get(dimension_name, []) if n.is_leaf]

    @property
    def loaded_dimensions(self) -> list[str]:
        """List of loaded dimension names."""
        return list(self._trees.keys())

    def clear(self) -> None:
        """Clear all cached data."""
        self._trees.clear()
        self._flat.clear()
        self._node_lookup.clear()
