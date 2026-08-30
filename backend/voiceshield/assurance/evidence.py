"""Evidence recording and hash-chaining interface (C-44)."""

from abc import ABC, abstractmethod
from typing import List, Optional
from voiceshield.contracts import Decision, EvidenceRecord, TamperReport


class EvidenceRecorder(ABC):
    """Abstract interface for constructing and persisting SHA-256 hash-chained evidence records."""

    @abstractmethod
    def append_record(self, decision: Decision) -> EvidenceRecord:
        """Construct canonical hash-chained EvidenceRecord and commit to SQLite."""
        raise NotImplementedError("EvidenceRecorder.append_record is not implemented yet")

    @abstractmethod
    def verify_chain(self, session_id: Optional[str] = None) -> TamperReport:
        """Verify hash chain integrity across all records or for a single session."""
        raise NotImplementedError("EvidenceRecorder.verify_chain is not implemented yet")
