"""Unit tests for shared.data.loader — DataLoader file I/O."""

from pathlib import Path

import pandas as pd
import pytest

from shared.data.loader import DataLoader


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    """Create a temp directory with sample data files."""
    # Create sample parquet
    df = pd.DataFrame({"period_id": ["2026-01"], "amount": [100.0]})
    df.to_parquet(tmp_path / "dim_period.parquet", index=False)
    df.to_csv(tmp_path / "dim_period.csv", index=False)

    # Create another table
    df2 = pd.DataFrame({"bu_id": ["marsh"], "bu_name": ["Marsh"]})
    df2.to_parquet(tmp_path / "dim_business_unit.parquet", index=False)
    return tmp_path


@pytest.fixture
def loader(data_dir: Path) -> DataLoader:
    return DataLoader(str(data_dir))


@pytest.mark.unit
class TestDataLoaderLoadTable:
    """Tests for loading tables by name."""

    def test_load_parquet(self, loader: DataLoader) -> None:
        df = loader.load_table("dim_period", format="parquet")
        assert len(df) == 1
        assert "period_id" in df.columns

    def test_load_csv(self, loader: DataLoader) -> None:
        df = loader.load_table("dim_period", format="csv")
        assert len(df) == 1

    def test_load_missing_table_raises(self, loader: DataLoader) -> None:
        with pytest.raises(FileNotFoundError):
            loader.load_table("nonexistent")

    def test_unsupported_format_raises(self, loader: DataLoader) -> None:
        with pytest.raises(ValueError, match="Unsupported format"):
            loader.load_table("dim_period", format="json")


@pytest.mark.unit
class TestDataLoaderUtilities:
    """Tests for table existence and listing."""

    def test_table_exists_true(self, loader: DataLoader) -> None:
        assert loader.table_exists("dim_period") is True

    def test_table_exists_false(self, loader: DataLoader) -> None:
        assert loader.table_exists("nonexistent") is False

    def test_list_tables(self, loader: DataLoader) -> None:
        tables = loader.list_tables()
        assert "dim_period" in tables
        assert "dim_business_unit" in tables

    def test_list_tables_empty_dir(self, tmp_path: Path) -> None:
        loader = DataLoader(str(tmp_path))
        assert loader.list_tables() == []
