"""Health and dependency readiness check endpoint (GET /health and GET /v1/health)."""

import os
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from typing import Any, Dict
from fastapi import APIRouter, status
from pydantic import BaseModel, ConfigDict, Field

from voiceshield.config import settings
from voiceshield.models.registry import expert_registry


class DependencyStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: str = Field(description="'OK', 'DEGRADED', 'UNAVAILABLE', or 'NOT_INSTALLED'")
    details: Dict[str, Any] = Field(default_factory=dict)


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: str = Field(description="'healthy' or 'degraded'")
    app: str = Field(default="VoiceShield")
    version: str = Field(default=settings.app_version)
    role: str = Field(default=settings.role.value)
    environment: str = Field(default=settings.env.value)
    timestamp: datetime = Field(description="UTC timestamp")
    dependencies: Dict[str, DependencyStatus] = Field(description="System and library dependencies")
    expert_models: Dict[str, Dict[str, str]] = Field(description="Per-expert availability report")


router = APIRouter(tags=["Health"])


def _check_python() -> DependencyStatus:
    return DependencyStatus(
        status="OK",
        details={
            "version": sys.version.split()[0],
            "executable": sys.executable,
        },
    )


def _check_sqlite() -> DependencyStatus:
    try:
        conn = sqlite3.connect(":memory:")
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.fetchone()
        conn.close()
        return DependencyStatus(
            status="OK",
            details={"sqlite_version": sqlite3.sqlite_version},
        )
    except Exception as e:
        return DependencyStatus(status="UNAVAILABLE", details={"error": str(e)})


def _check_ffmpeg() -> DependencyStatus:
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        return DependencyStatus(status="OK", details={"path": ffmpeg_path})
    return DependencyStatus(
        status="UNAVAILABLE",
        details={"warning": "FFmpeg binary not found on system PATH; PCM WAV fallback only"},
    )


def _check_ml_frameworks() -> DependencyStatus:
    details: Dict[str, Any] = {}
    # PyTorch
    try:
        import torch
        details["torch"] = {"version": torch.__version__, "cuda_available": torch.cuda.is_available()}
    except ImportError:
        details["torch"] = "NOT_INSTALLED"

    # Librosa & SoundFile
    try:
        import librosa
        details["librosa"] = librosa.__version__
    except ImportError:
        details["librosa"] = "NOT_INSTALLED"

    try:
        import soundfile
        details["soundfile"] = soundfile.__version__
    except ImportError:
        details["soundfile"] = "NOT_INSTALLED"

    return DependencyStatus(status="OK" if "torch" in details else "DEGRADED", details=details)


def _check_redis() -> DependencyStatus:
    # Synchronous ping test
    try:
        import redis
        client = redis.from_url(settings.redis_url, socket_connect_timeout=0.2)
        client.ping()
        client.close()
        return DependencyStatus(status="OK", details={"url": settings.redacted_dict().get("redis_url")})
    except Exception as e:
        return DependencyStatus(
            status="DEGRADED" if settings.role.value == "all-in-one" else "UNAVAILABLE",
            details={
                "error": str(e),
                "note": "Redis optional in single-process all-in-one mode, required for 3-process topology",
            },
        )


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Application Health & Dependency Readiness",
)
@router.get(
    "/v1/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="V1 Health & Expert Availability",
)
async def get_health() -> HealthResponse:
    """Report genuine live application health, runtime dependencies, and model availability."""
    deps: Dict[str, DependencyStatus] = {
        "python": _check_python(),
        "sqlite": _check_sqlite(),
        "ffmpeg": _check_ffmpeg(),
        "ml_frameworks": _check_ml_frameworks(),
        "redis": _check_redis(),
    }

    expert_report = expert_registry.get_availability_report()

    # System is healthy if core runtime dependencies are OK
    is_healthy = deps["python"].status == "OK" and deps["sqlite"].status == "OK"

    return HealthResponse(
        status="healthy" if is_healthy else "degraded",
        app="VoiceShield",
        version=settings.app_version,
        role=settings.role.value,
        environment=settings.env.value,
        timestamp=datetime.now(timezone.utc),
        dependencies=deps,
        expert_models=expert_report,
    )
