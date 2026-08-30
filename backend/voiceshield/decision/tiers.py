"""Transaction sensitivity interface (C-39)."""

from abc import ABC, abstractmethod
from typing import Dict
from voiceshield.contracts import TransactionContext, TransactionTier


class TransactionSensitivity(ABC):
    """Abstract interface for mapping transaction context to sensitivity tier and thresholds."""

    @abstractmethod
    def evaluate_tier(self, transaction: TransactionContext) -> TransactionTier:
        """Map transaction context to sensitivity tiers 0-4 (defaults to 4 on unknown)."""
        raise NotImplementedError("TransactionSensitivity.evaluate_tier is not implemented yet")

    @abstractmethod
    def get_tier_thresholds(self, tier: TransactionTier) -> Dict[str, float]:
        """Return warning and critical thresholds conditioned on tier."""
        raise NotImplementedError("TransactionSensitivity.get_tier_thresholds is not implemented yet")
