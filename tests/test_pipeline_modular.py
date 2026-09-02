"""Unit and invariant tests for the modular anti-spoofing pipeline components."""

import io
import math
import numpy as np
import pytest
import soundfile as sf

from voiceshield.pipeline.contracts import (
    AudioFormat,
    InferenceRequest,
    PolicyVerdict,
    RiskBand,
    TransactionContext,
    ValidationStatus,
)
from voiceshield.pipeline.detectors import (
    AcousticForensicDetector,
    DetectorRegistry,
    Wav2Vec2DeepfakeDetector,
)
from voiceshield.pipeline.features import FeatureExtractor
from voiceshield.pipeline.orchestrator import InferenceOrchestrator
from voiceshield.pipeline.preprocessor import AudioPreprocessor
from voiceshield.pipeline.validator import AudioValidator


def make_test_wav(
    duration_s: float = 2.0,
    sample_rate: int = 16000,
    freq: float = 220.0,
    channels: int = 1,
) -> bytes:
    """Helper to synthesize test WAV bytes."""
    t = np.linspace(0, duration_s, int(sample_rate * duration_s), endpoint=False, dtype=np.float32)
    sig = 0.5 * np.sin(2 * np.pi * freq * t)
    # Add second harmonic
    sig += 0.2 * np.sin(2 * np.pi * 2 * freq * t)
    if channels == 2:
        sig = np.column_stack([sig, sig])

    bio = io.BytesIO()
    sf.write(bio, sig, sample_rate, format="WAV", subtype="PCM_16")
    return bio.getvalue()


class TestAudioValidator:
    def test_valid_wav_is_accepted(self):
        wav_bytes = make_test_wav(duration_s=2.0)
        validator = AudioValidator()
        is_valid, report = validator.validate_bytes(wav_bytes)

        assert is_valid is True
        assert report.is_valid is True
        assert report.detected_format == AudioFormat.WAV
        assert report.sample_rate == 16000
        assert report.duration_seconds >= 1.9

    def test_empty_audio_is_rejected(self):
        validator = AudioValidator()
        is_valid, report = validator.validate_bytes(b"")

        assert is_valid is False
        assert report.status == ValidationStatus.EMPTY

    def test_too_short_audio_is_rejected(self):
        wav_bytes = make_test_wav(duration_s=0.1)
        validator = AudioValidator()
        is_valid, report = validator.validate_bytes(wav_bytes)

        assert is_valid is False
        assert any("below minimum" in note for note in report.validation_notes)


class TestAudioPreprocessor:
    def test_decode_and_resample(self):
        pre = AudioPreprocessor()
        # 44.1 kHz stereo audio
        wav_bytes = make_test_wav(duration_s=2.0, sample_rate=44100, channels=2)
        norm_pcm, segments, summary = pre.process(wav_bytes)

        assert summary.target_sample_rate == 16000
        assert summary.original_sample_rate == 44100
        assert summary.original_channels == 2
        assert len(norm_pcm) == int(2.0 * 16000)
        assert len(segments) >= 1
        assert summary.snr_db > 10.0


class TestFeatureExtractor:
    def test_feature_extraction(self):
        extractor = FeatureExtractor()
        t = np.linspace(0, 2.0, 32000, endpoint=False, dtype=np.float32)
        pcm = 0.5 * np.sin(2 * np.pi * 200.0 * t)

        feats = extractor.extract_features(pcm, sample_rate=16000)
        assert feats.spectral_centroid_mean_hz > 0.0
        assert feats.rms_energy_mean > 0.0
        assert feats.spectral_flatness_mean >= 0.0


class TestModularPipelineOrchestrator:
    def test_orchestrator_end_to_end_genuine(self):
        orchestrator = InferenceOrchestrator()
        wav_bytes = make_test_wav(duration_s=2.5, freq=180.0)

        response = orchestrator.process_audio(
            audio_bytes=wav_bytes,
            session_id="test-session-001",
        )

        assert response.session_id == "test-session-001"
        assert response.is_valid_audio is True
        assert response.confidence.score > 0.0
        assert response.calibrated_p_synthetic >= 0.0
        assert len(response.detectors) >= 1
        assert response.decision.verdict in (PolicyVerdict.ALLOW, PolicyVerdict.STEP_UP, PolicyVerdict.HOLD)
        assert len(response.explanation.summary_statement) > 0
        assert response.execution_time_ms > 0.0

    def test_pipeline_with_high_value_transaction(self):
        orchestrator = InferenceOrchestrator()
        wav_bytes = make_test_wav(duration_s=2.5, freq=180.0)

        req = InferenceRequest(
            session_id="tx-session-002",
            transaction=TransactionContext(
                amount=5000000.0,
                beneficiary="Acme Offshore Inc",
                beneficiary_novelty="NEW",
            ),
        )

        response = orchestrator.process_audio(
            audio_bytes=wav_bytes,
            session_id="tx-session-002",
            request=req,
        )

        assert response.session_id == "tx-session-002"
        # Context factors should be documented in explanation
        context_factors = [
            f for f in response.explanation.primary_risk_drivers if f.category == "TRANSACTION_CONTEXT"
        ]
        assert len(context_factors) >= 1
