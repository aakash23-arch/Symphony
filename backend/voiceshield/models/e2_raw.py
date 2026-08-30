"""E2 - raw-waveform anti-spoofing expert (C-21).

Consumes raw PCM only. Per C-21 this expert does NOT consume spectral features
and does NOT consume any other expert's output (§6.1 evidence independence).

A spoof probability is emitted ONLY when real model inference succeeds. Every
other path - no weights, audio too short, malformed input, inference error -
produces an explicit status with p=None.

SUBSTITUTION: backed by a wav2vec2 deepfake classifier, not RawNet2. See
adapters/hf_wav2vec2_spoof.py and docs/MODEL_INVENTORY.md.
"""

from __future__ import annotations

from typing import List, Optional

from voiceshield.config import settings
from voiceshield.contracts import ExpertResult, ExpertStatus
from voiceshield.signal_processing import FeatureBundle

from . import errors as err
from ._expert_support import abstain, extract_pcm, run_blocking, validate_bundle
from .base import Expert
from .interfaces import AntiSpoofingModel, ModelInferenceResult


class E2RawWaveformExpert(Expert):
    """Raw-waveform anti-spoofing expert."""

    def __init__(self, adapter: Optional[AntiSpoofingModel] = None, version: str = "1.0.0"):
        super().__init__(expert_id="E2", version=version)
        if adapter is None:
            from .adapters import Wav2Vec2SpoofAdapter

            adapter = Wav2Vec2SpoofAdapter()
        self._adapter = adapter
        self._last_signature: Optional[str] = None

    @property
    def required_features(self) -> List[str]:
        return ["raw_pcm"]

    @property
    def model_id(self) -> str:
        return self._adapter.describe().model_id

    @property
    def unavailable_reason(self) -> Optional[str]:
        return getattr(self._adapter, "load_error", None)

    @property
    def version_signature(self) -> Optional[str]:
        """Provenance string for EvidenceVector.model_versions[]."""
        return self._last_signature

    def is_available(self) -> bool:
        return bool(self._adapter.is_loaded())

    def warmup(self) -> bool:
        """Eagerly load weights. A cold load is ~53s; doing it on frame 1 would stall the call."""
        return bool(self._adapter.load())

    async def score(self, bundle: FeatureBundle) -> ExpertResult:
        """Score one frame of raw PCM."""
        reason = validate_bundle(bundle)
        if reason:
            return abstain(
                model_id=self.model_id,
                error_code=reason,
                error_message="unusable feature bundle",
                status=ExpertStatus.ERROR,
            ).to_expert_result(self.expert_id)

        pcm, reason = extract_pcm(bundle)
        if pcm is None:
            return abstain(
                model_id=self.model_id,
                error_code=reason or err.MALFORMED_INPUT,
                error_message="raw PCM unavailable or invalid",
                status=ExpertStatus.ABSTAIN,
            ).to_expert_result(self.expert_id)

        result: ModelInferenceResult = await run_blocking(
            self._adapter.infer, pcm, settings.audio_sample_rate
        )
        self._last_signature = result.version_signature(self.expert_id)
        return result.to_expert_result(self.expert_id)
