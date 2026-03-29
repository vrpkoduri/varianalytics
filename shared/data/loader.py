"""Data loading abstraction — reads from local files (MVP) or Databricks (Phase 2).

Provides a consistent interface for accessing dimension and fact tables
regardless of the underlying storage backend.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd


class DataLoader:
    """Loads dimension and fact tables from the data output directory.

    MVP: Reads Parquet/CSV from local disk.
    Phase 2: Will add Databricks SQL backend.
    """

    def __init__(self, data_dir: str = "data/output") -> None:
        """Initialize with path to data directory.

        Args:
            data_dir: Path to directory containing table files.
        """
        self.data_dir = Path(data_dir)

    def load_table(self, table_name: str, format: str = "parquet") -> pd.DataFrame:
        """Load a single table by name.

        Args:
            table_name: e.g. 'dim_hierarchy', 'fact_financials'
            format: 'parquet' or 'csv'

        Returns:
            DataFrame with table data.

        Raises:
            FileNotFoundError: If table file doesn't exist.
        """
        if format not in ("parquet", "csv"):
            raise ValueError(f"Unsupported format: {format}")

        file_path = self.data_dir / f"{table_name}.{format}"
        if not file_path.exists():
            raise FileNotFoundError(f"Table file not found: {file_path}")

        if format == "parquet":
            return pd.read_parquet(file_path)
        else:
            return pd.read_csv(file_path)

    def table_exists(self, table_name: str, format: str = "parquet") -> bool:
        """Check if a table file exists."""
        return (self.data_dir / f"{table_name}.{format}").exists()

    def list_tables(self) -> list[str]:
        """List all available table names."""
        tables = set()
        for f in self.data_dir.glob("*.*"):
            if f.suffix in (".parquet", ".csv"):
                tables.add(f.stem)
        return sorted(tables)
