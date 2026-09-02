"""Modular detector framework and concrete anti-spoofing detector implementations."""

import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import numpy as np

from .contracts import (
    AudioSegment,
    AcousticFeaturesSummary,
    DetectorResult,
    SegmentInferenceScore,
)


class BaseDetector(ABC):
    """Abstract base class for all anti-spoofing detectors."""

    @property
    @abstractmethod
    def detector_id(self) -> str:
        pass

    @property
    @abstractmethod
    def model_version(self) -> str:
        pass

    @property
    @abstractmethod
    def detector_type(self) -> str:
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if model weights and dependencies are ready."""
        pass

    @abstractmethod
    def detect(
        self,
        full_pcm: np.ndarray,
        segments: List[AudioSegment],
        features: AcousticFeaturesSummary,
        sample_rate: int = 16000,
        claimed_identity: Optional[str] = None,
    ) -> DetectorResult:
        """Run inference on the provided audio signal and segments."""
        pass


class Wav2Vec2DeepfakeDetector(BaseDetector):
    """Primary neural anti-spoofing detector wrapping fine-tuned Wav2Vec2 sequence classifier.
    
    Loaded ONCE into memory at server startup (singleton pattern).
    """

    _instance: Optional["Wav2Vec2DeepfakeDetector"] = None

    def __init__(self, model_key: Optional[str] = None, device: Optional[str] = None):
        from voiceshield.config import settings
        from voiceshield.models.adapters.hf_wav2vec2_spoof import Wav2Vec2SpoofAdapter

        self._model_key = model_key or settings.e2_model_key
        self._adapter = Wav2Vec2SpoofAdapter(model_key=self._model_key, device=device)
        self._is_loaded = False

    @classmethod
    def get_instance(cls) -> "Wav2Vec2DeepfakeDetector":
        """Singleton accessor ensuring weights are loaded only once."""
        if cls._instance is None:
            cls._instance = cls()
            cls._instance.ensure_loaded()
        return cls._instance

    @property
    def detector_id(self) -> str:
        return "wav2vec2-deepfake"

    @property
    def model_version(self) -> str:
        desc = self._adapter.describe()
        return desc.model_version if desc else "1.0.0"

    @property
    def detector_type(self) -> str:
        return "NEURAL_WAV2VEC2"

    def is_available(self) -> bool:
        return self._adapter.is_loaded()

    def ensure_loaded(self) -> bool:
        """Load model weights if not already in memory."""
        if not self._is_loaded:
            self._is_loaded = self._adapter.load()
        return self._is_loaded

    def detect(
        self,
        full_pcm: np.ndarray,
        segments: List[AudioSegment],
        features: AcousticFeaturesSummary,
        sample_rate: int = 16000,
        claimed_identity: Optional[str] = None,
    ) -> DetectorResult:
        """Execute neural inference on audio segments."""
        t0 = time.perf_counter()

        if not self.ensure_loaded():
            latency = (time.perf_counter() - t0) * 1000.0
            return DetectorResult(
                detector_id=self.detector_id,
                model_version=self.model_version,
                detector_type=self.detector_type,
                p_fake=0.5,
                p_real=0.5,
                raw_confidence=0.0,
                segment_scores=[],
                latency_ms=latency,
                status="ERROR",
                error_message=f"Wav2Vec2 model failed to load: {self._adapter.load_error}",
            )

        segment_scores: List[SegmentInferenceScore] = []
        p_fake_list: List[float] = []

        # If no segments, evaluate full PCM
        if not segments and len(full_pcm) > 0:
            segments = [
                AudioSegment(
                    segment_index=0,
                    start_time_s=0.0,
                    end_time_s=len(full_pcm) / float(sample_rate),
                    duration_s=len(full_pcm) / float(sample_rate),
                    samples_count=len(full_pcm),
                )
            ]

        for seg in segments:
            start_sample = int(seg.start_time_s * sample_rate)
            end_sample = int(seg.end_time_s * sample_rate)
            chunk = full_pcm[start_sample:end_sample]

            if len(chunk) < int(0.3 * sample_rate):
                continue

            try:
                res = self._adapter.infer(chunk, sample_rate=sample_rate)
                if res.status.value == "OK" and res.p is not None:
                    p_fake = float(res.p)
                    p_real = float(1.0 - p_fake)
                    conf = float(res.confidence) if res.confidence is not None else float(np.clip(abs(p_fake - 0.5) * 2.0, 0.50, 0.99))

                    p_fake_list.append(p_fake)
                    segment_scores.append(
                        SegmentInferenceScore(
                            segment_index=seg.segment_index,
                            start_time_s=seg.start_time_s,
                            end_time_s=seg.end_time_s,
                            p_fake=p_fake,
                            p_real=p_real,
                            confidence=conf,
                            is_spoof_suspected=p_fake >= 0.5,
                        )
                    )
            except Exception:
                continue

        latency = (time.perf_counter() - t0) * 1000.0

        if not p_fake_list:
            try:
                res = self._adapter.infer(full_pcm, sample_rate=sample_rate)
                if res.status.value == "OK" and res.p is not None:
                    p_fake = float(res.p)
                    p_real = float(1.0 - p_fake)
                    conf = float(res.confidence) if res.confidence is not None else float(np.clip(abs(p_fake - 0.5) * 2.0, 0.50, 0.99))
                    return DetectorResult(
                        detector_id=self.detector_id,
                        model_version=self.model_version,
                        detector_type=self.detector_type,
                        p_fake=p_fake,
                        p_real=p_real,
                        raw_confidence=conf,
                        segment_scores=[],
                        latency_ms=latency,
                        status="OK",
                    )
                else:
                    return DetectorResult(
                        detector_id=self.detector_id,
                        model_version=self.model_version,
                        detector_type=self.detector_type,
                        p_fake=0.5,
                        p_real=0.5,
                        raw_confidence=0.0,
                        segment_scores=[],
                        latency_ms=latency,
                        status="ERROR",
                        error_message=res.error_message or "Inference failed",
                    )
            except Exception as exc:
                return DetectorResult(
                    detector_id=self.detector_id,
                    model_version=self.model_version,
                    detector_type=self.detector_type,
                    p_fake=0.5,
                    p_real=0.5,
                    raw_confidence=0.0,
                    segment_scores=[],
                    latency_ms=latency,
                    status="ERROR",
                    error_message=str(exc),
                )

        mean_p_fake = float(np.mean(p_fake_list))
        mean_p_real = float(1.0 - mean_p_fake)
        mean_conf = float(np.mean([s.confidence for s in segment_scores]))

        return DetectorResult(
            detector_id=self.detector_id,
            model_version=self.model_version,
            detector_type=self.detector_type,
            p_fake=mean_p_fake,
            p_real=mean_p_real,
            raw_confidence=mean_conf,
            segment_scores=segment_scores,
            latency_ms=latency,
            status="OK",
        )


class WavLMSpeakerVerificationDetector(BaseDetector):
    """Speaker verification detector computing 512-d x-vectors and cosine distance."""

    _instance: Optional["WavLMSpeakerVerificationDetector"] = None

    def __init__(self, model_key: Optional[str] = None, device: Optional[str] = None):
        from voiceshield.config import settings
        from voiceshield.models.adapters.hf_wavlm_xvector import WavLMXVectorAdapter

        self._model_key = model_key or settings.e4_model_key
        self._adapter = WavLMXVectorAdapter(model_key=self._model_key, device=device)
        self._is_loaded = False

    @classmethod
    def get_instance(cls) -> "WavLMSpeakerVerificationDetector":
        if cls._instance is None:
            cls._instance = cls()
            cls._instance.ensure_loaded()
        return cls._instance

    @property
    def detector_id(self) -> str:
        return "wavlm-xvector-sv"

    @property
    def model_version(self) -> str:
        desc = self._adapter.describe()
        return desc.model_version if desc else "1.0.0"

    @property
    def detector_type(self) -> str:
        return "SPEAKER_BIOMETRIC_XVECTOR"

    def is_available(self) -> bool:
        return self._adapter.is_loaded()

    def ensure_loaded(self) -> bool:
        if not self._is_loaded:
            self._is_loaded = self._adapter.load()
        return self._is_loaded

    def detect(
        self,
        full_pcm: np.ndarray,
        segments: List[AudioSegment],
        features: AcousticFeaturesSummary,
        sample_rate: int = 16000,
        claimed_identity: Optional[str] = None,
    ) -> DetectorResult:
        """Run speaker biometric verification against enrolled speaker embedding."""
        t0 = time.perf_counter()

        if not self.ensure_loaded():
            return DetectorResult(
                detector_id=self.detector_id,
                model_version=self.model_version,
                detector_type=self.detector_type,
                p_fake=0.5,
                p_real=0.5,
                raw_confidence=0.0,
                segment_scores=[],
                latency_ms=(time.perf_counter() - t0) * 1000.0,
                status="DEFERRED",
                error_message="WavLM speaker model unavailable",
            )

        if not claimed_identity:
            return DetectorResult(
                detector_id=self.detector_id,
                model_version=self.model_version,
                detector_type=self.detector_type,
                p_fake=0.5,
                p_real=0.5,
                raw_confidence=0.0,
                segment_scores=[],
                latency_ms=(time.perf_counter() - t0) * 1000.0,
                status="DEFERRED",
                error_message="No claimed identity supplied for speaker verification.",
            )

        from voiceshield.api.runtime import get_runtime
        runtime = get_runtime()
        enrollment_store = getattr(runtime, "enrollment_store", None)
        enrolled_emb = enrollment_store.get_embedding(claimed_identity) if enrollment_store else None

        if enrolled_emb is None:
            return DetectorResult(
                detector_id=self.detector_id,
                model_version=self.model_version,
                detector_type=self.detector_type,
                p_fake=0.5,
                p_real=0.5,
                raw_confidence=0.0,
                segment_scores=[],
                latency_ms=(time.perf_counter() - t0) * 1000.0,
                status="DEFERRED",
                error_message=f"Speaker identity '{claimed_identity}' is not enrolled.",
            )

        try:
            res = self._adapter.verify(full_pcm, sample_rate=sample_rate, reference=enrolled_emb)
            latency = (time.perf_counter() - t0) * 1000.0
            if res.status.value == "OK" and res.p is not None:
                p_impersonation = float(res.p)
                p_real = float(1.0 - p_impersonation)
                conf = float(res.confidence) if res.confidence is not None else float(np.clip(abs(p_impersonation - 0.5) * 2.0, 0.50, 0.99))

                return DetectorResult(
                    detector_id=self.detector_id,
                    model_version=self.model_version,
                    detector_type=self.detector_type,
                    p_fake=p_impersonation,
                    p_real=p_real,
                    raw_confidence=conf,
                    segment_scores=[],
                    latency_ms=latency,
                    status="OK",
                )
            else:
                return DetectorResult(
                    detector_id=self.detector_id,
                    model_version=self.model_version,
                    detector_type=self.detector_type,
                    p_fake=0.5,
                    p_real=0.5,
                    raw_confidence=0.0,
                    segment_scores=[],
                    latency_ms=latency,
                    status="ERROR",
                    error_message=res.error_message or "Speaker verification failed",
                )
        except Exception as exc:
            return DetectorResult(
                detector_id=self.detector_id,
                model_version=self.model_version,
                detector_type=self.detector_type,
                p_fake=0.5,
                p_real=0.5,
                raw_confidence=0.0,
                segment_scores=[],
                latency_ms=(time.perf_counter() - t0) * 1000.0,
                status="ERROR",
                error_message=str(exc),
            )


class AcousticForensicDetector(BaseDetector):
    """DSP-based forensic detector inspecting acoustic anomalies.
    
    Checks for vocoder artifacts, artificial pitch rigidity, and spectral distribution anomalies.
    """

    @property
    def detector_id(self) -> str:
        return "dsp-acoustic-forensic"

    @property
    def model_version(self) -> str:
        return "1.0.0"

    @property
    def detector_type(self) -> str:
        return "ACOUSTIC_FORENSIC"

    def is_available(self) -> bool:
        return True

    def detect(
        self,
        full_pcm: np.ndarray,
        segments: List[AudioSegment],
        features: AcousticFeaturesSummary,
        sample_rate: int = 16000,
        claimed_identity: Optional[str] = None,
    ) -> DetectorResult:
        """Evaluate acoustic anomaly indicators from extracted features."""
        t0 = time.perf_counter()

        anomaly_score = 0.0
        factors_counted = 0

        # Indicator 1: Pitch micro-tremor / Jitter
        if features.jitter_local is not None and features.f0_voiced_fraction > 0.3:
            factors_counted += 1
            if features.jitter_local < 0.002:
                anomaly_score += 0.7
            elif features.jitter_local > 0.08:
                anomaly_score += 0.6
            else:
                anomaly_score += 0.1

        # Indicator 2: Spectral Flatness (Vocoder noise floor)
        factors_counted += 1
        if features.spectral_flatness_mean > 0.04:
            anomaly_score += 0.65
        elif features.spectral_flatness_mean > 0.02:
            anomaly_score += 0.35
        else:
            anomaly_score += 0.1

        # Indicator 3: Pitch Standard Deviation
        if features.f0_std_hz is not None and features.f0_voiced_fraction > 0.3:
            factors_counted += 1
            if features.f0_std_hz < 5.0:
                anomaly_score += 0.75
            else:
                anomaly_score += 0.15

        p_fake = anomaly_score / max(1, factors_counted) if factors_counted > 0 else 0.5
        p_real = 1.0 - p_fake
        latency = (time.perf_counter() - t0) * 1000.0

        raw_conf = (factors_counted / 3.0) * 0.5 + abs(p_fake - 0.5)
        conf = float(np.clip(raw_conf, 0.40, 0.95))

        return DetectorResult(
            detector_id=self.detector_id,
            model_version=self.model_version,
            detector_type=self.detector_type,
            p_fake=float(np.clip(p_fake, 0.01, 0.99)),
            p_real=float(np.clip(p_real, 0.01, 0.99)),
            raw_confidence=conf,
            segment_scores=[],
            latency_ms=latency,
            status="OK",
        )


class DetectorRegistry:
    """Registry coordinating multiple pluggable anti-spoofing detectors."""

    def __init__(self):
        self._detectors: Dict[str, BaseDetector] = {}

    def register(self, detector: BaseDetector) -> None:
        """Register a detector instance."""
        self._detectors[detector.detector_id] = detector

    def list_detectors(self) -> List[str]:
        """List registered detector IDs."""
        return list(self._detectors.keys())

    def get(self, detector_id: str) -> Optional[BaseDetector]:
        """Get detector by ID."""
        return self._detectors.get(detector_id)

    def run_all(
        self,
        full_pcm: np.ndarray,
        segments: List[AudioSegment],
        features: AcousticFeaturesSummary,
        sample_rate: int = 16000,
        claimed_identity: Optional[str] = None,
    ) -> List[DetectorResult]:
        """Run all registered available detectors."""
        results = []
        for det in self._detectors.values():
            if det.is_available():
                results.append(
                    det.detect(
                        full_pcm=full_pcm,
                        segments=segments,
                        features=features,
                        sample_rate=sample_rate,
                        claimed_identity=claimed_identity,
                    )
                )
        return results


def get_default_detector_registry() -> DetectorRegistry:
    """Create default detector registry with Wav2Vec2, WavLM x-vector, and DSP Forensic detectors."""
    registry = DetectorRegistry()
    registry.register(Wav2Vec2DeepfakeDetector.get_instance())
    registry.register(WavLMSpeakerVerificationDetector.get_instance())
    registry.register(AcousticForensicDetector())
    return registry
