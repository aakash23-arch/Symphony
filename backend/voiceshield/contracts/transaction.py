"""DEMO TRANSACTION ENVIRONMENT - transaction contracts (§9.2, C-39).

    THIS IS NOT A REAL BANKING INTEGRATION.

Every object in this module belongs to a simulated, in-memory transaction
environment built for the internal demo. Nothing here moves money, contacts a
payment network, or talks to any external system. The ``environment`` field on
``DemoTransaction`` carries that label into every API response and every
serialised record, so a consumer cannot receive one of these objects without
also receiving the disclaimer - a docstring alone would not survive
serialisation to the UI.

The state machine is the point of this module. A transaction's state may only
change along a declared edge, and every change emits an audit event.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Set

from pydantic import BaseModel, ConfigDict, Field

from .context import BeneficiaryNovelty
from .decision import PolicyAction

#: Stamped on every transaction and audit event. Do not change this string
#: without also changing the tests that assert the demo labelling is present.
DEMO_ENVIRONMENT_LABEL = "DEMO TRANSACTION ENVIRONMENT"

#: Restated on records so that a persisted or exported transaction still says
#: what it is, long after it has left the process that created it.
NOT_A_REAL_BANKING_INTEGRATION = (
    "Simulated transaction for internal demonstration only. "
    "No real funds move and no external banking system is contacted."
)


class TransactionState(str, Enum):
    """The five frozen demo transaction states."""

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    HELD = "HELD"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


#: States from which no further transition is legal.
#:
#: APPROVED is terminal alongside REJECTED and CANCELLED: in a real ledger an
#: executed payment is not un-executed by editing a row, it is reversed by a
#: second entry. Modelling it as terminal keeps the demo honest about that,
#: and stops a held-then-approved transaction from silently sliding back into
#: HELD after the verification that released it.
TERMINAL_STATES: Set[TransactionState] = {
    TransactionState.APPROVED,
    TransactionState.REJECTED,
    TransactionState.CANCELLED,
}

#: The complete legal transition graph. Anything not listed here is rejected.
#:
#: HELD is deliberately reachable only from PENDING, and is itself an
#: intermediate state: a held transaction must be resolved by an explicit
#: release, rejection or cancellation. It never expires into approval on its
#: own, because a hold that times out into "allowed" is not a hold.
LEGAL_TRANSITIONS: Dict[TransactionState, Set[TransactionState]] = {
    TransactionState.PENDING: {
        TransactionState.APPROVED,
        TransactionState.HELD,
        TransactionState.REJECTED,
        TransactionState.CANCELLED,
    },
    TransactionState.HELD: {
        TransactionState.APPROVED,
        TransactionState.REJECTED,
        TransactionState.CANCELLED,
    },
    TransactionState.APPROVED: set(),
    TransactionState.REJECTED: set(),
    TransactionState.CANCELLED: set(),
}


class AuditEventType(str, Enum):
    """Audit event kinds emitted by the demo transaction environment."""

    TRANSACTION_CREATED = "TRANSACTION_CREATED"
    STATE_CHANGED = "STATE_CHANGED"
    HOLD_PLACED = "HOLD_PLACED"
    HOLD_RELEASED = "HOLD_RELEASED"
    RISK_ACTION_REQUESTED = "RISK_ACTION_REQUESTED"
    VERIFICATION_RECORDED = "VERIFICATION_RECORDED"
    TRANSITION_REJECTED = "TRANSITION_REJECTED"


class TransactionAuditEvent(BaseModel):
    """One immutable entry in a transaction's audit trail.

    Every state change produces one of these, and so does every *refused* state
    change. Recording the refusals matters as much as recording the successes:
    an attacker probing for a way out of HELD leaves exactly that trace, and an
    audit log that only holds successful operations would not show it.
    """

    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(description="Unique audit event identifier")
    transaction_id: str = Field(description="Transaction this event belongs to")
    sequence: int = Field(description="Monotonic sequence number within the transaction")

    event_type: AuditEventType = Field(description="Kind of audit event")
    from_state: Optional[TransactionState] = Field(default=None, description="State before the change")
    to_state: Optional[TransactionState] = Field(default=None, description="State after the change")

    actor: str = Field(description="Who caused this: 'RISK_ENGINE' | 'OPERATOR' | 'SYSTEM' | 'DEMO'")
    reason: str = Field(description="Human-readable reason for the event")
    reason_codes: List[str] = Field(default_factory=list, description="Machine-readable reason codes")

    session_id: Optional[str] = Field(default=None, description="Voice session that triggered this, if any")
    risk_action: Optional[PolicyAction] = Field(default=None, description="Risk action requested, if any")

    environment: str = Field(
        default=DEMO_ENVIRONMENT_LABEL,
        description="Environment label; always the demo environment",
    )
    timestamp: datetime = Field(description="UTC timestamp")


class DemoTransaction(BaseModel):
    """A simulated transaction in the DEMO TRANSACTION ENVIRONMENT.

    Not a payment instruction. Holds no account numbers, no card data and no
    routing information, because the demo has no need of them and inventing
    them would make the object look more like a real banking payload than it is.
    """

    model_config = ConfigDict(extra="forbid")

    transaction_id: str = Field(description="Unique demo transaction identifier")
    environment: str = Field(
        default=DEMO_ENVIRONMENT_LABEL,
        description="Environment label; always the demo environment",
    )
    disclaimer: str = Field(
        default=NOT_A_REAL_BANKING_INTEGRATION,
        description="Restated disclaimer travelling with the serialised record",
    )

    caller_identity: str = Field(description="Claimed identity of the caller requesting this")
    amount: Decimal = Field(description="Simulated transaction amount")
    currency: str = Field(default="USD", description="Currency code of the simulated amount")

    beneficiary: str = Field(description="Simulated beneficiary name or reference")
    beneficiary_novelty: BeneficiaryNovelty = Field(
        default=BeneficiaryNovelty.UNKNOWN,
        description="Whether this beneficiary has been used before",
    )

    transaction_type: Optional[str] = Field(default=None, description="Declared transaction type")
    state: TransactionState = Field(default=TransactionState.PENDING, description="Current state")

    session_id: Optional[str] = Field(default=None, description="Associated voice session, if any")

    #: Set when a hold is placed, cleared when it is released. Present so the UI
    #: can explain a hold without walking the whole audit trail.
    hold_reason: Optional[str] = Field(default=None, description="Why this transaction is held")
    verification_reference: Optional[str] = Field(
        default=None, description="Reference for the verification that released a hold"
    )

    #: Every risk action ever requested against this transaction, in order.
    #: Kept because a transaction that was held, released, then held again is a
    #: materially different story from one that was held once.
    risk_actions: List[PolicyAction] = Field(
        default_factory=list, description="Risk actions requested against this transaction"
    )

    created_at: datetime = Field(description="UTC creation timestamp")
    updated_at: datetime = Field(description="UTC timestamp of the most recent change")

    @property
    def is_terminal(self) -> bool:
        """True when no further state change is legal."""
        return self.state in TERMINAL_STATES

    @property
    def is_held(self) -> bool:
        return self.state == TransactionState.HELD
