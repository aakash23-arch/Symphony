"""Quality-conditioned weighting interface (C-29)."""

from abc import ABC, abstractmethod
from typing import Dict, List
from voiceshield.contracts import EvidenceVector, ExpertStatus
from .config import FusionConfig


class QualityConditionedWeighting(ABC):
    """Abstract interface for computing expert fusion weights dynamically conditioned on audio quality."""

    @abstractmethod
    def compute_weights(self, evidence: EvidenceVector) -> Dict[str, float]:
        """Compute normalized expert weights based on SNR, codec, and expert status."""
        pass

class StandardQualityConditionedWeighting(QualityConditionedWeighting):
    """Concrete implementation of quality-conditioned weighting."""
    
    def __init__(self, config: FusionConfig):
        self.config = config

    def compute_weights(self, evidence: EvidenceVector) -> Dict[str, float]:
        raw_weights = {}
        q_t = evidence.q_t if evidence.q_t is not None else 1.0
        
        for expert_id, base_w in self.config.expert_weights.items():
            status = evidence.expert_statuses.get(expert_id, ExpertStatus.MODEL_UNAVAILABLE)
            
            if status != ExpertStatus.OK:
                raw_weights[expert_id] = 0.0
                continue
                
            c_i = evidence.expert_confidences.get(expert_id)
            if c_i is None:
                c_i = 1.0
                
            alpha = self.config.quality_sensitivities.get(expert_id, 0.0)
            
            # Quality degradation: w' = w_base * c_i * (1 - alpha * (1 - q_t))
            # Ensures weight doesn't go below 0
            q_factor = max(0.0, 1.0 - alpha * (1.0 - q_t))
            
            w_prime = base_w * c_i * q_factor
            raw_weights[expert_id] = w_prime
            
        # Normalize
        total_w = sum(raw_weights.values())
        if total_w > 0:
            return {k: v / total_w for k, v in raw_weights.items()}
            
        return {k: 0.0 for k in raw_weights.keys()}
