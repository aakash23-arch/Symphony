"""Probability calibration interfaces (C-28)."""

from abc import ABC, abstractmethod
from typing import Dict, Optional


class Calibrator(ABC):
    """Abstract interface for probability calibration (Heuristic Shrinkage)."""

    @abstractmethod
    def calibrate(self, expert_id: str, raw_score: float) -> float:
        """Calibrate raw expert output to posterior probability."""
        raise NotImplementedError("Calibrator.calibrate is not implemented yet")

    @abstractmethod
    def is_fitted(self) -> bool:
        """Check if calibration is fitted from empirical data or prior-only."""
        raise NotImplementedError("Calibrator.is_fitted is not implemented yet")

class StandardCalibrator(Calibrator):
    """Concrete identity calibrator (passes through raw probabilities for now)."""
    
    def calibrate(self, expert_id: str, raw_score: float) -> float:
        return raw_score
        
    def is_fitted(self) -> bool:
        return False
