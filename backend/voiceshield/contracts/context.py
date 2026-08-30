"""ContextVector contract (C-36..C-37, §6.4)."""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, Optional
from pydantic import BaseModel, ConfigDict, Field
from .frame import CodecDescriptor


class ProvenanceType(str, Enum):
    REAL = "REAL"
    SIMULATED = "SIMULATED"
    UNAVAILABLE = "UNAVAILABLE"


class EnrollmentStatus(str, Enum):
    ENROLLED = "ENROLLED"
    NOT_ENROLLED = "NOT_ENROLLED"
    UNKNOWN = "UNKNOWN"


class BeneficiaryNovelty(str, Enum):
    NEW = "NEW"
    KNOWN = "KNOWN"
    UNKNOWN = "UNKNOWN"


class VoipMobileIndicator(str, Enum):
    VOIP = "VOIP"
    MOBILE = "MOBILE"
    LANDLINE = "LANDLINE"
    UNKNOWN = "UNKNOWN"


class KnownContactStatus(str, Enum):
    """Whether the caller is an established contact of the claimed identity."""
    KNOWN_CONTACT = "KNOWN_CONTACT"
    FIRST_CONTACT = "FIRST_CONTACT"
    UNKNOWN = "UNKNOWN"


class CallSource(str, Enum):
    """Origin channel the call arrived on."""
    INBOUND_PSTN = "INBOUND_PSTN"
    INBOUND_VOIP = "INBOUND_VOIP"
    OUTBOUND_CALLBACK = "OUTBOUND_CALLBACK"
    IN_APP = "IN_APP"
    BRANCH = "BRANCH"
    UNKNOWN = "UNKNOWN"


class WorkflowState(str, Enum):
    """Position in a sensitive operational workflow (C-38 behavioural context)."""
    NONE = "NONE"
    ROUTINE = "ROUTINE"
    CREDENTIAL_RESET = "CREDENTIAL_RESET"
    PAYEE_ADDITION = "PAYEE_ADDITION"
    LIMIT_INCREASE = "LIMIT_INCREASE"
    HIGH_VALUE_TRANSFER = "HIGH_VALUE_TRANSFER"
    PRIVILEGED_AUTHORISATION = "PRIVILEGED_AUTHORISATION"


class IdentityContext(BaseModel):
    model_config = ConfigDict(extra="forbid")
    claimed_identity: Optional[str] = None
    verified_identity: Optional[str] = None
    enrollment_status: EnrollmentStatus = EnrollmentStatus.UNKNOWN
    cnap_state: Optional[str] = None
    identity_mismatch: Optional[bool] = None
    known_contact: KnownContactStatus = KnownContactStatus.UNKNOWN


class NumberContext(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reputation: Optional[float] = None
    age_days: Optional[int] = None
    known_fraud_status: Optional[bool] = None
    port_history: Optional[bool] = None


class TransactionContext(BaseModel):
    model_config = ConfigDict(extra="forbid")
    amount: Optional[Decimal] = None
    currency: Optional[str] = None
    transaction_type: Optional[str] = None
    beneficiary_novelty: BeneficiaryNovelty = BeneficiaryNovelty.UNKNOWN
    velocity: Optional[float] = None
    historical_deviation: Optional[float] = None
    sensitive_action: Optional[str] = Field(
        default=None,
        description="Declared sensitive-action class, e.g. 'CREDENTIAL_RESET', 'WIRE_TRANSFER'",
    )


class BehaviourContext(BaseModel):
    model_config = ConfigDict(extra="forbid")
    urgency: Optional[bool] = None
    secrecy: Optional[bool] = None
    callback_refusal: Optional[bool] = None
    verification_bypass: Optional[bool] = None
    unusual_request: Optional[bool] = None
    prior_fraud_indicator: Optional[bool] = Field(
        default=None,
        description="A previously confirmed fraud association for this identity/number, if known",
    )
    workflow_state: WorkflowState = WorkflowState.NONE


class TechnicalContext(BaseModel):
    model_config = ConfigDict(extra="forbid")
    device_signal: Optional[str] = None
    network_origin: Optional[str] = None
    voip_mobile_indicator: VoipMobileIndicator = VoipMobileIndicator.UNKNOWN
    call_source: CallSource = CallSource.UNKNOWN
    codec: Optional[CodecDescriptor] = None


class SessionHistory(BaseModel):
    """What this session has already done, and what earlier sessions established.

    Distinct from BehaviourContext: that describes what the caller is asking for
    right now, this describes accumulated session state the engine can hold
    against them (repeated failed step-ups, an escalation already raised).
    """
    model_config = ConfigDict(extra="forbid")
    prior_sessions: Optional[int] = Field(default=None, description="Count of prior sessions for this identity")
    prior_step_up_failures: int = Field(default=0, description="Failed step-up verifications this session")
    prior_step_up_successes: int = Field(default=0, description="Passed step-up verifications this session")
    prior_escalations: int = Field(default=0, description="Escalations previously raised for this identity")
    session_duration_s: Optional[float] = Field(default=None, description="Elapsed session duration in seconds")
    repeat_caller: Optional[bool] = Field(default=None, description="Caller seen before on this number")


class ContextVector(BaseModel):
    """Context vector holding identity, transaction, and behavioural factors with strict provenance."""
    model_config = ConfigDict(extra="forbid")

    session_id: str = Field(description="Session identifier")
    identity: IdentityContext = Field(default_factory=IdentityContext)
    number: NumberContext = Field(default_factory=NumberContext)
    transaction: TransactionContext = Field(default_factory=TransactionContext)
    behaviour: BehaviourContext = Field(default_factory=BehaviourContext)
    technical: TechnicalContext = Field(default_factory=TechnicalContext)
    history: SessionHistory = Field(default_factory=SessionHistory)

    language: str = Field(default="UNKNOWN", description="Observed call language tag or 'UNKNOWN'")

    provenance: Dict[str, ProvenanceType] = Field(
        default_factory=dict,
        description="Field-level provenance: REAL | SIMULATED | UNAVAILABLE",
    )
    timestamp: datetime = Field(description="UTC timestamp")
