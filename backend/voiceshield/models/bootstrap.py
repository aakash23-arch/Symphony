"""Expert registration and warmup (C-19, C-27).

Builds the six experts, registers them, optionally warms up the model-backed
ones, and logs a truthful availability report.

Warmup matters: a cold load was measured at ~53 s. Deferring it to the first
frame would blow every latency budget on the first real call.
"""

from __future__ import annotations

from typing import List, Optional

# pyrefly: ignore [missing-import]
from voiceshield.config import settings
# pyrefly: ignore [missing-import]
from voiceshield.obs.logging import get_logger
from voiceshield.speaker.enrollment import EnrollmentStore

from .e1_spectral import E1SpectralExpert
from .e2_raw import E2RawWaveformExpert
from .e3_ssl import E3SSLExpert
from .e4_speaker import E4SpeakerExpert
from .e5_prosody import E5ProsodyExpert
from .e6_replay import E6ReplayExpert
from .registry import ExpertRegistry, expert_registry

logger = get_logger("voiceshield.models.bootstrap")


def build_experts(enrollment: Optional[EnrollmentStore] = None) -> List:
    """Instantiate all six experts in contract order."""
    if enrollment is None:
        from voiceshield.speaker.store import JsonEnrollmentStore

        enrollment = JsonEnrollmentStore()

    return [
        E1SpectralExpert(),
        E2RawWaveformExpert(),
        E3SSLExpert(),
        E4SpeakerExpert(enrollment=enrollment),
        E5ProsodyExpert(),
        E6ReplayExpert(),
    ]


def register_experts(
    registry: Optional[ExpertRegistry] = None,
    enrollment: Optional[EnrollmentStore] = None,
    warmup: Optional[bool] = None,
) -> ExpertRegistry:
    """Register all experts and report availability.

    Never raises on a missing model: an expert whose weights are absent is
    registered anyway and reports MODEL_UNAVAILABLE, so the pipeline runs and
    the gap is visible (C-27).
    """
    target = registry or expert_registry
    do_warmup = settings.expert_warmup_on_start if warmup is None else warmup

    for expert in build_experts(enrollment=enrollment):
        target.register(expert)

    if do_warmup:
        for expert in target.list_expert_ids():
            instance = target.get(expert)
            warm = getattr(instance, "warmup", None)
            if warm is None:
                continue
            try:
                warm()
            except Exception as exc:
                # A warmup failure must not prevent startup; the expert simply
                # stays unavailable and says so in the report below.
                logger.error(
                    f"warmup failed for {expert}",
                    extra={
                        "extra_fields": {
                            "expert_id": expert,
                            "error_type": type(exc).__name__,
                            "detail": str(exc)[:200],
                        }
                    },
                )

    target.log_availability_report()
    return target


def collect_model_versions(registry: Optional[ExpertRegistry] = None) -> List[str]:
    """Gather provenance signatures for EvidenceVector.model_versions[]."""
    target = registry or expert_registry
    versions: List[str] = []
    for eid in target.list_expert_ids():
        expert = target.get(eid)
        signature = getattr(expert, "version_signature", None)
        if signature:
            versions.append(str(signature))
    return sorted(set(versions))
