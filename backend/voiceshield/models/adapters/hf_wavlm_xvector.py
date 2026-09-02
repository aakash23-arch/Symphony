"""Speaker verification adapter over WavLMForXVector (C-23).

SUBSTITUTION NOTICE
    The specification (§6.2, C-23) names an ECAPA-TDNN speaker encoder via
    SpeechBrain. SpeechBrain is not installable in this environment: it requires
    torchaudio, which is absent, and its torch-2.1.2 compatibility was already
    flagged "REQUIRES VERIFICATION" in the tech-stack document.

    This adapter uses ``microsoft/wavlm-base-plus-sv`` (WavLMForXVector) instead.
    It is a genuine speaker-verification model - the task matches the slot
    exactly - but the architecture and the embedding dimension differ:
    512-d here versus 192-d for ECAPA. The dimension is recorded per enrolment
    so a stale 192-d reference cannot be silently compared against a 512-d one.

SCORE POLARITY
    Cosine similarity is natively "higher = matches the enrolled speaker" =
    LESS suspicious, which is the opposite of every other expert's `p`. This
    adapter therefore emits p = 1 - normalised_similarity so that `p` means
    P(inauthentic) uniformly, and preserves the raw cosine in extra["cosine"].
    See interfaces.P_MEANS_PROBABILITY_INAUTHENTIC.

SPEAKER-CONSISTENCY EVIDENCE
    Provides speaker-consistency evidence. No generic accuracy or detection rate is asserted.
"""

from __future__ import annotations

import time
from typing import Any, List, Optional

import numpy as np

from voiceshield.contracts import ExpertStatus
from voiceshield.obs.logging import get_logger

from .. import errors as err
from ..interfaces import MIN_SAMPLES_XVECTOR, ModelDescriptor, ModelInferenceResult
from ..loader import ManifestModelLoader, enforce_offline, model_loader
from ..runtime import configure_torch_runtime, resolve_device

logger = get_logger("voiceshield.models.adapters.wavlm_xvector")

#: WavLMForXVector output dimensionality (config.xvector_output_dim). Verified.
XVECTOR_DIM = 512


