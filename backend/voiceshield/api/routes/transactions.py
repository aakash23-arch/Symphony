"""DEMO TRANSACTION ENVIRONMENT - REST routes (C-47, §7).

    THIS IS NOT A REAL BANKING INTEGRATION.
    No funds move. No external banking system is contacted.

Every response carries the environment label and disclaimer in its body, so a
client cannot consume this API without also receiving the statement that it is
simulated.
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field

from voiceshield.contracts import (
    DEMO_ENVIRONMENT_LABEL,
    NOT_A_REAL_BANKING_INTEGRATION,
    BeneficiaryNovelty,
    DemoTransaction,
    PolicyAction,
    TimelineEventKind,
    TransactionAuditEvent,
    TransactionState,
)
from voiceshield.contracts.errors import VoiceShieldException

from ..runtime import get_runtime



#: Risk actions the API accepts. Narrower than PolicyAction: WARN and
#: ACTIVE_LIVENESS are voice-session concerns that say nothing about a
#: transaction, so they are not exposed on this surface.
ACCEPTED_RISK_ACTIONS = {
    PolicyAction.ALLOW,
    PolicyAction.STEP_UP,
    PolicyAction.HOLD,
    PolicyAction.ESCALATE,
}


# --- request/response models --------------------------------------------------


class CreateTransactionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    caller_identity: str = Field(description="Claimed identity of the caller")
    amount: Decimal = Field(description="Simulated amount; must be positive")
    beneficiary: str = Field(description="Simulated beneficiary reference")
    beneficiary_novelty: BeneficiaryNovelty = Field(default=BeneficiaryNovelty.UNKNOWN)
    currency: str = Field(default="USD")
    transaction_type: Optional[str] = Field(default=None)
    session_id: Optional[str] = Field(default=None, description="Associated voice session")


class UpdateStateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    state: TransactionState = Field(description="Target state")
    reason: str = Field(default="State updated by operator")
    actor: str = Field(default="OPERATOR")


class HoldRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str = Field(default="Held pending verification")
    actor: str = Field(default="OPERATOR")
    session_id: Optional[str] = Field(default=None)


class ReleaseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    verification_reference: str = Field(
        description="What was verified; required, and recorded in the audit trail"
    )
    approve: bool = Field(
        default=True,
        description="True releases to APPROVED; False releases to REJECTED after failed verification",
    )
    actor: str = Field(default="OPERATOR")
    session_id: Optional[str] = Field(default=None)


class RiskActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: PolicyAction = Field(description="One of ALLOW, STEP_UP, HOLD, ESCALATE")
    reason: str = Field(default="Requested by risk engine")
    session_id: Optional[str] = Field(default=None)


class TransactionResponse(BaseModel):
    """A transaction plus the demo labelling that must travel with it."""

    model_config = ConfigDict(extra="forbid")
    environment: str = Field(default=DEMO_ENVIRONMENT_LABEL)
    disclaimer: str = Field(default=NOT_A_REAL_BANKING_INTEGRATION)
    transaction: DemoTransaction


class TransactionListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    environment: str = Field(default=DEMO_ENVIRONMENT_LABEL)
    disclaimer: str = Field(default=NOT_A_REAL_BANKING_INTEGRATION)
    transactions: List[DemoTransaction]


class AuditTrailResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    environment: str = Field(default=DEMO_ENVIRONMENT_LABEL)
    disclaimer: str = Field(default=NOT_A_REAL_BANKING_INTEGRATION)
    transaction_id: str
    events: List[TransactionAuditEvent]


# --- helpers ------------------------------------------------------------------


def _raise_http(exc: VoiceShieldException) -> None:
    """Translate a typed simulator error into the standard HTTP envelope."""
    raise HTTPException(status_code=exc.status_code, detail=f"{exc.code}: {exc.message}") from exc


def _wrap(transaction: DemoTransaction) -> TransactionResponse:
    return TransactionResponse(transaction=transaction)


def _record_on_timeline(
    session_id: Optional[str],
    transaction: DemoTransaction,
    kind: TimelineEventKind,
    label: str,
    detail: Optional[str] = None,
) -> None:
    """Mirror an operator action onto the call timeline.

    The REST mutation returns the new state to its own caller, but pushes
    nothing, so a second console would never learn about it. Appending the same
    entry the orchestrator's auto-hold appends both closes that gap and keeps
    the audit narrative complete: without it, a manually held transaction is
    invisible in the call's history.
    """
    if not session_id:
        return
    get_runtime().orchestrator.record_transaction_event(
        session_id, transaction.transaction_id, kind, label, detail
    )


# --- routes -------------------------------------------------------------------


def build_router(prefix: str, suffix: str) -> APIRouter:
    """Build the demo transaction router at ``prefix``.

    ``suffix`` disambiguates operation ids between the two mounts, so the
    generated OpenAPI document stays valid with both surfaces present.
    """
    router = APIRouter(prefix=prefix, tags=["Demo Transaction Environment"])

    @router.post("", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED,
                 summary="Create a simulated transaction (DEMO TRANSACTION ENVIRONMENT)",
                 operation_id=f"create_transaction{suffix}")
    async def create_transaction(request: CreateTransactionRequest) -> TransactionResponse:
        """Create a simulated transaction in PENDING. No real funds move."""
        simulator = get_runtime().transactions
        try:
            transaction = simulator.create_transaction(
                caller_identity=request.caller_identity,
                amount=request.amount,
                beneficiary=request.beneficiary,
                beneficiary_novelty=request.beneficiary_novelty,
                currency=request.currency,
                transaction_type=request.transaction_type,
                session_id=request.session_id,
            )
        except VoiceShieldException as exc:
            _raise_http(exc)
        return _wrap(transaction)


    @router.get("", response_model=TransactionListResponse,
                summary="List simulated transactions",
                 operation_id=f"list_transactions{suffix}")
    async def list_transactions(
        session_id: Optional[str] = Query(default=None, description="Filter to one voice session"),
    ) -> TransactionListResponse:
        """List simulated transactions, newest last."""
        simulator = get_runtime().transactions
        return TransactionListResponse(transactions=simulator.list_transactions(session_id))


    @router.get("/{transaction_id}", response_model=TransactionResponse,
                summary="View a simulated transaction",
                 operation_id=f"get_transaction{suffix}")
    async def get_transaction(transaction_id: str) -> TransactionResponse:
        """Retrieve one simulated transaction."""
        simulator = get_runtime().transactions
        try:
            transaction = simulator.get_transaction(transaction_id)
        except VoiceShieldException as exc:
            _raise_http(exc)
        return _wrap(transaction)


    @router.get("/{transaction_id}/audit", response_model=AuditTrailResponse,
                summary="Read the audit trail for a simulated transaction",
                 operation_id=f"get_transaction_audit{suffix}")
    async def get_audit_trail(transaction_id: str) -> AuditTrailResponse:
        """Return every audit event for this transaction, including refused changes."""
        simulator = get_runtime().transactions
        try:
            events = simulator.get_audit_trail(transaction_id)
        except VoiceShieldException as exc:
            _raise_http(exc)
        return AuditTrailResponse(transaction_id=transaction_id, events=events)


    @router.patch("/{transaction_id}/state", response_model=TransactionResponse,
                  summary="Update the state of a simulated transaction",
                 operation_id=f"update_transaction_state{suffix}")
    async def update_transaction_state(
        transaction_id: str, request: UpdateStateRequest
    ) -> TransactionResponse:
        """Move a transaction along a legal edge. Illegal transitions return 409."""
        simulator = get_runtime().transactions
        try:
            transaction = simulator.update_state(
                transaction_id,
                request.state,
                actor=request.actor,
                reason=request.reason,
            )
        except VoiceShieldException as exc:
            _raise_http(exc)
        return _wrap(transaction)


    @router.post("/{transaction_id}/hold", response_model=TransactionResponse,
                 summary="Place a simulated transaction on hold",
                 operation_id=f"hold_transaction{suffix}")
    async def hold_transaction(transaction_id: str, request: HoldRequest) -> TransactionResponse:
        """Place a hold. Holding an already-held transaction is idempotent."""
        simulator = get_runtime().transactions
        try:
            transaction = simulator.hold_transaction(
                transaction_id,
                reason=request.reason,
                actor=request.actor,
                session_id=request.session_id,
            )
        except VoiceShieldException as exc:
            _raise_http(exc)
        _record_on_timeline(
            request.session_id,
            transaction,
            TimelineEventKind.TRANSACTION_HELD,
            "Demo transaction held by operator",
            request.reason,
        )
        return _wrap(transaction)


    @router.post("/{transaction_id}/release", response_model=TransactionResponse,
                 summary="Release a held simulated transaction after verification",
                 operation_id=f"release_transaction{suffix}")
    async def release_transaction(
        transaction_id: str, request: ReleaseRequest
    ) -> TransactionResponse:
        """Release a hold. Requires a verification reference, which is audited."""
        simulator = get_runtime().transactions
        try:
            transaction = simulator.release_transaction(
                transaction_id,
                request.verification_reference,
                approve=request.approve,
                actor=request.actor,
                session_id=request.session_id,
            )
        except VoiceShieldException as exc:
            _raise_http(exc)
        _record_on_timeline(
            request.session_id,
            transaction,
            TimelineEventKind.TRANSACTION_RELEASED,
            f"Demo transaction released to {transaction.state.value}",
            f"verified via {request.verification_reference}",
        )
        return _wrap(transaction)


    @router.post("/{transaction_id}/risk-action", response_model=TransactionResponse,
                 summary="Apply a risk engine action to a simulated transaction",
                 operation_id=f"request_transaction_risk_action{suffix}")
    async def request_risk_action(
        transaction_id: str, request: RiskActionRequest
    ) -> TransactionResponse:
        """Apply HOLD, STEP_UP, ESCALATE or ALLOW from the risk engine.

        ALLOW and STEP_UP are recorded without moving the state machine: the risk
        engine's authority is to object, not to execute (§9.3).
        """
        if request.action not in ACCEPTED_RISK_ACTIONS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"UNSUPPORTED_RISK_ACTION: {request.action.value} is not applicable to a "
                    f"transaction; expected one of "
                    f"{sorted(a.value for a in ACCEPTED_RISK_ACTIONS)}"
                ),
            )
        simulator = get_runtime().transactions
        try:
            transaction = simulator.request_risk_action(
                transaction_id,
                request.action,
                reason=request.reason,
                session_id=request.session_id,
            )
        except VoiceShieldException as exc:
            _raise_http(exc)
        return _wrap(transaction)

    return router


#: Spec-aligned surface, and the one the existing tests address.
router = build_router("/v1/demo/transactions", "_v1")

#: The surface requested in Gate 10. Same handlers, different mount.
api_router = build_router("/api/transactions", "_api")
