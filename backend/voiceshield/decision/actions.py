"""Action emitter interface (C-42)."""

from abc import ABC, abstractmethod
from voiceshield.contracts import Decision, PolicyAction, RiskAssessment, RiskState, TransactionTier, VoiceBelief


class ActionEmitter(ABC):
    """Abstract interface for constructing action-grade Decision objects."""

    @abstractmethod
    def build_decision(
        self,
        session_id: str,
        belief: VoiceBelief,
        risk: RiskAssessment,
        tier: TransactionTier,
        action: PolicyAction,
        state: RiskState,
        reason_codes: list[str],
    ) -> Decision:
        """Construct structured Decision object without executing external side-effects."""
        raise NotImplementedError("ActionEmitter.build_decision is not implemented yet")
