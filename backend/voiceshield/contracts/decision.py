"""Decision and RiskAssessment contracts (C-38..C-42, §6.5)."""

from datetime import datetime
from enum import Enum, IntEnum
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from .belief import ClockType


class RiskBand(str, Enum):
    """Contextual composite risk bands."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
    UNCERTAIN = "UNCERTAIN"


class PolicyAction(str, Enum):
    """Actions emitted by the explicit policy engine."""
    ALLOW = "ALLOW"
    WARN = "WARN"
    STEP_UP = "STEP_UP"
    HOLD = "HOLD"
    ESCALATE = "ESCALATE"
    ACTIVE_LIVENESS = "ACTIVE_LIVENESS"


class RiskState(str, Enum):
    """Risk state machine states."""
    UNKNOWN = "UNKNOWN"
    MONITORING = "MONITORING"
    TRUSTED = "TRUSTED"
    VERIFY = "VERIFY"
    HIGH_RISK = "HIGH_RISK"
    HOLD = "HOLD"
    ESCALATE = "ESCALATE"
    REVIEWED = "REVIEWED"


class TransactionTier(IntEnum):
    """Transaction sensitivity tiers 0 (least sensitive) to 4 (most sensitive)."""
    TIER_0 = 0
    TIER_1 = 1
    TIER_2 = 2
    TIER_3 = 3
    TIER_4 = 4


class RiskContribution(BaseModel):
    """Signed risk attribution factor.

    ``weight`` is the factor's share of the total absolute movement away from the
    baseline; it is an attribution of the score this engine computed, NOT a
    causal claim about the call (§10.1).
    """
    model_config = ConfigDict(extra="forbid")
    factor: str = Field(description="Factor name e.g. acoustic_P_spoof, transaction_amount, high_velocity")
    weight: float = Field(description="Normalized influence weight [0, 1]")
    direction: str = Field(description="Impact direction: 'INCREASES_RISK' or 'DECREASES_RISK'")
    points: float = Field(default=0.0, description="Signed contribution in risk points on the [0, 1] scale")
    detail: Optional[str] = Field(default=None, description="Human-readable basis for this contribution")


class EvidenceReference(BaseModel):
    """Pointer to the evidence a contribution was derived from.

    The engine never copies audio or embeddings; it references the artefact that
    produced the signal so an auditor can retrieve it (P2, §10.2).
    """
    model_config = ConfigDict(extra="forbid")
    kind: str = Field(description="Evidence kind: 'VOICE_BELIEF' | 'EXPERT' | 'CONTEXT' | 'POLICY'")
    ref: str = Field(description="Identifier of the referenced artefact")
    detail: Optional[str] = Field(default=None, description="What this reference contributed")


class ScoreSemantics(str, Enum):
    """How the emitted score may legitimately be described.

    ``UNCALIBRATED_RISK_SCORE`` is the only honest label until a calibration set
    has actually been fitted; it means the score orders calls by concern, not
    that 0.8 implies an 80% chance of fraud.
    """
    UNCALIBRATED_RISK_SCORE = "UNCALIBRATED_RISK_SCORE"
    CALIBRATED_PROBABILITY = "CALIBRATED_PROBABILITY"


class RiskAssessment(BaseModel):
    """Composite risk assessment combining acoustic voice belief and contextual signals."""
    model_config = ConfigDict(extra="forbid")

    session_id: str = Field(description="Session identifier")
    risk_score: float = Field(description="Composite risk score [0, 1]")
    risk_confidence: float = Field(description="Confidence in composite risk score [0, 1]")
    risk_band: RiskBand = Field(description="Risk classification band")

    contributions: List[RiskContribution] = Field(default_factory=list, description="Ordered factor contributions")
    context_degraded: bool = Field(default=False, description="Flag indicating context was missing or degraded")

    score_semantics: ScoreSemantics = Field(
        default=ScoreSemantics.UNCALIBRATED_RISK_SCORE,
        description="Whether risk_score is a calibrated probability or an uncalibrated risk score",
    )
    score_label: str = Field(
        default="risk score",
        description="Human-facing noun for risk_score; must not read as a probability while uncalibrated",
    )
    timestamp: datetime = Field(description="UTC timestamp")


class RiskDecision(BaseModel):
    """Full explainable output of the Context and Risk Engine.

    Wraps the frozen ``RiskAssessment`` and adds the action, reason codes and
    audit metadata a caller needs to act on it and later defend it.
    """
    model_config = ConfigDict(extra="forbid")

    session_id: str = Field(description="Session identifier")
    risk: RiskAssessment = Field(description="Composite risk assessment (score, band, confidence)")

    action: PolicyAction = Field(description="Action mandated by the matched policy")
    matched_policy: str = Field(description="Identifier of the policy rule that produced the action")
    transaction_tier: TransactionTier = Field(description="Sensitivity tier applied (0-4)")

    reason_codes: List[str] = Field(default_factory=list, description="Machine-readable reason codes")
    top_factors: List[RiskContribution] = Field(default_factory=list, description="Highest-attribution factors, ordered")
    evidence_refs: List[EvidenceReference] = Field(default_factory=list, description="Evidence artefact references")

    recommended_verifications: List[str] = Field(default_factory=list, description="Concrete step-up recommendations")
    fail_safe_engaged: bool = Field(default=False, description="True when the outcome came from a fail-safe path")

    policy_version: str = Field(description="Version of the policy set applied")
    timestamp: datetime = Field(description="UTC timestamp")

    @property
    def risk_score(self) -> float:
        """Convenience accessor for the composite risk score."""
        return self.risk.risk_score

    @property
    def risk_band(self) -> RiskBand:
        """Convenience accessor for the risk band."""
        return self.risk.risk_band


class Decision(BaseModel):
    """Action-grade security policy decision emitted by L5."""
    model_config = ConfigDict(extra="forbid")

    decision_id: str = Field(description="Unique decision ID")
    session_id: str = Field(description="Session identifier")

    voice_belief_ref: str = Field(description="Reference ID or hash of originating VoiceBelief")
    risk: RiskAssessment = Field(description="Underlying composite risk assessment")

    transaction_tier: TransactionTier = Field(description="Sensitivity tier (0-4)")

    action: PolicyAction = Field(description="Recommended action class")
    state: RiskState = Field(description="Risk state machine state")

    reason_codes: List[str] = Field(default_factory=list, description="Machine-readable policy reason codes")
    policy_version: str = Field(description="Version of policy rules applied")
    clock: ClockType = Field(default=ClockType.SLOW, description="Decisions are SLOW clock only")

    recommended_verifications: List[str] = Field(default_factory=list, description="Actionable step-up recommendations")
    timestamp: datetime = Field(description="UTC timestamp")
