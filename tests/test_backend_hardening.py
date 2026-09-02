"""Tests to verify backend ML hardening requirements."""

import base64
import json
import pytest
from fastapi.testclient import TestClient
from voiceshield.api.app import app
from pathlib import Path

client = TestClient(app)
AUDIO_DIR = Path(__file__).resolve().parent.parent / "demo" / "audio"

def test_same_audio_deterministic_result():
    """Verify same audio returns deterministic result within numerical tolerance."""
    audio_path = AUDIO_DIR / "case_01_authentic_human.wav"
    raw_bytes = audio_path.read_bytes()
    b64 = base64.b64encode(raw_bytes).decode("utf-8")

    r1 = client.post("/api/inference", json={"audio_base64": b64})
    r2 = client.post("/api/inference", json={"audio_base64": b64})

    assert r1.status_code == 200
    assert r2.status_code == 200

    d1 = r1.json()
    d2 = r2.json()

    assert abs(d1["calibrated_p_synthetic"] - d2["calibrated_p_synthetic"]) < 1e-4
    assert abs(d1["confidence_score"] - d2["confidence_score"]) < 1e-4
    assert d1["risk_band"] == d2["risk_band"]

def test_metadata_cannot_influence_prediction():
    """Verify changing scenario metadata does not change the core prediction."""
    audio_path = AUDIO_DIR / "case_02_cloned_synthetic.wav"
    raw_bytes = audio_path.read_bytes()
    b64 = base64.b64encode(raw_bytes).decode("utf-8")

    req1 = {
        "audio_base64": b64,
        "context_parameters": {"expected_outcome": "ALLOW", "risk": "LOW", "score": 0.1}
    }
    req2 = {
        "audio_base64": b64,
        "context_parameters": {"expected_outcome": "HOLD", "risk": "HIGH", "score": 0.9}
    }

    r1 = client.post("/api/inference", json=req1)
    r2 = client.post("/api/inference", json=req2)

    assert r1.status_code == 200
    assert r2.status_code == 200

    d1 = r1.json()
    d2 = r2.json()

    # The prediction must be purely based on the audio
    assert abs(d1["calibrated_p_synthetic"] - d2["calibrated_p_synthetic"]) < 1e-4

def test_invalid_audio_fails_explicitly():
    """Verify invalid audio causes explicit degraded state."""
    b64 = base64.b64encode(b"not a valid audio file bytes").decode("utf-8")
    resp = client.post("/api/inference", json={"audio_base64": b64})
    assert resp.status_code == 200
    data = resp.json()
    
    assert data["is_valid_audio"] is False
    assert data["risk_band"] == "UNCERTAIN"
    assert data["confidence_score"] == 0.0

def test_demo_cases_return_exactly_three_scenarios():
    """Verify exactly 3 canonical cases exist."""
    resp = client.get("/api/demo/cases")
    assert resp.status_code == 200
    data = resp.json()
    scenarios = data.get("scenarios", [])
    assert len(scenarios) == 3
    ids = [s["scenario_id"] for s in scenarios]
    assert "case-01-authentic" in ids
    assert "case-02-cloned" in ids
    assert "case-03-adversarial" in ids

