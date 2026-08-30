"""Risk state machine interface (C-41)."""

from abc import ABC, abstractmethod
from voiceshield.contracts import PolicyAction, RiskState


class RiskStateMachine(ABC):
    """Abstract interface for session-level risk state transitions."""

    @abstractmethod
    def transition(
        self,
        current_state: RiskState,
        action: PolicyAction,
    ) -> RiskState:
        """Evaluate and return valid next state adhering to the transition graph."""
        raise NotImplementedError("RiskStateMachine.transition is not implemented yet")

    @abstractmethod
    def is_valid_transition(self, current_state: RiskState, next_state: RiskState) -> bool:
        """Check if transition is legally permitted."""
        raise NotImplementedError("RiskStateMachine.is_valid_transition is not implemented yet")
