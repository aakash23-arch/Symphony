"""SQLite storage repository interface (C-50)."""

from abc import ABC, abstractmethod
from typing import List, Optional
from voiceshield.contracts import Decision, EvidenceRecord


class StorageRepository(ABC):
    """Abstract interface for local SQLite persistence."""

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize database schema and tables."""
        raise NotImplementedError("StorageRepository.initialize is not implemented yet")

    @abstractmethod
    async def save_evidence_record(self, record: EvidenceRecord) -> None:
        """Persist EvidenceRecord to hash-chained storage (No PCM allowed)."""
        raise NotImplementedError("StorageRepository.save_evidence_record is not implemented yet")

    @abstractmethod
    async def get_evidence_records(self, session_id: str) -> List[EvidenceRecord]:
        """Fetch all evidence records for a session."""
        raise NotImplementedError("StorageRepository.get_evidence_records is not implemented yet")

    @abstractmethod
    async def get_latest_hash(self) -> str:
        """Get previous record hash for chain continuation (or GENESIS)."""
        raise NotImplementedError("StorageRepository.get_latest_hash is not implemented yet")
