"""Integration tests for the minimal production-style API contract.

Required operations:
- GET /health
- GET /ready
- GET /demo/cases
- POST /detect
"""

import base64
import io
from pathlib import Path
import numpy as np
import pytest
import soundfile as sf
from fastapi.testclient import TestClient

from voiceshield.api.app import app

client = TestClient(app)
AUDIO_DIR = Path(__file__).resolve().parent.parent / "demo" / "audio"


def make_test_wav_bytes(duration_s: float = 2.0, freq: float = 220.0) -> bytes:
    t = np.linspace(0, duration_s, int(16000 * duration_s), endpoint=False, dtype=np.float32)
    sig = 0.5 * np.sin(2 * np.pi * freq * t)
    bio = io.BytesIO()
    sf.write(bio, sig, 16000, format="WAV", subtype="PCM_16")
    return bio.getvalue()


class TestMinimalProductionContract:
    def test_get_health(self):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("healthy", "degraded")
        assert data["app"] == "VoiceShield"
        assert "dependencies" in data
        assert "timestamp" in data

    def test_get_ready(self):
        resp = client.get("/ready")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ready"
        assert data["models_loaded"] is True
        assert data["demo_assets_available"] is True
        assert data["inference_pipeline_operational"] is True
        assert data["demo_cases_supported"] == 3
        assert len(data["demo_assets"]) == 3

    def test_get_demo_cases(self):
        resp = client.get("/demo/cases")
        assert resp.status_code == 200
        data = resp.json()
        assert "scenarios" in data
        assert len(data["scenarios"]) == 3

        # Verify only safe display metadata is present
        for sc in data["scenarios"]:
            assert "scenario_id" in sc
            assert "title" in sc
            assert "summary" in sc
            assert "caller_name" in sc
            assert "caller_ref" in sc
            assert "audio_fixture" in sc
            assert "context" in sc

    def test_post_detect_json(self):
        wav_bytes = make_test_wav_bytes(duration_s=2.0)
        b64_audio = base64.b64encode(wav_bytes).decode("utf-8")

        payload = {
            "session_id": "req-prod-001",
            "audio_base64": b64_audio,
            "transaction": {
                "caller_identity": "cfo.ananya_sharma",
                "amount": "2500000.00",
                "currency": "INR",
                "beneficiary": "Supplier Ltd",
            },
        }

        resp = client.post("/detect", json=payload)
        assert resp.status_code == 200, resp.text
        data = resp.json()

        # Core required contract metadata
        assert data["request_id"] == "req-prod-001"
        assert data["session_id"] == "req-prod-001"
        assert "timestamp" in data
        assert data["pipeline_version"] == "voiceshield-pipeline-v3.0"
        assert "model_versions" in data
        assert "processing_time" in data
        assert data["processing_time"] > 0

        # Structured evidence & forensic results
        assert "overall_risk" in data
        assert "risk_score" in data["overall_risk"]
        assert "risk_band" in data["overall_risk"]
        assert "summary" in data["overall_risk"]

        assert "decision" in data
        assert "verdict" in data["decision"]
        assert "matched_rule" in data["decision"]

        assert "confidence" in data
        assert "score" in data["confidence"]
        assert "confidence_interval" in data["confidence"]

        assert "detector_scores" in data
        assert len(data["detector_scores"]) >= 1

        assert "evidence_items" in data
        assert len(data["evidence_items"]) >= 1

        assert "audio_metadata" in data
        assert data["audio_metadata"]["sample_rate_hz"] == 16000

    def test_post_detect_upload(self):
        wav_bytes = make_test_wav_bytes(duration_s=1.5)
        files = {"file": ("audio_sample.wav", io.BytesIO(wav_bytes), "audio/wav")}
        data = {"session_id": "req-upload-002"}

        resp = client.post("/detect/upload", files=files, data=data)
        assert resp.status_code == 200, resp.text
        res = resp.json()

        assert res["request_id"] == "req-upload-002"
        assert res["is_valid_audio"] is True
        assert res["processing_time"] > 0
        assert "overall_risk" in res

    def test_post_detect_fixture(self):
        payload = {
            "session_id": "req-fixture-003",
            "audio_fixture": "case_01_authentic_human",
        }

        resp = client.post("/detect", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["request_id"] == "req-fixture-003"
        assert data["is_valid_audio"] is True
        assert data["overall_risk"]["risk_band"] == "LOW"
        assert data["decision"]["verdict"] == "ALLOW"

    def test_detect_error_envelope_on_missing_payload(self):
        resp = client.post("/detect", json={})
        assert resp.status_code in (400, 422)
        data = resp.json()
        # Standard error envelope format
        assert "error" in data or "detail" in data
