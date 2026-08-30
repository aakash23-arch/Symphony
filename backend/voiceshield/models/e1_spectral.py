"""E1 - spectro-temporal anti-spoofing expert (C-20).

STATUS: MODEL_UNAVAILABLE. This is the truthful state, not a placeholder bug.

The specification names an AASIST-style spectro-temporal architecture consuming
``FeatureBundle.spectral``. As of 2026-08-28, in this environment:

  * No AASIST checkpoint is available in a loadable form.
  * No AASIST architecture code is vendored (the graph-attention layers are not
    part of transformers, and there is no pip-installable implementation pinned
    against torch 2.1.2).

Per readiness R1 and SYMPHONY_REFERENCE §22, the correct behaviour is to report
MODEL_UNAVAILABLE and emit no probability at all. We deliberately do NOT:

  * substitute a different architecture into this slot and call it AASIST
    (the wav2vec2 deepfake classifier consumes raw waveform, so it belongs at
    E2 whose contract declares raw PCM input - see e2_raw.py);
  * synthesise a heuristic "spectral artefact score" that would look like model
    inference to the UI and to L4.

When AASIST weights are acquired, this expert gains an AntiSpoofingModel adapter
and the rest of the pipeline needs no change.
"""

from __future__ import annotations

from typing import List

from voiceshield.contracts import ExpertResult, ExpertStatus
from voiceshield.signal_processing import FeatureBundle

from . import errors as err
from ._expert_support import abstain
from .base import Expert

MODEL_ID_UNACQUIRED = "aasist:not-acquired"


class E1SpectralExpert(Expert):
    """Spectro-temporal expert. Abstains until AASIST weights are acquired."""

    def __init__(self, version: str = "0.0.0-unavailable"):
        super().__init__(expert_id="E1", version=version)

    @property
    def required_features(self) -> List[str]:
        return ["spectral"]

    @property
    def model_id(self) -> str:
        return MODEL_ID_UNACQUIRED

    @property
    def unavailable_reason(self) -> str:
        """Surfaced in the availability report so the UI can explain the gap."""
        return err.WEIGHTS_NOT_ACQUIRED

    def is_available(self) -> bool:
        """False: no AASIST weights and no architecture code exist here."""
        return False

    async def score(self, bundle: FeatureBundle) -> ExpertResult:
        """Always abstains with an explicit reason. Never returns a probability."""
        result = abstain(
            model_id=MODEL_ID_UNACQUIRED,
            error_code=err.WEIGHTS_NOT_ACQUIRED,
            error_message=(
                "AASIST-style spectro-temporal weights are not vendored and no "
                "architecture implementation is available in this environment"
            ),
            status=ExpertStatus.MODEL_UNAVAILABLE,
        )
        return result.to_expert_result(self.expert_id)
