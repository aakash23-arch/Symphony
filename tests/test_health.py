"""Tests for health endpoint (GET /health and GET /v1/health)."""

from fastapi import status


def test_get_health(client):
    response = client.get("/health")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["app"] == "VoiceShield"
    assert data["status"] in ["healthy", "degraded"]
    assert "dependencies" in data
    assert "python" in data["dependencies"]
    assert data["dependencies"]["python"]["status"] == "OK"
    assert "sqlite" in data["dependencies"]
    assert data["dependencies"]["sqlite"]["status"] == "OK"

    # Per-expert availability report check
    assert "expert_models" in data
    assert "E1" in data["expert_models"]
    assert "E4" in data["expert_models"]
    assert "E5" in data["expert_models"]
    assert data["expert_models"]["E5"]["status"] == "DEFERRED"
    assert data["expert_models"]["E6"]["status"] == "DEFERRED"


def test_get_v1_health(client):
    response = client.get("/v1/health")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["version"] == "0.1.0"


def test_get_health_readiness(client):
    response = client.get("/health/ready")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["status"] in ["ready", "not_ready"]
    assert "models_loaded" in data
    assert "demo_assets_available" in data
    assert "inference_pipeline_operational" in data
    assert data["demo_cases_supported"] == 3
    assert "case_01_authentic_human.wav" in data["demo_assets"]
    assert "case_02_cloned_synthetic.wav" in data["demo_assets"]
    assert "case_03_adversarial_manipulated.wav" in data["demo_assets"]
    assert data["demo_assets"]["case_01_authentic_human.wav"].startswith("VALID")

