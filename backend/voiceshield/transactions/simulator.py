"""DEMO TRANSACTION ENVIRONMENT - deterministic transaction simulator.

    THIS IS NOT A REAL BANKING INTEGRATION.
    No funds move. No external banking system is contacted.

An in-memory, single-process store of simulated transactions plus the state
machine that governs them. Its purpose in the demo is to give the risk engine
something to act on, so that HOLD and ESCALATE are visibly consequential rather
than advisory text on a dashboard.

Determinism
-----------
Given the same sequence of calls, this produces the same states and the same
audit trail. Identifiers and timestamps are the only varying parts, and both
are injectable (``id_factory``, ``clock``) so a test or a scripted demo can
pin them. Nothing here samples randomness or reads wall-clock time except
through ``clock``.

What it deliberately does not model
-----------------------------------
Account numbers, balances, card data, routing information, settlement, fees and
reversal accounting are all absent. The demo needs none of them, and inventing
them would make this object look far more like a real payment instruction than
it is.
"""

import itertools
import uuid
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Callable, Dict, List, Optional

from voiceshield.contracts import (
    DEMO_ENVIRONMENT_LABEL,
    AuditEventType,
    BeneficiaryNovelty,
    DemoTransaction,
    PolicyAction,
    TransactionAuditEvent,
    TransactionState,
)
from voiceshield.contracts.transaction import LEGAL_TRANSITIONS, TERMINAL_STATES
from voiceshield.obs.logging import get_logger

from .errors import (
    IllegalTransactionTransition,
    InvalidTransactionAmount,
    TransactionNotFound,
    TransactionNotHeld,
    VerificationRequired,
)

logger = get_logger("voiceshield.transactions.simulator")

#: How each risk action maps onto the transaction state machine.
#:
#: ALLOW and STEP_UP deliberately map to None - neither is a state change.
#: ALLOW is the absence of an objection, not an instruction to approve; a
#: transaction still needs an explicit approval from an operator or from the
#: demo script. STEP_UP is a request for more evidence about the caller, which
#: says nothing yet about the transaction's fate. Collapsing either one into an
#: automatic approval would let the risk engine execute payments, which is
#: exactly the authority §9.3 withholds from it.
RISK_ACTION_TO_STATE: Dict[PolicyAction, Optional[TransactionState]] = {
    PolicyAction.ALLOW: None,
    PolicyAction.WARN: None,
    PolicyAction.ACTIVE_LIVENESS: None,
    PolicyAction.STEP_UP: None,
    PolicyAction.HOLD: TransactionState.HELD,
    PolicyAction.ESCALATE: TransactionState.HELD,
}


def _default_clock() -> datetime:
    return datetime.now(timezone.utc)


