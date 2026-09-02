import dataclasses
from typing import Dict

@dataclasses.dataclass(frozen=True)
class FusionConfig:
    # Base weights for each expert if available and high quality
    expert_weights: Dict[str, float] = dataclasses.field(default_factory=lambda: {
        "E1": 1.0,  # Spectro-temporal
        "E2": 1.0,  # Raw waveform
        "E3": 1.2,  # Multilingual SSL
        "E4": 1.5,  # Speaker verification (high weight when available)
        "E5": 0.5,  # Prosodic anomaly
        "E6": 0.8,  # Replay detection
    })
    
    # Sensitivity to audio quality (alpha). 1.0 = weight drops to 0 at 0 quality.
    quality_sensitivities: Dict[str, float] = dataclasses.field(default_factory=lambda: {
        "E1": 0.5,
        "E2": 0.2,
        "E3": 0.3,
        "E4": 1.0,  # Speaker ID heavily affected by poor quality
        "E5": 0.2,
        "E6": 0.5,
    })
    
    # Temporal smoothing
    smoothing_time_constant: float = 0.5 # tau in seconds
    
    # Variance penalty (lambda)
    variance_penalty: float = 2.0
    
    # Decision thresholds
    threshold_critical: float = 0.85
    threshold_suspicious: float = 0.50
    threshold_uncertain_confidence: float = 0.40
