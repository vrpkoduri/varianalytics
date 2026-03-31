"""Report storage abstraction — local filesystem (MVP) + Azure Blob (production)."""
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class ReportStorage(ABC):
    """Abstract report storage interface."""

    @abstractmethod
    async def save(self, job_id: str, filename: str, data: bytes) -> str:
        """Save report data. Returns path/URL."""

    @abstractmethod
    async def get_path(self, job_id: str) -> Optional[str]:
        """Get local path for a saved report. None if not found."""

    @abstractmethod
    async def exists(self, job_id: str) -> bool:
        """Check if report exists."""


class LocalReportStorage(ReportStorage):
    """Local filesystem storage for MVP."""

    def __init__(self, base_dir: str = "data/reports") -> None:
        self._base_dir = Path(base_dir)
        self._base_dir.mkdir(parents=True, exist_ok=True)
        self._files: dict[str, str] = {}  # job_id -> filepath

    async def save(self, job_id: str, filename: str, data: bytes) -> str:
        job_dir = self._base_dir / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        filepath = job_dir / filename
        filepath.write_bytes(data)
        self._files[job_id] = str(filepath)
        logger.info("Saved report %s → %s (%d bytes)", job_id, filepath, len(data))
        return str(filepath)

    async def get_path(self, job_id: str) -> Optional[str]:
        path = self._files.get(job_id)
        if path and Path(path).exists():
            return path
        # Try to find in directory
        job_dir = self._base_dir / job_id
        if job_dir.exists():
            files = list(job_dir.iterdir())
            if files:
                self._files[job_id] = str(files[0])
                return str(files[0])
        return None

    async def exists(self, job_id: str) -> bool:
        return await self.get_path(job_id) is not None


class AzureBlobReportStorage(ReportStorage):
    """Azure Blob Storage for production. Requires azure-storage-blob."""

    def __init__(self, connection_string: str, container: str = "reports") -> None:
        self._connection_string = connection_string
        self._container = container
        # TODO: Initialize BlobServiceClient when deploying to Azure

    async def save(self, job_id: str, filename: str, data: bytes) -> str:
        raise NotImplementedError("Azure Blob Storage — configure for production deployment")

    async def get_path(self, job_id: str) -> Optional[str]:
        raise NotImplementedError("Azure Blob Storage — configure for production deployment")

    async def exists(self, job_id: str) -> bool:
        raise NotImplementedError("Azure Blob Storage — configure for production deployment")
