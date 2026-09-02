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


class ReadinessResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: str = Field(description="'ready' or 'not_ready'")
    models_loaded: bool
    models: Dict[str, str]
    demo_assets_available: bool
    demo_assets: Dict[str, str]
    inference_pipeline_operational: bool
    demo_cases_supported: int = 3
    timestamp: datetime = Field(description="UTC timestamp")


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
@router.get(
    "/api/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="API Health & Expert Availability",
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


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    status_code=status.HTTP_200_OK,
    summary="Root SIH Demo Readiness Check",
)
@router.get(
    "/v1/ready",
    response_model=ReadinessResponse,
    status_code=status.HTTP_200_OK,
    summary="V1 Root Readiness Check",
)
@router.get(
    "/api/ready",
    response_model=ReadinessResponse,
    status_code=status.HTTP_200_OK,
    summary="API Root Readiness Check",
)
@router.get(
    "/health/ready",
    response_model=ReadinessResponse,
    status_code=status.HTTP_200_OK,
    summary="SIH Demo Readiness Check",
)
@router.get(
    "/v1/health/ready",
    response_model=ReadinessResponse,
    status_code=status.HTTP_200_OK,
    summary="V1 SIH Demo Readiness Check",
)
@router.get(
    "/api/health/ready",
    response_model=ReadinessResponse,
    status_code=status.HTTP_200_OK,
    summary="API SIH Demo Readiness Check",
)
async def get_readiness() -> ReadinessResponse:
    """Verify preloaded models, demo audio assets, and operational pipeline readiness."""
    from pathlib import Path
    import soundfile as sf
    from voiceshield.pipeline.detectors import (
        AcousticForensicDetector,
        Wav2Vec2DeepfakeDetector,
        WavLMSpeakerVerificationDetector,
    )

    models_info: Dict[str, str] = {}
    models_ok = True

    # 1. Models Loaded Check
    w2v = Wav2Vec2DeepfakeDetector.get_instance()
    if w2v.is_available():
        models_info["wav2vec2_deepfake"] = f"{w2v.model_version} (PRELOADED)"
    else:
        models_info["wav2vec2_deepfake"] = "UNAVAILABLE"
        models_ok = False

    wavlm = WavLMSpeakerVerificationDetector.get_instance()
    if wavlm.is_available():
        models_info["wavlm_speaker_sv"] = f"{wavlm.model_version} (PRELOADED)"
    else:
        models_info["wavlm_speaker_sv"] = "UNAVAILABLE"
        models_ok = False

    forensic = AcousticForensicDetector()
    if forensic.is_available():
        models_info["dsp_forensic_physics"] = f"{forensic.model_version} (OPERATIONAL)"
    else:
        models_info["dsp_forensic_physics"] = "UNAVAILABLE"
        models_ok = False

    # 2. Demo Assets Check
    audio_dir = Path("demo/audio")
    demo_files = [
        "case_01_authentic_human.wav",
        "case_02_cloned_synthetic.wav",
        "case_03_adversarial_manipulated.wav",
    ]
    assets_info: Dict[str, str] = {}
    assets_ok = True

    for filename in demo_files:
        path = audio_dir / filename
        if path.exists():
            try:
                info = sf.info(str(path))
                assets_info[filename] = f"VALID (duration: {info.duration:.2f}s, {info.samplerate}Hz, channels: {info.channels})"
            except Exception as exc:
                assets_info[filename] = f"CORRUPTED ({str(exc)})"
                assets_ok = False
        else:
            assets_info[filename] = "MISSING"
            assets_ok = False

    is_ready = models_ok and assets_ok

    return ReadinessResponse(
        status="ready" if is_ready else "not_ready",
        models_loaded=models_ok,
        models=models_info,
        demo_assets_available=assets_ok,
        demo_assets=assets_info,
        inference_pipeline_operational=is_ready,
        demo_cases_supported=3,
        timestamp=datetime.now(timezone.utc),
    )

