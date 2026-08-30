"""VoiceBelief contract (C-28..C-35, §6.3)."""

from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class DecisionBand(str, Enum):
    """Four-tier evidence classification band for VoiceBelief."""
    GENUINE = "GENUINE"
    UNCERTAIN = "UNCERTAIN"
    SUSPICIOUS = "SUSPICIOUS"
    SYNTHETIC_HIGH_CONFIDENCE = "SYNTHETIC_HIGH_CONFIDENCE"


class ClockType(str, Enum):
    """Inference cadence."""
    FAST = "FAST"
    SLOW = "SLOW"


class TrajectoryPoint(BaseModel):
    """Single time-indexed point on the temporal risk trajectory."""
    model_config = ConfigDict(extra="forbid")
    t: float = Field(description="Time in seconds from session start")
    p_spoof: Optional[float] = Field(description="Aggregated synthetic belief [0, 1]")
    confidence: float = Field(description="Belief confidence [0, 1]")


class ExpertContribution(BaseModel):
    """Feature factor contribution to the current belief."""
    model_config = ConfigDict(extra="forbid")
    expert_id: str = Field(description="Expert identifier, e.g. E1, E2, E3, E4")
    weight: float = Field(description="Normalized weight assigned to this expert in fusion")
    raw_p: Optional[float] = Field(description="Raw probability emitted by expert")
    calibrated_p: Optional[float] = Field(description="Calibrated probability")


class VoiceBelief(BaseModel):
    """Voice belief state produced by L4 fusion representing acoustic authenticity."""
    model_config = ConfigDict(extra="forbid")

    session_id: str = Field(description="Session identifier")

    P_spoof: Optional[float] = Field(default=None, description="Posterior probability of synthetic speech [0, 1]")
    confidence: float = Field(description="Statistical confidence in P_spoof estimate [0, 1]")

    band: DecisionBand = Field(description="Categorical evidence band")
    q_call: Optional[float] = Field(default=None, description="Call-level aggregated acoustic quality")

    spans: List[str] = Field(default_factory=list, description="Suspicious temporal audio spans (empty in demo)")
    trajectory: List[TrajectoryPoint] = Field(default_factory=list, description="Historical belief trajectory points")

    contributing_experts: List[ExpertContribution] = Field(default_factory=list, description="Expert contribution weights")
    uncertainty_reason: Optional[str] = Field(default=None, description="Reason for high uncertainty or UNCERTAIN band")

    switch_damping_events: List[str] = Field(default_factory=list, description="Damping events (empty in demo)")
    model_versions: List[str] = Field(default_factory=list, description="Versions of models contributing to belief")
    clock: ClockType = Field(default=ClockType.SLOW, description="Fast provisional vs slow action-grade clock")
    timestamp: datetime = Field(description="UTC timestamp")
