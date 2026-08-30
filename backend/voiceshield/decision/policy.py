"""Policy engine interface (C-40)."""

from abc import ABC, abstractmethod
from typing import List, Tuple
from voiceshield.contracts import PolicyAction, RiskAssessment, TransactionTier


class PolicyEngine(ABC):
    """Abstract interface for explicit, inspectable decision rules."""

    @abstractmethod
    def evaluate_policy(
        self,
        risk: RiskAssessment,
        tier: TransactionTier,
    ) -> Tuple[PolicyAction, List[str]]:
        """Apply explicit rule matrix and return recommended action and reason codes."""
        raise NotImplementedError("PolicyEngine.evaluate_policy is not implemented yet")