class WavLMXVectorAdapter:
    """SpeakerVerificationModel implementation over transformers WavLMForXVector."""

    def __init__(
        self,
        model_key: Optional[str] = None,
        loader: Optional[ManifestModelLoader] = None,
        device: Optional[str] = None,
    ):
        from voiceshield.config import settings

        self._key = model_key or settings.e4_model_key
        self._loader = loader or model_loader
        self._device = resolve_device(device)
        self._model: Any = None
        self._extractor: Any = None
        self._load_state = "UNATTEMPTED"
        self._load_error: Optional[str] = None

    # --- Identity --------------------------------------------------------------

    def describe(self) -> ModelDescriptor:
        descriptor = self._loader.describe(self._key, MIN_SAMPLES_XVECTOR)
        if descriptor is not None:
            return descriptor
        return ModelDescriptor(
            model_id=f"{self._key}:not-acquired",
            model_version="none",
            family="wavlm-xvector",
            min_input_samples=MIN_SAMPLES_XVECTOR,
            is_substitution=True,
            substitution_note="Specification names ECAPA-TDNN; weights not acquired.",
        )

    @property
    def embedding_dim(self) -> int:
        """512 for WavLMForXVector (ECAPA would be 192)."""
        if self._model is not None:
            return int(getattr(self._model.config, "xvector_output_dim", XVECTOR_DIM))
        return XVECTOR_DIM

    @property
    def load_error(self) -> Optional[str]:
        return self._load_error

    # --- Lifecycle -------------------------------------------------------------

    def is_loaded(self) -> bool:
        return self._load_state == "OK" and self._model is not None

    def unload(self) -> None:
        self._model = None
        self._extractor = None
        self._load_state = "UNATTEMPTED"

    def load(self) -> bool:
        """Load from vendored weights. Offline only; never downloads (C-27)."""
        if self._load_state == "OK":
            return True
        if self._load_state == "FAILED":
            return False

        self._load_state = "FAILED"

        ok, reason = self._loader.verify_model(self._key)
        if not ok:
            self._load_error = reason
            logger.warning(
                "E4 speaker verification model unavailable",
                extra={"extra_fields": {"code": reason, "key": self._key}},
            )
            return False

        path = self._loader.resolve_path(self._key)
        if path is None:
            self._load_error = err.ARTEFACT_MISSING
            return False

        enforce_offline()
        if not configure_torch_runtime():
            self._load_error = err.BACKEND_IMPORT_FAILED
            return False

        try:
            from transformers import AutoFeatureExtractor, WavLMForXVector
        except ImportError as exc:
            self._load_error = err.BACKEND_IMPORT_FAILED
            logger.error(
                "transformers unavailable; E4 cannot run",
                extra={"extra_fields": {"code": err.BACKEND_IMPORT_FAILED, "detail": str(exc)[:200]}},
            )
            return False

        try:
            # NOTE: loading prints a warning about pos_conv_embed weight_g/weight_v
            # not being used. It is COSMETIC - the weights load correctly; see
            # models/runtime.py for the tensor-level verification. It is
            # suppressed by configure_torch_runtime().
            self._extractor = AutoFeatureExtractor.from_pretrained(str(path), local_files_only=True)
            model = WavLMForXVector.from_pretrained(str(path), local_files_only=True)
            model.eval()
            model.to(self._device)
            self._model = model
        except Exception as exc:
            self._load_error = err.MODEL_LOAD_FAILED
            logger.error(
                "E4 model failed to load",
                extra={
                    "extra_fields": {
                        "code": err.MODEL_LOAD_FAILED,
                        "key": self._key,
                        "error_type": type(exc).__name__,
                        "detail": str(exc)[:200],
                    }
                },
            )
            return False

        self._load_state = "OK"
        self._load_error = None
        descriptor = self.describe()
        logger.info(
            "E4 speaker verification model loaded",
            extra={
                "extra_fields": {
                    "model_id": descriptor.model_id,
                    "model_version": descriptor.model_version,
                    "device": self._device,
                    "embedding_dim": self.embedding_dim,
                    "is_substitution": descriptor.is_substitution,
                }
            },
        )
        return True

    # --- Embeddings ------------------------------------------------------------

    def embed(self, pcm: np.ndarray, sample_rate: int) -> np.ndarray:
        """Generate a speaker embedding. Raises if the model is not loaded.

        Callers should prefer ``verify()``, which converts every failure into an
        abstaining result instead of raising.
        """
        if not self.is_loaded() and not self.load():
            raise RuntimeError(f"E4 model not loaded: {self._load_error}")

        arr = np.asarray(pcm, dtype=np.float32)
        if arr.size < MIN_SAMPLES_XVECTOR:
            raise ValueError(
                f"WavLMForXVector needs >= {MIN_SAMPLES_XVECTOR} samples, got {arr.size}"
            )

        import torch

        inputs = self._extractor(arr, sampling_rate=sample_rate, return_tensors="pt")
        inputs = {k: v.to(self._device) for k, v in inputs.items()}
        with torch.inference_mode():
            embeddings = self._model(**inputs).embeddings
        return embeddings[0].cpu().numpy().astype(np.float32)

    def similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Cosine similarity in [-1, 1]."""
        va = np.asarray(a, dtype=np.float64).ravel()
        vb = np.asarray(b, dtype=np.float64).ravel()
        if va.shape != vb.shape:
            raise ValueError(f"embedding dimension mismatch: {va.shape} vs {vb.shape}")
        na = float(np.linalg.norm(va))
        nb = float(np.linalg.norm(vb))
        if na == 0.0 or nb == 0.0:
            return 0.0
        return float(np.clip(np.dot(va, vb) / (na * nb), -1.0, 1.0))

    def verify(
        self, pcm: np.ndarray, sample_rate: int, reference: np.ndarray
    ) -> ModelInferenceResult:
        """Embed and compare against the enrolled reference embedding."""
        descriptor = self.describe()
        n = int(np.asarray(pcm).size)

        if not self.is_loaded() and not self.load():
            return ModelInferenceResult.unavailable(
                model_id=descriptor.model_id,
                model_version=descriptor.model_version,
                error_code=self._load_error or err.WEIGHTS_NOT_ACQUIRED,
                error_message="E4 speaker verification model is not loaded",
                input_samples=n,
                input_sample_rate=sample_rate,
            )

        if n < MIN_SAMPLES_XVECTOR:
            return ModelInferenceResult.unavailable(
                model_id=descriptor.model_id,
                model_version=descriptor.model_version,
                error_code=err.INSUFFICIENT_AUDIO,
                error_message=f"need >= {MIN_SAMPLES_XVECTOR} samples, got {n}",
                status=ExpertStatus.ABSTAIN,
                input_samples=n,
                input_sample_rate=sample_rate,
            )

        ref = np.asarray(reference, dtype=np.float32).ravel()
        if ref.size != self.embedding_dim:
            # A 192-d ECAPA reference against a 512-d WavLM embedding is not a
            # low score, it is an incomparable one. Abstain rather than raise
            # inside inference.
            return ModelInferenceResult.unavailable(
                model_id=descriptor.model_id,
                model_version=descriptor.model_version,
                error_code=err.ENROLLMENT_DIM_MISMATCH,
                error_message=f"reference is {ref.size}-d, model emits {self.embedding_dim}-d",
                status=ExpertStatus.ABSTAIN,
                input_samples=n,
                input_sample_rate=sample_rate,
            )

        started = time.perf_counter()
        try:
            current = self.embed(pcm, sample_rate)
            cosine = self.similarity(current, ref)
        except Exception as exc:
            return ModelInferenceResult.unavailable(
                model_id=descriptor.model_id,
                model_version=descriptor.model_version,
                error_code=err.INFERENCE_ERROR,
                error_message=f"{type(exc).__name__}: {str(exc)[:160]}",
                status=ExpertStatus.ERROR,
                latency_ms=(time.perf_counter() - started) * 1000.0,
                input_samples=n,
                input_sample_rate=sample_rate,
            )

        latency_ms = (time.perf_counter() - started) * 1000.0

        # Map cosine [-1,1] -> similarity [0,1], then invert so p = P(inauthentic).
        normalised = (cosine + 1.0) / 2.0
        p_inauthentic = float(np.clip(1.0 - normalised, 0.0, 1.0))

        from voiceshield.config import settings

        return ModelInferenceResult(
            model_id=descriptor.model_id,
            model_version=descriptor.model_version,
            model_family=descriptor.family,
            status=ExpertStatus.OK,
            p=p_inauthentic,
            # Distance from the configured operating point, as a rough strength
            # signal. Deliberately NOT a decision: L3 does not threshold (C-23).
            confidence=float(min(1.0, abs(cosine - settings.e4_similarity_threshold) * 2.0)),
            logits=[float(cosine)],
            latency_ms=latency_ms,
            input_samples=n,
            input_sample_rate=sample_rate,
            extra={
                "cosine": float(cosine),
                "normalised_similarity": float(normalised),
                "threshold": float(settings.e4_similarity_threshold),
                "embedding_dim": float(self.embedding_dim),
            },
        )
