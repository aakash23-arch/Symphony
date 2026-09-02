"""API integration tests for the canonical inference endpoints."""

import base64
import io
import numpy as np
import pytest
import soundfile as sf
from fastapi.testclient import TestClient

from voiceshield.api.app import create_app
from voiceshield.pipeline.contracts import PolicyVerdict


def make_test_wav_bytes(duration_s: float = 2.0, freq: float = 220.0) -> bytes:
    t = np.linspace(0, duration_s, int(16000 * duration_s), endpoint=False, dtype=np.float32)
    sig = 0.5 * np.sin(2 * np.pi * freq * t)
    bio = io.BytesIO()
    sf.write(bio, sig, 16000, format="WAV", subtype="PCM_16")
    return bio.getvalue()


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


class TestCanonicalInferenceAPI:
    def test_json_base64_payload_inference(self, client):
        wav_bytes = make_test_wav_bytes(duration_s=2.0)
        b64_audio = base64.b64encode(wav_bytes).decode("utf-8")

        payload = {
            "session_id": "sess-canon-01",
            "audio_base64": b64_audio,
            "transaction": {
                "caller_identity": "cfo.ananya",
                "amount": "2500000.00",
                "currency": "INR",
                "beneficiary": "Supplier Ltd",
            },
        }

        resp = client.post("/api/inference", json=payload)
        assert resp.status_code == 200, f"Inference failed: {resp.text}"
        data = resp.json()

        assert data["session_id"] == "sess-canon-01"
        assert data["is_valid_audio"] is True
        assert "overall_risk" in data
        assert "risk_score" in data["overall_risk"]
        assert "risk_band" in data["overall_risk"]
        assert "severity_level" in data["overall_risk"]
        assert "summary" in data["overall_risk"]
        
        assert "decision" in data
        assert "verdict" in data["decision"]
        assert "matched_rule" in data["decision"]
        
        assert "confidence" in data
        assert "score" in data["confidence"]
        assert "confidence_interval" in data["confidence"]
        
        assert "detector_scores" in data
        assert len(data["detector_scores"]) >= 1
        for det in data["detector_scores"]:
            assert "detector_id" in det
            assert "p_synthetic" in det
            assert "confidence" in det
            assert "latency_ms" in det
            
        assert "evidence_items" in data
        assert len(data["evidence_items"]) >= 1
        for ev in data["evidence_items"]:
            assert "signal" in ev
            assert "category" in ev
            assert "score" in ev
            assert "severity" in ev
            assert "explanation" in ev
            
        assert "processing_latency" in data
        assert data["processing_latency"]["total_ms"] > 0
        assert "audio_metadata" in data
        assert data["audio_metadata"]["sample_rate_hz"] == 16000
        assert "model_versions" in data
        
        assert "verdict" in data
        assert "calibrated_p_synthetic" in data
        assert "calibration" in data
        assert "detectors" in data
        assert "explanation" in data
        assert len(data["detectors"]) >= 1

    def test_fixture_inference(self, client):
        payload = {
            "session_id": "sess-fixture-02",
            "audio_fixture": "case_01_authentic_human",
        }

        resp = client.post("/api/inference", json=payload)
        assert resp.status_code == 200, f"Fixture inference failed: {resp.text}"
        data = resp.json()

        assert data["session_id"] == "sess-fixture-02"
        assert data["is_valid_audio"] is True
        assert data["preprocessing"]["snr_db"] > 0

    def test_multipart_file_upload_inference(self, client):
        wav_bytes = make_test_wav_bytes(duration_s=2.0)

        files = {
            "file": ("test_sample.wav", io.BytesIO(wav_bytes), "audio/wav"),
        }
        data = {
            "session_id": "sess-upload-03",
        }

        resp = client.post("/api/inference/upload", files=files, data=data)
        assert resp.status_code == 200, f"Upload inference failed: {resp.text}"
        res = resp.json()

        assert res["session_id"] == "sess-upload-03"
        assert res["is_valid_audio"] is True
        assert "verdict" in res

    def test_v1_alias_parity(self, client):
        wav_bytes = make_test_wav_bytes(duration_s=2.0)
        b64_audio = base64.b64encode(wav_bytes).decode("utf-8")

        payload = {
            "audio_base64": b64_audio,
        }

        resp_api = client.post("/api/inference", json=payload)
        resp_v1 = client.post("/v1/inference", json=payload)

        assert resp_api.status_code == 200
        assert resp_v1.status_code == 200
        assert resp_api.json()["verdict"] == resp_v1.json()["verdict"]
