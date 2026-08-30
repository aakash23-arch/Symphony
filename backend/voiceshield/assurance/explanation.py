"""Assurance and factor attribution interfaces (C-43)."""

from abc import ABC, abstractmethod
from typing import List
from voiceshield.contracts import RiskAssessment, RiskContribution, VoiceBelief


class ExplanationService(ABC):
    """Abstract interface for producing inspectable factor attribution explanations."""

    @abstractmethod
    def generate_explanation(
        self,
        belief: VoiceBelief,
        risk: RiskAssessment,
    ) -> List[RiskContribution]:
        """Generate ordered factors with signed weights distinguishing attribution from causal proof."""
        raise NotImplementedError("ExplanationService.generate_explanation is not implemented yet")
