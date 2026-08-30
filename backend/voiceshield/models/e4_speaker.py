"""E4 - speaker verification expert (C-23).

Answers a different question from the anti-spoofing experts: not "is this
synthetic?" but "is this the claimed person?". It is deliberately NOT another
spoof classifier (§6.2).

ABSTENTION LADDER, in order. Each rung has a distinct reason code so the UI can
say WHY there is no score:

    no adapter / weights      -> MODEL_UNAVAILABLE
    no raw PCM in the bundle  -> ABSTAIN / MISSING_RAW_PCM
    buffer still filling      -> ABSTAIN / INSUFFICIENT_AUDIO
    stride not yet elapsed    -> ABSTAIN / E4_STRIDE_SKIP
    no enrolled reference     -> ABSTAIN / ENROLLMENT_MISSING
    reference dim mismatch    -> ABSTAIN / ENROLLMENT_DIM_MISMATCH

C-23 and §22 are explicit that an unenrolled speaker yields an ABSTENTION - not
a low score, not a high score. A missing reference is an absence of evidence,
and encoding it as either "matches" or "does not match" would be a fabrication.

BUFFERING: a frame carries 250 ms (4000 samples), below WavLMForXVector's
measured 4880-sample floor, so audio is accumulated across frames. See
buffering.py.

SCORE POLARITY: emits p = P(inauthentic) = 1 - normalised_cosine, so `p` means
the same thing here as for every other expert. Raw cosine is preserved in
logits[0].
"""

from __future__ import annotations

from typing import List, Optional

from voiceshield.config import settings
from voiceshield.contracts import ExpertResult, ExpertStatus
from voiceshield.obs.logging import get_logger
from voiceshield.signal_processing import FeatureBundle
from voiceshield.speaker.enrollment import EnrollmentStore

from . import errors as err
from ._expert_support import abstain, extract_pcm, run_blocking, validate_bundle
from .base import Expert
from .buffering import RollingPCMBuffer
from .interfaces import ModelInferenceResult, SpeakerVerificationModel

logger = get_logger("voiceshield.models.e4")


class E4SpeakerExpert(Expert):
    """Speaker verification expert with a rolling buffer and explicit abstention."""

    def __init__(
        self,
        adapter: Optional[SpeakerVerificationModel] = None,
        enrollment: Optional[EnrollmentStore] = None,
        buffer: Optional[RollingPCMBuffer] = None,
        speaker_id_resolver=None,
        version: str = "1.0.0",
    ):
        super().__init__(expert_id="E4", version=version)
        if adapter is None:
            from .adapters import WavLMXVectorAdapter

            adapter = WavLMXVectorAdapter()
        self._adapter = adapter
        self._enrollment = enrollment
        self._buffer = buffer or RollingPCMBuffer()
        # Maps a session to the enrolled speaker whose reference we compare
        # against. Defaults to using the session id itself.
        self._resolve_speaker = speaker_id_resolver or (lambda session_id: session_id)
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
        return self._last_signature

    @property
    def buffer(self) -> RollingPCMBuffer:
        return self._buffer

    def is_available(self) -> bool:
        return bool(self._adapter.is_loaded())

    def warmup(self) -> bool:
        """Eagerly load weights to avoid a ~53s cold load on the first frame."""
        return bool(self._adapter.load())

    def release_session(self, session_id: str) -> None:
        """Drop a finished session's buffer. Call at session end or memory leaks."""
        self._buffer.release(session_id)

    def _abstain(self, code: str, message: str, status: ExpertStatus = ExpertStatus.ABSTAIN) -> ExpertResult:
        return abstain(
            model_id=self.model_id, error_code=code, error_message=message, status=status
        ).to_expert_result(self.expert_id)

    async def score(self, bundle: FeatureBundle) -> ExpertResult:
        """Verify the current speaker against the enrolled reference."""
        reason = validate_bundle(bundle)
        if reason:
            return self._abstain(reason, "unusable feature bundle", ExpertStatus.ERROR)

        pcm, reason = extract_pcm(bundle)
        if pcm is None:
            return self._abstain(reason or err.MALFORMED_INPUT, "raw PCM unavailable or invalid")

        session_id = bundle.session_id
        self._buffer.append(session_id, pcm)

        if not self._buffer.is_ready(session_id):
            return self._abstain(
                err.INSUFFICIENT_AUDIO,
                f"buffering: need >= {self._buffer.min_samples} samples for a stable embedding",
            )

        if not self._buffer.should_emit(session_id):
            return self._abstain(
                err.E4_STRIDE_SKIP,
                f"holding: re-scores every {self._buffer.stride_ms} ms",
            )

        # Enrollment is checked before inference: with no reference there is
        # nothing to compare against, and running the encoder would burn CPU to
        # produce an embedding we must then discard.
        if self._enrollment is None:
            return self._abstain(err.ENROLLMENT_MISSING, "no enrollment store configured")

        speaker_id = self._resolve_speaker(session_id)
        try:
            reference = self._enrollment.get_embedding(speaker_id)
        except NotImplementedError:
            return self._abstain(err.ENROLLMENT_MISSING, "enrollment store not implemented")

        if reference is None:
            return self._abstain(
                err.ENROLLMENT_MISSING,
                f"speaker {speaker_id!r} has no enrolled reference; abstaining rather "
                "than scoring an identity we cannot check (C-23)",
            )

        window = self._buffer.get(session_id)
        if window is None:
            return self._abstain(err.INSUFFICIENT_AUDIO, "session buffer disappeared")

        result: ModelInferenceResult = await run_blocking(
            self._adapter.verify, window, settings.audio_sample_rate, reference
        )

        if result.status == ExpertStatus.OK:
            self._buffer.mark_emitted(session_id)

        self._last_signature = result.version_signature(self.expert_id)
        return result.to_expert_result(self.expert_id)
