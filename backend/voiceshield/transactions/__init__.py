"""DEMO TRANSACTION ENVIRONMENT (Phase 9).

    THIS IS NOT A REAL BANKING INTEGRATION.
    No funds move. No external banking system is contacted.

A deterministic, in-memory transaction simulator that gives the risk engine
something consequential to act on during the demo.
"""

from .errors import (
    ILLEGAL_TRANSACTION_TRANSITION,
    TRANSACTION_NOT_FOUND,
    TRANSACTION_NOT_HELD,
    VERIFICATION_REQUIRED,
    IllegalTransactionTransition,
    InvalidTransactionAmount,
    TransactionNotFound,
    TransactionNotHeld,
    VerificationRequired,
)
from .simulator import RISK_ACTION_TO_STATE, TransactionSimulator

__all__ = [
    "ILLEGAL_TRANSACTION_TRANSITION",
    "TRANSACTION_NOT_FOUND",
    "TRANSACTION_NOT_HELD",
    "VERIFICATION_REQUIRED",
    "IllegalTransactionTransition",
    "InvalidTransactionAmount",
    "TransactionNotFound",
    "TransactionNotHeld",
    "VerificationRequired",
    "RISK_ACTION_TO_STATE",
    "TransactionSimulator",
]
