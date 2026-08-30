"""EvidenceRecord and audit contracts (C-44, §6.6)."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from .frame import CodecDescriptor
from .belief import VoiceBelief
from .context import ContextVector, TransactionContext
from .decision import PolicyAction


class ExpertScoreSummary(BaseModel):
    """Summarized expert output for the immutable record."""
    model_config = ConfigDict(extra="forbid")
    p: Optional[float] = None
    confidence: Optional[float] = None
    status: str


class EvidenceRecord(BaseModel):
    """Cryptographically chained, immutable evidence record persisted in SQLite."""
    model_config = ConfigDict(extra="forbid")

    record_id: str = Field(description="Unique record ID")
    session_id: str = Field(description="Session identifier")
    call_id: str = Field(description="External call or transaction reference")

    timestamp: datetime = Field(description="UTC timestamp")
    model_versions: List[str] = Field(description="Active model versions")

    codec: Optional[CodecDescriptor] = Field(default=None, description="Codec descriptor")
    audio_quality: Optional[float] = Field(default=None, description="Acoustic quality [0, 1]")

    expert_scores: Dict[str, ExpertScoreSummary] = Field(description="Summary of expert outputs")
    voice_belief: VoiceBelief = Field(description="Voice belief state snapshot")

    context_features: ContextVector = Field(description="Context vector snapshot")
    transaction_context: TransactionContext = Field(description="Transaction context snapshot")

    risk: float = Field(description="Risk score [0, 1]")
    confidence: float = Field(description="Risk confidence [0, 1]")

    action: PolicyAction = Field(description="Action chosen by policy engine")
    policy_version: str = Field(description="Policy version string")
    reason_codes: List[str] = Field(description="Reason codes")

    previous_hash: str = Field(description="SHA-256 hash of the previous record in the chain (or GENESIS)")
    record_hash: str = Field(description="SHA-256 hash of this canonical record content")


class TamperReport(BaseModel):
    """Result of evidence chain integrity verification."""
    model_config = ConfigDict(extra="forbid")
    is_valid: bool
    total_records: int
    corrupted_record_id: Optional[str] = None
    error_message: Optional[str] = None
