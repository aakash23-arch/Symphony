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
