"""Anti-spoofing adapter over a HuggingFace wav2vec2 sequence classifier (C-21).

SUBSTITUTION NOTICE
    The specification names a RawNet2-class raw-waveform anti-spoof model. No
    RawNet2 checkpoint is loadable in this environment. This adapter wraps a
    wav2vec2 sequence classifier fine-tuned for deepfake audio detection.

    IT IS NOT RawNet2 AND IT IS NOT AASIST.

    It occupies the E2 slot because it consumes raw waveform, which is what C-21
    declares as E2's input. E1 (AASIST, spectral input) stays unavailable rather
    than being filled with this model.

    ``ModelDescriptor.is_substitution`` carries this fact in machine-readable
    form so it reaches the availability report and cannot be lost.

NO ACCURACY CLAIM
    No accuracy, EER or detection rate is asserted for this model. No evaluation
    set exists in this workspace. The probability it emits is the model's raw
    output, uncalibrated; L4 treats it as a prior-weighted expert, not as truth.
"""

from __future__ import annotations

import time
from typing import Any, List, Optional

import numpy as np

from voiceshield.contracts import ExpertStatus
from voiceshield.obs.logging import get_logger

from .. import errors as err
from ..interfaces import MIN_SAMPLES_SPOOF, ModelDescriptor, ModelInferenceResult
from ..loader import ManifestModelLoader, enforce_offline, model_loader
from ..runtime import configure_torch_runtime, resolve_device

logger = get_logger("voiceshield.models.adapters.wav2vec2_spoof")

#: Label strings that denote the SYNTHETIC class. Resolved from the checkpoint's
#: own id2label at load time - never hardcoded to an index. Checkpoints disagree:
#: mo-thecreator uses {0:'fake',1:'real'} while Hemgg uses
#: {0:'AIVoice',1:'HumanVoice'}, so an index-0 assumption silently inverts one.
FAKE_LABEL_TOKENS = {"fake", "spoof", "spoofed", "synthetic", "aivoice", "ai", "deepfake", "generated"}
REAL_LABEL_TOKENS = {"real", "bonafide", "genuine", "human", "humanvoice", "authentic"}


def _normalise(label: str) -> str:
    return "".join(ch for ch in label.lower() if ch.isalnum())


