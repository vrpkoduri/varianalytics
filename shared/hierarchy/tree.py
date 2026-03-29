"""Hierarchy tree data structures and traversal utilities.

Used across the synthetic data generator, computation engine, and API layer
for working with ragged parent-child hierarchies (Geo, Segment, LOB, CostCenter, Account).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class HierarchyNode:
    """A node in a parent-child hierarchy tree.

    Attributes:
        node_id: Unique identifier for this node.
        node_name: Display name.
        parent_id: Parent node ID (None for root).
        children: Child nodes.
        depth: Depth in tree (root=0).
        is_leaf: True if node has no children.
        rollup_path: Materialized path string, e.g. 'root/parent/child'.
        metadata: Additional key-value pairs (pl_category, variance_sign, etc.).
    """

    node_id: str
    node_name: str
    parent_id: Optional[str] = None
    children: list[HierarchyNode] = field(default_factory=list)
    depth: int = 0
    is_leaf: bool = True
    rollup_path: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


def build_tree_from_dict(data: dict[str, Any], parent_id: Optional[str] = None, depth: int = 0) -> HierarchyNode:
    """Build a HierarchyNode tree from nested dict (as in synthetic-data-spec.json).

    Args:
        data: Dict with 'node_id', 'node_name', 'children', and optional metadata keys.
        parent_id: Parent node ID for this level.
        depth: Current depth.

    Returns:
        Root HierarchyNode with children populated.
    """
    children_data = data.get("children", [])
    metadata = {
        k: v for k, v in data.items()
        if k not in ("node_id", "node_name", "children")
    }

    node = HierarchyNode(
        node_id=data["node_id"],
        node_name=data["node_name"],
        parent_id=parent_id,
        depth=depth,
        is_leaf=len(children_data) == 0,
        metadata=metadata,
    )

    node.children = [
        build_tree_from_dict(child, parent_id=node.node_id, depth=depth + 1)
        for child in children_data
    ]

    return node


def flatten_tree(node: HierarchyNode, path_prefix: str = "") -> list[HierarchyNode]:
    """Flatten a tree into a list with materialized rollup paths.

    Args:
        node: Root node to flatten.
        path_prefix: Parent's rollup path (builds incrementally).

    Returns:
        Flat list of all nodes with rollup_path populated.
    """
    current_path = f"{path_prefix}/{node.node_id}" if path_prefix else node.node_id
    node.rollup_path = current_path
    node.is_leaf = len(node.children) == 0

    result = [node]
    for child in node.children:
        result.extend(flatten_tree(child, current_path))

    return result


def get_leaf_nodes(node: HierarchyNode) -> list[HierarchyNode]:
    """Get all leaf nodes from a tree.

    Args:
        node: Root node.

    Returns:
        List of leaf nodes only.
    """
    if node.is_leaf:
        return [node]

    leaves: list[HierarchyNode] = []
    for child in node.children:
        leaves.extend(get_leaf_nodes(child))
    return leaves


def get_node_by_id(node: HierarchyNode, node_id: str) -> Optional[HierarchyNode]:
    """Find a node by ID in the tree.

    Args:
        node: Root node to search from.
        node_id: ID to find.

    Returns:
        The matching node, or None.
    """
    if node.node_id == node_id:
        return node
    for child in node.children:
        found = get_node_by_id(child, node_id)
        if found:
            return found
    return None


def get_ancestors(node_id: str, flat_nodes: list[HierarchyNode]) -> list[str]:
    """Get ancestor node IDs by walking up parent_id chain.

    Args:
        node_id: Starting node ID.
        flat_nodes: Flat list of all nodes.

    Returns:
        List of ancestor IDs from immediate parent to root.
    """
    node_map = {n.node_id: n for n in flat_nodes}
    ancestors = []
    current = node_map.get(node_id)
    while current and current.parent_id:
        ancestors.append(current.parent_id)
        current = node_map.get(current.parent_id)
    return ancestors
