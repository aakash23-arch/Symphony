"""Models module (L3 - ML / evidence generation).

Public surface. Note that importing this package does NOT require torch: the
experts are constructible, and the availability report truthful, on a machine
with no ML stack. Only the adapters touch an ML library, lazily.
"""

from .base import Expert
from .bootstrap import build_experts, collect_model_versions, register_experts
from .buffering import RollingPCMBuffer
from .e1_spectral import E1SpectralExpert
from .e2_raw import E2RawWaveformExpert
from .e3_ssl import E3SSLExpert
from .e4_speaker import E4SpeakerExpert
from .e5_prosody import E5ProsodyExpert
from .e6_replay import E6ReplayExpert
from .interfaces import (
    MIN_SAMPLES_SPOOF,
    MIN_SAMPLES_XVECTOR,
    AntiSpoofingModel,
    ModelDescriptor,
    ModelInferenceResult,
    ProsodyModel,
    RepresentationModel,
    SpeakerVerificationModel,
)
from .loader import ManifestModelLoader, ModelLoader, model_loader
from .registry import ALL_EXPERT_IDS, ExpertRegistry, expert_registry

__all__ = [
    # Base + registry
    "Expert",
    "ExpertRegistry",
    "expert_registry",
    "ALL_EXPERT_IDS",
    # Adapter protocols (the ML-library-agnostic boundary)
    "AntiSpoofingModel",
    "SpeakerVerificationModel",
    "ProsodyModel",
    "RepresentationModel",
    "ModelInferenceResult",
    "ModelDescriptor",
    "MIN_SAMPLES_XVECTOR",
    "MIN_SAMPLES_SPOOF",
    # Experts
    "E1SpectralExpert",
    "E2RawWaveformExpert",
    "E3SSLExpert",
    "E4SpeakerExpert",
    "E5ProsodyExpert",
    "E6ReplayExpert",
    # Loading / lifecycle
    "ModelLoader",
    "ManifestModelLoader",
    "model_loader",
    "RollingPCMBuffer",
    "build_experts",
    "register_experts",
    "collect_model_versions",
]
