"""EvidenceVector contract (C-26, §6.2)."""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from .frame import CodecDescriptor


class ExpertStatus(str, Enum):
    """Execution status for an anti-spoofing expert."""
    OK = "OK"
    ABSTAIN = "ABSTAIN"
    DEFERRED = "DEFERRED"
    MODEL_UNAVAILABLE = "MODEL_UNAVAILABLE"
    TIMEOUT = "TIMEOUT"
    ERROR = "ERROR"


class ExpertResult(BaseModel):
    """Result emitted by an individual expert."""
    model_config = ConfigDict(extra="forbid")

    expert_id: str = Field(description="Identifier e.g. E1, E2, E3, E4, E5, E6")
    status: ExpertStatus = Field(description="Operational status")
    p: Optional[float] = Field(default=None, description="Raw synthetic probability [0, 1] if available")
    confidence: Optional[float] = Field(default=None, description="Expert confidence score [0, 1] if available")
    logits: Optional[List[float]] = Field(default=None, description="Internal frame logits if available")
    latency_ms: float = Field(default=0.0, description="Inference execution latency in ms")


class EvidenceVector(BaseModel):
    """Vector of multi-expert evidence emitted by L3 and published to Redis."""
    model_config = ConfigDict(extra="forbid")

    session_id: str = Field(description="Session identifier")
    frame_id: int = Field(description="Monotonic frame index")

    p_spec: Optional[float] = Field(default=None, description="E1 spectro-temporal probability")
    p_raw: Optional[float] = Field(default=None, description="E2 raw waveform probability")
    p_ssl: Optional[float] = Field(default=None, description="E3 multilingual SSL probe probability")
    p_spk: Optional[float] = Field(default=None, description="E4 speaker verification probability (ABSTAIN if unenrolled)")
    p_beh: Optional[float] = Field(default=None, description="E5 prosodic probability (DEFERRED in demo)")
    p_rep: Optional[float] = Field(default=None, description="E6 replay probability (DEFERRED in demo)")

    frame_logits: Dict[str, List[float]] = Field(default_factory=dict, description="Expert frame-level logits")
    expert_confidences: Dict[str, Optional[float]] = Field(default_factory=dict, description="Expert confidence scores")
    expert_statuses: Dict[str, ExpertStatus] = Field(default_factory=dict, description="Expert execution statuses")

    q_t: Optional[float] = Field(default=None, description="Acoustic quality score [0, 1]")
    codec_vec: Optional[CodecDescriptor] = Field(default=None, description="Detected audio codec descriptor")

    lang_t: str = Field(default="UNKNOWN", description="Language tag")
    switch_flag: bool = Field(default=False, description="Language switch flag")

    inference_latency_ms: Dict[str, float] = Field(default_factory=dict, description="Per-expert execution latency")
    model_versions: List[str] = Field(default_factory=list, description="Active model version signatures")
    timestamp: datetime = Field(description="UTC timestamp of evidence assembly")
