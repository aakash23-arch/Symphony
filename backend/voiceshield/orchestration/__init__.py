"""Analysis orchestration.

The only package permitted to compose every analysis layer: it wires L1 frames
through L2 features, L3 experts, L4 fusion/context/risk and, when configured,
L5 transaction actions. Sits above the layers and below the API.
"""

from .analysis import CORE_SPOOF_EXPERTS, AnalysisOrchestrator, EventSink
from .config import OrchestrationConfig
from .errors import (
    ANALYSIS_STATE_NOT_FOUND,
    RISK_NOT_YET_AVAILABLE,
    AnalysisStateNotFound,
    RiskNotYetAvailable,
)
from .state import SessionAnalysisState, SessionAnalysisStore
from .timeline import TimelineRecorder

__all__ = [
    "CORE_SPOOF_EXPERTS",
    "AnalysisOrchestrator",
    "EventSink",
    "OrchestrationConfig",
    "ANALYSIS_STATE_NOT_FOUND",
    "RISK_NOT_YET_AVAILABLE",
    "AnalysisStateNotFound",
    "RiskNotYetAvailable",
    "SessionAnalysisState",
    "SessionAnalysisStore",
    "TimelineRecorder",
]