class Wav2Vec2SpoofAdapter:
    """AntiSpoofingModel implementation over transformers wav2vec2."""

    def __init__(
        self,
        model_key: Optional[str] = None,
        loader: Optional[ManifestModelLoader] = None,
        device: Optional[str] = None,
    ):
        from voiceshield.config import settings

        self._key = model_key or settings.e2_model_key
        self._loader = loader or model_loader
        self._device = resolve_device(device)
        self._model: Any = None
        self._extractor: Any = None
        self._fake_index: Optional[int] = None
        # Tri-state so a failed load is not retried on every single frame.
        self._load_state = "UNATTEMPTED"
        self._load_error: Optional[str] = None

    # --- Identity --------------------------------------------------------------

    def describe(self) -> ModelDescriptor:
        descriptor = self._loader.describe(self._key, MIN_SAMPLES_SPOOF)
        if descriptor is not None:
            return descriptor
        return ModelDescriptor(
            model_id=f"{self._key}:not-acquired",
            model_version="none",
            family="wav2vec2-seq-cls",
            min_input_samples=MIN_SAMPLES_SPOOF,
            is_substitution=True,
            substitution_note="Specification names RawNet2; this slot is unfilled.",
        )

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
                "E2 anti-spoofing model unavailable",
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
            from transformers import AutoFeatureExtractor, AutoModelForAudioClassification
        except ImportError as exc:
            self._load_error = err.BACKEND_IMPORT_FAILED
            logger.error(
                "transformers unavailable; E2 cannot run",
                extra={"extra_fields": {"code": err.BACKEND_IMPORT_FAILED, "detail": str(exc)[:200]}},
            )
            return False

        try:
            self._extractor = AutoFeatureExtractor.from_pretrained(str(path), local_files_only=True)
            model = AutoModelForAudioClassification.from_pretrained(str(path), local_files_only=True)
            model.eval()
            model.to(self._device)
            self._model = model
        except Exception as exc:
            self._load_error = err.MODEL_LOAD_FAILED
            logger.error(
                "E2 model failed to load",
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

        self._fake_index = self._resolve_fake_index()
        if self._fake_index is None:
            # Refusing to guess: if we cannot tell which logit means "synthetic",
            # any probability we emit could be exactly inverted. Abstaining is
            # the only honest option.
            self._load_error = err.LABEL_MAP_UNRECOGNIZED
            logger.error(
                "cannot identify the synthetic class from id2label; E2 will abstain",
                extra={
                    "extra_fields": {
                        "code": err.LABEL_MAP_UNRECOGNIZED,
                        "id2label": str(getattr(self._model.config, "id2label", {}))[:200],
                    }
                },
            )
            self._model = None
            return False

        self._load_state = "OK"
        self._load_error = None
        descriptor = self.describe()
        logger.info(
            "E2 anti-spoofing model loaded",
            extra={
                "extra_fields": {
                    "model_id": descriptor.model_id,
                    "model_version": descriptor.model_version,
                    "device": self._device,
                    "fake_class_index": self._fake_index,
                    "is_substitution": descriptor.is_substitution,
                }
            },
        )
        return True

    def _resolve_fake_index(self) -> Optional[int]:
        """Find which output index means "synthetic", from the checkpoint labels."""
        id2label = getattr(self._model.config, "id2label", None) or {}
        if len(id2label) != 2:
            return None

        fake_idx = None
        real_idx = None
        for idx, label in id2label.items():
            token = _normalise(str(label))
            if token in FAKE_LABEL_TOKENS:
                fake_idx = int(idx)
            elif token in REAL_LABEL_TOKENS:
                real_idx = int(idx)

        if fake_idx is not None and real_idx is not None and fake_idx != real_idx:
            return fake_idx
        return None

    # --- Inference -------------------------------------------------------------

    def infer(self, pcm: np.ndarray, sample_rate: int) -> ModelInferenceResult:
        """Run spoof detection. Emits a probability ONLY when inference succeeds."""
        descriptor = self.describe()
        n = int(np.asarray(pcm).size)

        if not self.is_loaded() and not self.load():
            return ModelInferenceResult.unavailable(
                model_id=descriptor.model_id,
                model_version=descriptor.model_version,
                error_code=self._load_error or err.WEIGHTS_NOT_ACQUIRED,
                error_message="E2 anti-spoofing model is not loaded",
                input_samples=n,
                input_sample_rate=sample_rate,
            )

        if sample_rate != descriptor.sample_rate:
            return ModelInferenceResult.unavailable(
                model_id=descriptor.model_id,
                model_version=descriptor.model_version,
                error_code=err.MALFORMED_INPUT,
                error_message=f"expected {descriptor.sample_rate} Hz, got {sample_rate}",
                status=ExpertStatus.ABSTAIN,
                input_samples=n,
                input_sample_rate=sample_rate,
            )

        if n < MIN_SAMPLES_SPOOF:
            # Measured floor: below this the conv stack raises. Abstain BEFORE
            # calling the model rather than letting a RuntimeError escape.
            return ModelInferenceResult.unavailable(
                model_id=descriptor.model_id,
                model_version=descriptor.model_version,
                error_code=err.INSUFFICIENT_AUDIO,
                error_message=f"need >= {MIN_SAMPLES_SPOOF} samples, got {n}",
                status=ExpertStatus.ABSTAIN,
                input_samples=n,
                input_sample_rate=sample_rate,
            )

        import torch

        started = time.perf_counter()
        try:
            inputs = self._extractor(
                np.asarray(pcm, dtype=np.float32), sampling_rate=sample_rate, return_tensors="pt"
            )
            inputs = {k: v.to(self._device) for k, v in inputs.items()}
            with torch.inference_mode():
                logits = self._model(**inputs).logits
            probs = torch.softmax(logits, dim=-1)[0]
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
        p_fake = float(probs[self._fake_index].item())

        # Confidence = margin between the two classes. A 50/50 output is a real
        # inference but a weak one, and L4 needs to see that difference.
        confidence = float(abs(probs[0].item() - probs[1].item()))

        return ModelInferenceResult(
            model_id=descriptor.model_id,
            model_version=descriptor.model_version,
            model_family=descriptor.family,
            status=ExpertStatus.OK,
            p=p_fake,
            confidence=confidence,
            logits=[float(x) for x in logits[0].tolist()],
            latency_ms=latency_ms,
            input_samples=n,
            input_sample_rate=sample_rate,
            extra={"p_fake": p_fake, "p_real": float(probs[1 - self._fake_index].item())},
        )
