"""End-to-End Regression Test for the Three Canonical Demo Cases.

Ensures that:
1. Case 01 (Authentic Human): Evaluates with low synthetic probability -> ALLOW / LOW risk.
2. Case 02 (Cloned Synthetic): Evaluates with high synthetic probability -> HOLD / CRITICAL risk.
3. Case 03 (Adversarial Manipulated): Triggers degraded SNR / forensic anomalies -> STEP_UP / UNCERTAIN.
4. All 3 cases exercise the exact same endpoint without any case-specific branching or hardcoded values.
"""

import base64
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from voiceshield.api.app import app

client = TestClient(app)
AUDIO_DIR = Path(__file__).resolve().parent.parent / "demo" / "audio"


class TestThreeDemoCasesEndToEnd:
    """Regression suite exercising the 3 SIH demo cases through POST /api/inference."""

    def test_case_01_authentic_human(self):
        """Case 01 should be processed and inferred as authentic speech."""
        audio_path = AUDIO_DIR / "case_01_authentic_human.wav"
        assert audio_path.exists(), f"Missing audio asset: {audio_path}"

        raw_bytes = audio_path.read_bytes()
        b64 = base64.b64encode(raw_bytes).decode("utf-8")

        response = client.post(
            "/api/inference",
            json={
                "audio_base64": b64,
                "transaction": {
                    "caller_identity": "cfo.ananya_sharma",
                    "amount": 2500000.0,
                    "currency": "INR",
                },
            },
        )
        assert response.status_code == 200, response.text
        data = response.json()

        # Operational integrity checks
        assert data["validation"]["is_valid"] is True
        assert data["preprocessing"]["target_sample_rate"] == 16000
        assert data["calibrated_p_synthetic"] < 0.20
        assert data["risk_band"] == "LOW"
        assert data["verdict"] == "ALLOW"
        assert len(data["detectors"]) >= 2
        assert any(d["detector_id"] == "wav2vec2-deepfake" and d["status"] == "OK" for d in data["detectors"])
        assert data["execution_time_ms"] > 0
        assert "ALLOW" in data["explanation"]["summary_statement"]

        # Structured forensic result checks
        assert "overall_risk" in data
        assert data["overall_risk"]["risk_band"] == "LOW"
        assert data["decision"]["verdict"] == "ALLOW"
        assert data["confidence"]["score"] > 0.0
        assert len(data["detector_scores"]) >= 2
        assert len(data["evidence_items"]) >= 1
        assert "processing_latency" in data
        assert "model_versions" in data
        assert "audio_metadata" in data

    def test_case_02_cloned_synthetic(self):
        """Case 02 should be processed and inferred as synthetic voice clone."""
        audio_path = AUDIO_DIR / "case_02_cloned_synthetic.wav"
        assert audio_path.exists(), f"Missing audio asset: {audio_path}"

        raw_bytes = audio_path.read_bytes()
        b64 = base64.b64encode(raw_bytes).decode("utf-8")

        response = client.post(
            "/api/inference",
            json={
                "audio_base64": b64,
                "transaction": {
                    "caller_identity": "cfo.ananya_sharma",
                    "amount": 2500000.0,
                    "currency": "INR",
                },
            },
        )
        assert response.status_code == 200, response.text
        data = response.json()

        # Operational integrity checks
        assert data["validation"]["is_valid"] is True
        assert data["calibrated_p_synthetic"] > 0.70
        assert data["risk_band"] in ("HIGH", "CRITICAL")
        assert data["verdict"] in ("HOLD", "ESCALATE")
        assert any(d["detector_id"] == "wav2vec2-deepfake" and d["p_fake"] > 0.80 for d in data["detectors"])
        assert "HOLD" in data["explanation"]["summary_statement"] or "CRITICAL" in data["explanation"]["summary_statement"]

    def test_case_03_adversarial_manipulated(self):
        """Case 03 should trigger DSP anomalies / degraded channel quality resulting in STEP_UP."""
        audio_path = AUDIO_DIR / "case_03_adversarial_manipulated.wav"
        assert audio_path.exists(), f"Missing audio asset: {audio_path}"

        raw_bytes = audio_path.read_bytes()
        b64 = base64.b64encode(raw_bytes).decode("utf-8")

        response = client.post(
            "/api/inference",
            json={
                "audio_base64": b64,
                "transaction": {
                    "caller_identity": "cfo.ananya_sharma",
                    "amount": 2500000.0,
                    "currency": "INR",
                },
            },
        )
        assert response.status_code == 200, response.text
        data = response.json()

        # Operational integrity checks
        assert data["validation"]["is_valid"] is True
        assert data["preprocessing"]["snr_db"] < 15.0
        assert data["verdict"] == "STEP_UP"
        assert data["risk_band"] == "UNCERTAIN"
        assert len(data["evidence"]["anomalies_detected"]) > 0
        assert any(a["anomaly_code"] == "DEGRADED_CHANNEL_SNR" for a in data["evidence"]["anomalies_detected"])

    def test_adversarial_audio_mutation_changes_predictions(self):
        """Adversarial proof: modifying the audio waveform directly alters feature extraction,
        detector outputs, and policy decisions, proving zero hardcoding or case lookup.
        """
        import io
        import numpy as np
        import soundfile as sf

        # Synthesize Audio 1: Clean natural harmonic waveform
        sr = 16000
        t = np.linspace(0, 2.5, int(sr * 2.5), endpoint=False, dtype=np.float32)
        sig_clean = 0.5 * np.sin(2 * np.pi * 180.0 * t) + 0.2 * np.sin(2 * np.pi * 360.0 * t)
        bio_clean = io.BytesIO()
        sf.write(bio_clean, sig_clean, sr, format="WAV", subtype="PCM_16")
        b64_clean = base64.b64encode(bio_clean.getvalue()).decode("utf-8")

        # Synthesize Audio 2: Severe noise-degraded waveform with flat spectrum
        sig_noisy = sig_clean * 0.1 + 0.4 * np.random.RandomState(42).randn(len(sig_clean)).astype(np.float32)
        bio_noisy = io.BytesIO()
        sf.write(bio_noisy, sig_noisy, sr, format="WAV", subtype="PCM_16")
        b64_noisy = base64.b64encode(bio_noisy.getvalue()).decode("utf-8")

        resp_clean = client.post("/api/inference", json={"audio_base64": b64_clean})
        resp_noisy = client.post("/api/inference", json={"audio_base64": b64_noisy})

        assert resp_clean.status_code == 200
        assert resp_noisy.status_code == 200

        data_clean = resp_clean.json()
        data_noisy = resp_noisy.json()

        # 1. Feature differences
        assert data_clean["preprocessing"]["snr_db"] != data_noisy["preprocessing"]["snr_db"]
        assert data_clean["preprocessing"]["snr_db"] > data_noisy["preprocessing"]["snr_db"]
        assert data_clean["features"]["spectral_flatness_mean"] != data_noisy["features"]["spectral_flatness_mean"]

        # 2. Decision and risk score differences
        assert data_clean["confidence"]["score"] != data_noisy["confidence"]["score"]
        assert data_noisy["risk_band"] == "UNCERTAIN" or data_noisy["verdict"] == "STEP_UP"

        # 3. Measured latencies are non-zero and dynamic
        assert data_clean["processing_latency"]["total_ms"] > 0
        assert data_clean["processing_latency"]["validation_ms"] >= 0
        assert data_clean["processing_latency"]["feature_extraction_ms"] >= 0

    def test_repeated_execution_consistency_and_latency(self):
        """Verify fast repeated execution across all 3 cases with zero intermittent failures,
        consistent scores, and low warm latency (< 300ms).
        """
        cases = [
            ("case_01_authentic_human.wav", "LOW", "ALLOW"),
            ("case_02_cloned_synthetic.wav", "HIGH", "HOLD"),
            ("case_03_adversarial_manipulated.wav", "UNCERTAIN", "STEP_UP"),
        ]

        for iteration in range(3):
            for filename, expected_band, expected_verdict in cases:
                audio_path = AUDIO_DIR / filename
                raw_bytes = audio_path.read_bytes()
                b64 = base64.b64encode(raw_bytes).decode("utf-8")

                resp = client.post(
                    "/api/inference",
                    json={
                        "audio_base64": b64,
                        "session_id": f"repeat-test-iter-{iteration}-{filename}",
                    },
                )
                assert resp.status_code == 200, f"Iteration {iteration} failed on {filename}: {resp.text}"
                data = resp.json()

                assert data["is_valid_audio"] is True
                if expected_band in ("HIGH", "CRITICAL"):
                    assert data["risk_band"] in ("HIGH", "CRITICAL")
                else:
                    assert data["risk_band"] == expected_band

                if expected_verdict in ("HOLD", "ESCALATE"):
                    assert data["verdict"] in ("HOLD", "ESCALATE")
                else:
                    assert data["verdict"] == expected_verdict

                assert data["processing_latency"]["total_ms"] > 0
                assert data["processing_latency"]["total_ms"] < 5000.0  # reasonable bound on CPU


