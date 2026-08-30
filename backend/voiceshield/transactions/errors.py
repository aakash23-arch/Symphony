"""DEMO TRANSACTION ENVIRONMENT - typed errors and reason codes.

    THIS IS NOT A REAL BANKING INTEGRATION.

Follows the L1 convention: every failure is typed and carries a machine-readable
reason code, so the UI can show the refusal rather than silently doing nothing.
"""

from typing import Optional

from voiceshield.contracts.errors import VoiceShieldException

# --- Reason codes -------------------------------------------------------------

TRANSACTION_NOT_FOUND = "TRANSACTION_NOT_FOUND"
TRANSACTION_ALREADY_EXISTS = "TRANSACTION_ALREADY_EXISTS"
ILLEGAL_TRANSACTION_TRANSITION = "ILLEGAL_TRANSACTION_TRANSITION"
TRANSACTION_TERMINAL = "TRANSACTION_TERMINAL"
TRANSACTION_NOT_HELD = "TRANSACTION_NOT_HELD"
VERIFICATION_REQUIRED = "VERIFICATION_REQUIRED"
INVALID_TRANSACTION_AMOUNT = "INVALID_TRANSACTION_AMOUNT"


class TransactionNotFound(VoiceShieldException):
    """No demo transaction exists with the requested id."""

    def __init__(self, transaction_id: str, session_id: Optional[str] = None):
        super().__init__(
            code=TRANSACTION_NOT_FOUND,
            message=f"Unknown demo transaction: {transaction_id}",
            status_code=404,
            session_id=session_id,
            retriable=False,
        )
        self.reason = TRANSACTION_NOT_FOUND
        self.transaction_id = transaction_id


class IllegalTransactionTransition(VoiceShieldException):
    """The requested state change is not an edge in the transition graph.

    Carries the attempted edge so the audit trail and the API response can both
    name exactly what was refused, rather than reporting a generic conflict.
    """

    def __init__(
        self,
        transaction_id: str,
        from_state: str,
        to_state: str,
        reason: str = ILLEGAL_TRANSACTION_TRANSITION,
        session_id: Optional[str] = None,
    ):
        super().__init__(
            code=reason,
            message=(
                f"Illegal demo transaction transition {from_state} -> {to_state} "
                f"for {transaction_id}"
            ),
            status_code=409,
            session_id=session_id,
            retriable=False,
        )
        self.reason = reason
        self.transaction_id = transaction_id
        self.from_state = from_state
        self.to_state = to_state


class TransactionNotHeld(VoiceShieldException):
    """A release was attempted against a transaction that is not on hold."""

    def __init__(self, transaction_id: str, current_state: str, session_id: Optional[str] = None):
        super().__init__(
            code=TRANSACTION_NOT_HELD,
            message=(
                f"Demo transaction {transaction_id} is {current_state}, not HELD; "
                "nothing to release"
            ),
            status_code=409,
            session_id=session_id,
            retriable=False,
        )
        self.reason = TRANSACTION_NOT_HELD
        self.transaction_id = transaction_id


class VerificationRequired(VoiceShieldException):
    """A hold release was attempted without a verification reference.

    Releasing a hold is the one operation that undoes a protective decision, so
    it must record what verification justified it. An unexplained release would
    leave the audit trail unable to answer the only question that matters after
    a fraud loss: who let it through, and on what basis.
    """

    def __init__(self, transaction_id: str, session_id: Optional[str] = None):
        super().__init__(
            code=VERIFICATION_REQUIRED,
            message=(
                f"Releasing demo transaction {transaction_id} requires a "
                "verification_reference recording what was verified"
            ),
            status_code=422,
            session_id=session_id,
            retriable=False,
        )
        self.reason = VERIFICATION_REQUIRED
        self.transaction_id = transaction_id


class InvalidTransactionAmount(VoiceShieldException):
    """A non-positive or unparseable simulated amount was supplied."""

    def __init__(self, detail: str, session_id: Optional[str] = None):
        super().__init__(
            code=INVALID_TRANSACTION_AMOUNT,
            message=f"Invalid simulated transaction amount: {detail}",
            status_code=422,
            session_id=session_id,
            retriable=False,
        )
        self.reason = INVALID_TRANSACTION_AMOUNT
