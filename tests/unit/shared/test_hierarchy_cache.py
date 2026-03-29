"""Unit tests for shared.hierarchy.cache — HierarchyCache initialization and lookup."""

import pytest

from shared.hierarchy.cache import HierarchyCache
from shared.hierarchy.tree import HierarchyNode


@pytest.fixture
def cache() -> HierarchyCache:
    """Empty cache instance."""
    return HierarchyCache()


@pytest.fixture
def loaded_cache(cache: HierarchyCache, sample_geo_tree_data: dict, sample_account_tree_data: dict) -> HierarchyCache:
    """Cache loaded with Geography and Account dimensions."""
    cache.load_dimension("Geography", sample_geo_tree_data)
    cache.load_dimension("Account", sample_account_tree_data)
    return cache


@pytest.mark.unit
class TestHierarchyCacheLoad:
    """Tests for loading dimensions into the cache."""

    def test_load_dimension_creates_tree(self, cache: HierarchyCache, sample_geo_tree_data: dict) -> None:
        cache.load_dimension("Geography", sample_geo_tree_data)
        tree = cache.get_tree("Geography")
        assert tree is not None
        assert tree.node_id == "geo_global"

    def test_load_multiple_dimensions(self, loaded_cache: HierarchyCache) -> None:
        assert set(loaded_cache.loaded_dimensions) == {"Geography", "Account"}

    def test_loaded_dimensions_property(self, cache: HierarchyCache) -> None:
        assert cache.loaded_dimensions == []

    def test_load_dimension_creates_flat_list(self, cache: HierarchyCache, sample_geo_tree_data: dict) -> None:
        cache.load_dimension("Geography", sample_geo_tree_data)
        flat = cache.get_flat("Geography")
        assert len(flat) == 8  # All geo nodes

    def test_load_dimension_populates_node_lookup(self, cache: HierarchyCache, sample_geo_tree_data: dict) -> None:
        cache.load_dimension("Geography", sample_geo_tree_data)
        node = cache.get_node("geo_us_ne")
        assert node is not None
        assert node.node_name == "US Northeast"


@pytest.mark.unit
class TestHierarchyCacheLookup:
    """Tests for node and tree lookups."""

    def test_get_tree_missing_dimension(self, cache: HierarchyCache) -> None:
        assert cache.get_tree("Nonexistent") is None

    def test_get_flat_missing_dimension(self, cache: HierarchyCache) -> None:
        assert cache.get_flat("Nonexistent") == []

    def test_get_node_missing(self, cache: HierarchyCache) -> None:
        assert cache.get_node("nonexistent") is None

    def test_get_node_across_dimensions(self, loaded_cache: HierarchyCache) -> None:
        """Node lookup works across all loaded dimensions."""
        geo_node = loaded_cache.get_node("geo_us_ne")
        acct_node = loaded_cache.get_node("acct_advisory_fees")
        assert geo_node is not None
        assert acct_node is not None
        assert geo_node.node_name == "US Northeast"
        assert acct_node.node_name == "Advisory Fees"

    def test_get_leaf_ids(self, loaded_cache: HierarchyCache) -> None:
        geo_leaves = loaded_cache.get_leaf_ids("Geography")
        assert set(geo_leaves) == {"geo_us_ne", "geo_us_se", "geo_canada", "geo_uk_ireland"}

    def test_get_leaf_ids_missing_dimension(self, loaded_cache: HierarchyCache) -> None:
        assert loaded_cache.get_leaf_ids("Nonexistent") == []


@pytest.mark.unit
class TestHierarchyCacheClear:
    """Tests for cache clearing."""

    def test_clear_removes_all_data(self, loaded_cache: HierarchyCache) -> None:
        loaded_cache.clear()
        assert loaded_cache.loaded_dimensions == []
        assert loaded_cache.get_tree("Geography") is None
        assert loaded_cache.get_node("geo_us_ne") is None

    def test_reload_after_clear(self, loaded_cache: HierarchyCache, sample_geo_tree_data: dict) -> None:
        loaded_cache.clear()
        loaded_cache.load_dimension("Geography", sample_geo_tree_data)
        assert loaded_cache.get_tree("Geography") is not None
