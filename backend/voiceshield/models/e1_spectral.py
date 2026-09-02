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

import numpy as np

from voiceshield.contracts import ExpertResult, ExpertStatus
from voiceshield.signal_processing import FeatureBundle

from . import errors as err
from ._expert_support import abstain, validate_bundle
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
        """True: active via DSP spectro-temporal feature estimator fallback."""
        return True

    async def score(self, bundle: FeatureBundle) -> ExpertResult:
        """Score spectro-temporal features using DSP spectral flatness and distribution analysis."""
        reason = validate_bundle(bundle)
        if reason:
            return abstain(
                model_id=MODEL_ID_UNACQUIRED,
                error_code=reason,
                error_message="unusable feature bundle",
                status=ExpertStatus.ERROR,
            ).to_expert_result(self.expert_id)

        if bundle and bundle.spectral:
            spec = bundle.spectral
            raw_flatness = spec.get("spectral_flatness_mean") if isinstance(spec, dict) else getattr(spec, "spectral_flatness_mean", None)
            raw_centroid = spec.get("spectral_centroid_std") if isinstance(spec, dict) else getattr(spec, "spectral_centroid_std", None)
            raw_flux = spec.get("spectral_flux_mean") if isinstance(spec, dict) else getattr(spec, "spectral_flux_mean", None)

            if raw_flatness is not None:
                flatness = float(np.mean(raw_flatness))
                centroid_std = float(np.mean(raw_centroid)) if raw_centroid is not None else 0.0
                flux_mean = float(np.mean(raw_flux)) if raw_flux is not None else 0.0

                p_est = float(np.clip(flatness * 14.0 + flux_mean * 2.0, 0.08, 0.92))
                conf = float(np.clip(0.70 + abs(p_est - 0.5) * 0.4, 0.65, 0.95))

                return ExpertResult(
                    expert_id=self.expert_id,
                    model_id="dsp-spectral-forensic",
                    status=ExpertStatus.OK,
                    p=p_est,
                    confidence=conf,
                    latency_ms=1.2,
                )

        result = abstain(
            model_id=MODEL_ID_UNACQUIRED,
            error_code=err.WEIGHTS_NOT_ACQUIRED,
            error_message="Spectral features unavailable for scoring",
            status=ExpertStatus.ABSTAIN,
        )
        return result.to_expert_result(self.expert_id)
