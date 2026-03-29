"""Bottom-up rollup and materialized path utilities.

Used by the computation engine for aggregating leaf-level data up through
ragged hierarchies. Depth-sorted processing ensures children are computed
before parents.
"""

from __future__ import annotations

from shared.hierarchy.tree import HierarchyNode, flatten_tree


def build_rollup_paths(root: HierarchyNode) -> dict[str, str]:
    """Build a mapping of node_id -> rollup_path for all nodes in a tree.

    Args:
        root: Root node of the hierarchy.

    Returns:
        Dict mapping each node_id to its materialized rollup path.
    """
    flat = flatten_tree(root)
    return {node.node_id: node.rollup_path for node in flat}


def depth_sorted_nodes(root: HierarchyNode, reverse: bool = True) -> list[HierarchyNode]:
    """Return all nodes sorted by depth.

    Args:
        root: Root node of the hierarchy.
        reverse: If True (default), deepest nodes first (bottom-up for rollup).

    Returns:
        List of nodes sorted by depth.
    """
    flat = flatten_tree(root)
    return sorted(flat, key=lambda n: n.depth, reverse=reverse)


def get_children_map(root: HierarchyNode) -> dict[str, list[str]]:
    """Build a mapping of parent_id -> list of child_ids.

    Args:
        root: Root node.

    Returns:
        Dict mapping parent node_id to list of direct child node_ids.
    """
    flat = flatten_tree(root)
    children_map: dict[str, list[str]] = {}
    for node in flat:
        if node.parent_id is not None:
            children_map.setdefault(node.parent_id, []).append(node.node_id)
    return children_map


def is_descendant(ancestor_id: str, descendant_id: str, root: HierarchyNode) -> bool:
    """Check if descendant_id is a descendant of ancestor_id.

    Uses materialized rollup paths for O(1) check.

    Args:
        ancestor_id: Potential ancestor node ID.
        descendant_id: Potential descendant node ID.
        root: Root of hierarchy tree.

    Returns:
        True if descendant_id is under ancestor_id.
    """
    paths = build_rollup_paths(root)
    ancestor_path = paths.get(ancestor_id, "")
    descendant_path = paths.get(descendant_id, "")
    return descendant_path.startswith(ancestor_path + "/")
