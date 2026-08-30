"""Base expert interface (C-19, §9.1)."""

from abc import ABC, abstractmethod
from typing import List, Optional
from voiceshield.contracts import ExpertResult, ExpertStatus
from voiceshield.signal_processing import FeatureBundle


class Expert(ABC):
    """Abstract interface for all anti-spoofing and verification experts (E1..E6)."""

    def __init__(self, expert_id: str, version: str = "1.0.0"):
        self.expert_id = expert_id
        self.version = version

    @property
    @abstractmethod
    def required_features(self) -> List[str]:
        """List of feature keys required in FeatureBundle."""
        raise NotImplementedError("Expert.required_features must be specified by subclasses")

    @abstractmethod
    async def score(self, bundle: FeatureBundle) -> ExpertResult:
        """Execute model forward pass over the provided feature bundle."""
        raise NotImplementedError(f"Expert {self.expert_id}.score is not implemented yet")

    @abstractmethod
    def is_available(self) -> bool:
        """Check whether model weights are loaded and ready."""
        raise NotImplementedError("Expert.is_available must be implemented by subclasses")
