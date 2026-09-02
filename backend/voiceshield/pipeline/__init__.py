"""Modular Audio Anti-Spoofing Pipeline Package."""

from .calibration import ConfidenceCalibrator
from .contracts import (
    AcousticFeaturesSummary,
    AudioFormat,
    AudioSegment,
    AudioValidationResult,
    CalibratedScore,
    DetectorResult,
    ForensicAnomaly,
    ForensicEvidence,
    FusedScore,
    InferenceRequest,
    InferenceResponse,
    PolicyVerdict,
    PreprocessingSummary,
    RiskBand,
    RiskDecisionResult,
    RiskFactorAttribution,
    SegmentInferenceScore,
    StructuredExplanation,
    TransactionContext,
    ValidationStatus,
)
from .decision import DecisionEngine
from .detectors import (
    AcousticForensicDetector,
    BaseDetector,
    DetectorRegistry,
    Wav2Vec2DeepfakeDetector,
    get_default_detector_registry,
)
from .evidence import EvidenceEngine
from .explanation import ExplanationEngine
from .features import FeatureExtractor
from .fusion import ScoreFusion
from .orchestrator import InferenceOrchestrator, default_orchestrator
from .preprocessor import AudioPreprocessor
from .validator import AudioValidator

__all__ = [
    "AudioValidator",
    "AudioPreprocessor",
    "FeatureExtractor",
    "BaseDetector",
    "Wav2Vec2DeepfakeDetector",
    "AcousticForensicDetector",
    "DetectorRegistry",
    "get_default_detector_registry",
    "EvidenceEngine",
    "ScoreFusion",
    "ConfidenceCalibrator",
    "DecisionEngine",
    "ExplanationEngine",
    "InferenceOrchestrator",
    "default_orchestrator",
    "InferenceRequest",
    "InferenceResponse",
    "AudioValidationResult",
    "PreprocessingSummary",
    "AcousticFeaturesSummary",
    "DetectorResult",
    "ForensicEvidence",
    "FusedScore",
    "CalibratedScore",
    "RiskDecisionResult",
    "StructuredExplanation",
    "PolicyVerdict",
    "RiskBand",
]