class TransactionSimulator:
    """In-memory demo transaction store with an audited state machine.

    Single-process and not thread-safe, matching ``SessionManager``. The demo
    runs one API process; adding a lock here would imply a concurrency story
    this build does not actually have.
    """

    def __init__(
        self,
        clock: Optional[Callable[[], datetime]] = None,
        id_factory: Optional[Callable[[], str]] = None,
    ):
        self._clock = clock or _default_clock
        self._id_factory = id_factory or (lambda: uuid.uuid4().hex)
        self._transactions: Dict[str, DemoTransaction] = {}
        self._audit: Dict[str, List[TransactionAuditEvent]] = {}
        self._sequences: Dict[str, itertools.count] = {}

    # --- audit ---------------------------------------------------------------

    def _record(
        self,
        transaction_id: str,
        event_type: AuditEventType,
        actor: str,
        reason: str,
        *,
        from_state: Optional[TransactionState] = None,
        to_state: Optional[TransactionState] = None,
        reason_codes: Optional[List[str]] = None,
        session_id: Optional[str] = None,
        risk_action: Optional[PolicyAction] = None,
    ) -> TransactionAuditEvent:
        """Append one audit event. Never raises, never skipped."""
        sequence = next(self._sequences.setdefault(transaction_id, itertools.count()))
        event = TransactionAuditEvent(
            event_id=self._id_factory(),
            transaction_id=transaction_id,
            sequence=sequence,
            event_type=event_type,
            from_state=from_state,
            to_state=to_state,
            actor=actor,
            reason=reason,
            reason_codes=list(reason_codes or []),
            session_id=session_id,
            risk_action=risk_action,
            environment=DEMO_ENVIRONMENT_LABEL,
            timestamp=self._clock(),
        )
        self._audit.setdefault(transaction_id, []).append(event)
        logger.info(
            "demo transaction audit event",
            extra={
                "extra_fields": {
                    "environment": DEMO_ENVIRONMENT_LABEL,
                    "transaction_id": transaction_id,
                    "event_type": event_type.value,
                    "from_state": from_state.value if from_state else None,
                    "to_state": to_state.value if to_state else None,
                    "actor": actor,
                }
            },
        )
        return event

    # --- creation and retrieval ----------------------------------------------

    def create_transaction(
        self,
        caller_identity: str,
        amount,
        beneficiary: str,
        *,
        beneficiary_novelty: BeneficiaryNovelty = BeneficiaryNovelty.UNKNOWN,
        currency: str = "USD",
        transaction_type: Optional[str] = None,
        session_id: Optional[str] = None,
        transaction_id: Optional[str] = None,
    ) -> DemoTransaction:
        """Create a simulated transaction in PENDING.

        Every transaction starts PENDING. There is no path that creates one
        already approved: the demo's whole value is showing the decision being
        made, and a pre-approved transaction would have skipped it.
        """
        try:
            parsed = Decimal(str(amount))
        except (InvalidOperation, ValueError, TypeError) as exc:
            raise InvalidTransactionAmount(f"{amount!r} is not a number", session_id) from exc
        if parsed <= 0:
            raise InvalidTransactionAmount(f"{parsed} is not positive", session_id)

        tid = transaction_id or self._id_factory()
        if tid in self._transactions:
            raise IllegalTransactionTransition(
                tid, "NONE", TransactionState.PENDING.value,
                reason="TRANSACTION_ALREADY_EXISTS", session_id=session_id,
            )

        now = self._clock()
        transaction = DemoTransaction(
            transaction_id=tid,
            caller_identity=caller_identity,
            amount=parsed,
            currency=currency,
            beneficiary=beneficiary,
            beneficiary_novelty=beneficiary_novelty,
            transaction_type=transaction_type,
            state=TransactionState.PENDING,
            session_id=session_id,
            created_at=now,
            updated_at=now,
        )
        self._transactions[tid] = transaction
        self._record(
            tid,
            AuditEventType.TRANSACTION_CREATED,
            actor="DEMO",
            reason=f"Simulated transaction created for {caller_identity}",
            to_state=TransactionState.PENDING,
            reason_codes=["TRANSACTION_CREATED"],
            session_id=session_id,
        )
        return transaction

    def get_transaction(self, transaction_id: str) -> DemoTransaction:
        """Return one transaction, or raise TransactionNotFound."""
        transaction = self._transactions.get(transaction_id)
        if transaction is None:
            raise TransactionNotFound(transaction_id)
        return transaction

    def exists(self, transaction_id: str) -> bool:
        return transaction_id in self._transactions

    def list_transactions(self, session_id: Optional[str] = None) -> List[DemoTransaction]:
        """List transactions, optionally filtered to one voice session."""
        values = list(self._transactions.values())
        if session_id is not None:
            values = [t for t in values if t.session_id == session_id]
        return sorted(values, key=lambda t: (t.created_at, t.transaction_id))

    def get_audit_trail(self, transaction_id: str) -> List[TransactionAuditEvent]:
        """Return the ordered audit trail for one transaction."""
        if transaction_id not in self._transactions:
            raise TransactionNotFound(transaction_id)
        return list(self._audit.get(transaction_id, []))

    # --- state machine -------------------------------------------------------

    @staticmethod
    def is_legal_transition(from_state: TransactionState, to_state: TransactionState) -> bool:
        """True when ``from_state -> to_state`` is an edge in the graph."""
        return to_state in LEGAL_TRANSITIONS.get(from_state, set())

    def _apply(
        self,
        transaction_id: str,
        target: TransactionState,
        *,
        actor: str,
        reason: str,
        event_type: AuditEventType = AuditEventType.STATE_CHANGED,
        reason_codes: Optional[List[str]] = None,
        session_id: Optional[str] = None,
        risk_action: Optional[PolicyAction] = None,
    ) -> DemoTransaction:
        """Apply one guarded state change, auditing both outcomes.

        A refused transition is recorded before the exception is raised, so the
        attempt survives in the trail even though the state did not move.
        """
        transaction = self.get_transaction(transaction_id)
        current = transaction.state

        if not self.is_legal_transition(current, target):
            self._record(
                transaction_id,
                AuditEventType.TRANSITION_REJECTED,
                actor=actor,
                reason=f"Refused illegal transition {current.value} -> {target.value}: {reason}",
                from_state=current,
                to_state=target,
                reason_codes=(list(reason_codes or []) + ["ILLEGAL_TRANSACTION_TRANSITION"]),
                session_id=session_id or transaction.session_id,
                risk_action=risk_action,
            )
            raise IllegalTransactionTransition(
                transaction_id,
                current.value,
                target.value,
                reason=("TRANSACTION_TERMINAL" if current in TERMINAL_STATES
                        else "ILLEGAL_TRANSACTION_TRANSITION"),
                session_id=session_id or transaction.session_id,
            )

        updated = transaction.model_copy(update={"state": target, "updated_at": self._clock()})
        self._transactions[transaction_id] = updated
        self._record(
            transaction_id,
            event_type,
            actor=actor,
            reason=reason,
            from_state=current,
            to_state=target,
            reason_codes=reason_codes,
            session_id=session_id or transaction.session_id,
            risk_action=risk_action,
        )
        return updated

    def update_state(
        self,
        transaction_id: str,
        target: TransactionState,
        *,
        actor: str = "OPERATOR",
        reason: str = "State updated",
        reason_codes: Optional[List[str]] = None,
        session_id: Optional[str] = None,
    ) -> DemoTransaction:
        """Move a transaction to ``target``, if that edge is legal."""
        return self._apply(
            transaction_id,
            target,
            actor=actor,
            reason=reason,
            reason_codes=reason_codes,
            session_id=session_id,
        )

    def hold_transaction(
        self,
        transaction_id: str,
        *,
        reason: str = "Held pending verification",
        actor: str = "OPERATOR",
        reason_codes: Optional[List[str]] = None,
        session_id: Optional[str] = None,
        risk_action: Optional[PolicyAction] = None,
    ) -> DemoTransaction:
        """Place a transaction on hold.

        Holding an already-held transaction is idempotent rather than an error:
        two risk updates in one call both concluding HOLD is normal, and the
        second must not fail. The repeat is still audited so the trail shows it
        happened.
        """
        transaction = self.get_transaction(transaction_id)
        if transaction.state == TransactionState.HELD:
            self._record(
                transaction_id,
                AuditEventType.HOLD_PLACED,
                actor=actor,
                reason=f"Hold reaffirmed: {reason}",
                from_state=TransactionState.HELD,
                to_state=TransactionState.HELD,
                reason_codes=(list(reason_codes or []) + ["HOLD_ALREADY_ACTIVE"]),
                session_id=session_id,
                risk_action=risk_action,
            )
            return transaction

        held = self._apply(
            transaction_id,
            TransactionState.HELD,
            actor=actor,
            reason=reason,
            event_type=AuditEventType.HOLD_PLACED,
            reason_codes=(list(reason_codes or []) + ["HOLD_PLACED"]),
            session_id=session_id,
            risk_action=risk_action,
        )
        held = held.model_copy(update={"hold_reason": reason})
        self._transactions[transaction_id] = held
        return held

    def release_transaction(
        self,
        transaction_id: str,
        verification_reference: str,
        *,
        approve: bool = True,
        actor: str = "OPERATOR",
        reason: Optional[str] = None,
        reason_codes: Optional[List[str]] = None,
        session_id: Optional[str] = None,
    ) -> DemoTransaction:
        """Release a held transaction after verification.

        ``verification_reference`` is mandatory: this is the operation that
        undoes a protective decision, so the trail must record what was
        verified. ``approve=False`` releases the hold into REJECTED, for the
        case where verification came back negative.
        """
        transaction = self.get_transaction(transaction_id)
        if transaction.state != TransactionState.HELD:
            self._record(
                transaction_id,
                AuditEventType.TRANSITION_REJECTED,
                actor=actor,
                reason=f"Release refused: transaction is {transaction.state.value}, not HELD",
                from_state=transaction.state,
                reason_codes=["TRANSACTION_NOT_HELD"],
                session_id=session_id,
            )
            raise TransactionNotHeld(transaction_id, transaction.state.value, session_id)

        if not verification_reference or not str(verification_reference).strip():
            self._record(
                transaction_id,
                AuditEventType.TRANSITION_REJECTED,
                actor=actor,
                reason="Release refused: no verification reference supplied",
                from_state=transaction.state,
                reason_codes=["VERIFICATION_REQUIRED"],
                session_id=session_id,
            )
            raise VerificationRequired(transaction_id, session_id)

        self._record(
            transaction_id,
            AuditEventType.VERIFICATION_RECORDED,
            actor=actor,
            reason=f"Verification recorded: {verification_reference}",
            from_state=transaction.state,
            reason_codes=["VERIFICATION_RECORDED"],
            session_id=session_id,
        )

        target = TransactionState.APPROVED if approve else TransactionState.REJECTED
        released = self._apply(
            transaction_id,
            target,
            actor=actor,
            reason=reason or (
                f"Hold released after verification {verification_reference}"
                if approve
                else f"Rejected after failed verification {verification_reference}"
            ),
            event_type=AuditEventType.HOLD_RELEASED,
            reason_codes=(list(reason_codes or []) + ["HOLD_RELEASED"]),
            session_id=session_id,
        )
        released = released.model_copy(
            update={"hold_reason": None, "verification_reference": str(verification_reference)}
        )
        self._transactions[transaction_id] = released
        return released

    # --- risk engine interface -----------------------------------------------

    def request_risk_action(
        self,
        transaction_id: str,
        action: PolicyAction,
        *,
        reason: str = "Requested by risk engine",
        reason_codes: Optional[List[str]] = None,
        session_id: Optional[str] = None,
    ) -> DemoTransaction:
        """Apply a risk engine action to a transaction.

        The risk engine may request HOLD, STEP_UP, ESCALATE or ALLOW. Only the
        two that express an objection move the state machine; ALLOW and STEP_UP
        are recorded and otherwise leave the transaction where it is, because
        the engine's authority is to object, not to execute (§9.3).

        Requesting an action against an already-terminal transaction is audited
        and ignored rather than raising: a late risk update arriving after an
        operator has already resolved the case is expected, and should leave a
        trace rather than an error.
        """
        transaction = self.get_transaction(transaction_id)
        recorded = transaction.model_copy(
            update={"risk_actions": list(transaction.risk_actions) + [action]}
        )
        self._transactions[transaction_id] = recorded

        self._record(
            transaction_id,
            AuditEventType.RISK_ACTION_REQUESTED,
            actor="RISK_ENGINE",
            reason=f"Risk engine requested {action.value}: {reason}",
            from_state=transaction.state,
            reason_codes=(list(reason_codes or []) + [f"RISK_ACTION_{action.value}"]),
            session_id=session_id or transaction.session_id,
            risk_action=action,
        )

        target = RISK_ACTION_TO_STATE.get(action)
        if target is None:
            return recorded

        if recorded.state in TERMINAL_STATES:
            self._record(
                transaction_id,
                AuditEventType.TRANSITION_REJECTED,
                actor="RISK_ENGINE",
                reason=(
                    f"{action.value} arrived after the transaction reached "
                    f"{recorded.state.value}; no state change applied"
                ),
                from_state=recorded.state,
                to_state=target,
                reason_codes=["TRANSACTION_TERMINAL", f"RISK_ACTION_{action.value}"],
                session_id=session_id or transaction.session_id,
                risk_action=action,
            )
            return recorded

        return self.hold_transaction(
            transaction_id,
            reason=f"{action.value} requested by risk engine: {reason}",
            actor="RISK_ENGINE",
            reason_codes=(list(reason_codes or []) + [f"RISK_ACTION_{action.value}"]),
            session_id=session_id,
            risk_action=action,
        )

    # --- test/demo support ---------------------------------------------------

    def reset(self) -> None:
        """Drop all simulated transactions. Test and demo-reset helper."""
        self._transactions.clear()
        self._audit.clear()
        self._sequences.clear()
