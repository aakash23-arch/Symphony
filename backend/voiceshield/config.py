"""VoiceShield configuration module (C-52).

Loads, validates, and provides access to application settings across all runtime roles.
"""

from enum import Enum
from typing import List, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppRole(str, Enum):
    API = "api"
    ANALYSIS_WORKER = "analysis-worker"
    DECISION_WORKER = "decision-worker"
    ALL_IN_ONE = "all-in-one"


class Environment(str, Enum):
    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """VoiceShield unified application settings."""

    model_config = SettingsConfigDict(
        env_prefix="VOICESHIELD_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Runtime Identity
    role: AppRole = Field(default=AppRole.ALL_IN_ONE, description="Process role")
    env: Environment = Field(default=Environment.DEVELOPMENT, description="Deployment environment")
    debug: bool = Field(default=False, description="Debug mode flag")
    app_version: str = Field(default="0.1.0", description="VoiceShield build version")

    # API Server
    host: str = Field(default="0.0.0.0", description="Host address")
    port: int = Field(default=8000, description="Port number")
    cors_origins: Union[List[str], str] = Field(
        default=["http://localhost:5173", "http://127.0.0.1:5173"],
        description="Allowed CORS origins",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if v.strip().startswith("[") and v.strip().endswith("]"):
                import json
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return [str(i) for i in v]
        return list(v)

    # Logging
    log_level: str = Field(default="INFO", description="Log level")
    log_format: str = Field(default="json", description="Log format: json or text")

    # Redis Streaming Infrastructure
    redis_url: str = Field(default="redis://localhost:6379/0", description="Redis connection URL")
    redis_max_connections: int = Field(default=20, description="Redis pool max connections")
    redis_stream_maxlen: int = Field(default=10000, description="Max frame buffer retention")

    # SQLite Persistence
    sqlite_path: str = Field(default="data/voiceshield.sqlite3", description="SQLite database file path")

    # Audio DSP Ingestion Constants
    audio_sample_rate: int = Field(default=16000, description="Target sample rate in Hz")
    audio_channels: int = Field(default=1, description="Single channel (mono)")
    audio_frame_ms: int = Field(default=20, description="Audio frame duration in ms (320 samples)")
    audio_window_ms: int = Field(default=1000, description="Inference window size in ms")
    audio_hop_ms: int = Field(default=250, description="Inference hop size in ms")

    # ML Inference & Models
    models_dir: str = Field(default="assets/models", description="Local weights directory")
    device: str = Field(default="cpu", description="Inference device: cpu | cuda | mps")
    torch_threads: int = Field(default=4, description="PyTorch intra-op threads")

    # Model artefacts & offline cold start (C-27, readiness R12)
    models_offline: bool = Field(
        default=True,
        description="Force HF_HUB_OFFLINE: weights must be vendored, never fetched at runtime",
    )
    models_manifest: str = Field(
        default="assets/models/manifest.json", description="Vendored artefact manifest with sha256"
    )
    verify_model_checksums: bool = Field(
        default=True, description="Verify artefact sha256 against the manifest before loading"
    )

    # Deterministic evaluation mode
    deterministic_mode: bool = Field(
        default=True, description="Seed torch and prefer deterministic kernels"
    )
    torch_seed: int = Field(default=20260828, description="Seed (matches the audio fixture seed)")

    # Expert execution (C-19)
    expert_timeout_ms: int = Field(default=1500, description="Per-expert inference time budget")
    expert_max_workers: int = Field(default=4, description="Inference thread pool size")
    expert_warmup_on_start: bool = Field(
        default=True,
        description="Load models at startup; a cold load is ~53s and would blow the first frame",
    )

    # Expert -> artefact binding
    e2_model_key: str = Field(default="wav2vec2_deepfake", description="Manifest key for E2")
    e4_model_key: str = Field(default="wavlm_base_plus_sv", description="Manifest key for E4")

    # E4 speaker verification (C-23)
    # A FrameObject carries audio_hop_ms of audio (250 ms = 4000 samples), which is
    # BELOW the measured 4880-sample floor of WavLMForXVector. E4 therefore buffers
    # across frames and re-scores on a stride rather than per frame.
    e4_buffer_ms: int = Field(default=2000, description="Rolling PCM buffer length for E4")
    e4_stride_ms: int = Field(default=1000, description="Minimum interval between E4 re-scores")
    e4_min_samples: int = Field(
        default=4880, description="Measured hard floor for WavLMForXVector; below this it raises"
    )
    e4_similarity_threshold: float = Field(
        default=0.70,
        description="Reported alongside similarity for explanation; L3 does NOT decide on it",
    )
    e4_max_sessions: int = Field(default=64, description="LRU cap on per-session PCM buffers")
    enrollment_path: str = Field(
        default="data/enrollment.json", description="Speaker reference embedding store"
    )

    # Decision & Policy
    policy_version: str = Field(default="1.0.0", description="Active policy engine version")
    risk_threshold_warn: float = Field(default=0.45, description="Warning risk boundary")
    risk_threshold_crit: float = Field(default=0.75, description="Critical risk boundary")

    def redacted_dict(self) -> dict:
        """Return a dictionary of settings suitable for logging with secrets redacted."""
        dump = self.model_dump()
        if "redis_url" in dump and "@" in dump["redis_url"]:
            # Redact password in redis url if present
            prefix, rest = dump["redis_url"].split("://", 1)
            creds, host_part = rest.split("@", 1)
            dump["redis_url"] = f"{prefix}://***:***@{host_part}"
        return dump


# Global singleton instance
settings = Settings()
