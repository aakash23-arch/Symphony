"""Pytest test fixtures and configuration."""

import json
import wave
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from audio_fixtures import (
    FIXTURE_RATE,
    silence,
    standard_fixture_samples,
    tone,
    write_wav,
)
from voiceshield.api.app import create_app
from voiceshield.config import Settings

REPO_ROOT = Path(__file__).resolve().parents[1]


# --- L3 model-weight gating ---------------------------------------------------
#
# The suite MUST pass with no weights vendored - that is the default CI state and
# it is what proves graceful degradation. Tests that need real inference are
# skipped rather than failed when assets/models is empty.


def _manifest_complete(models_dir: Path = None) -> bool:
    """True only if the manifest exists AND every file it lists is present."""
    root = models_dir or (REPO_ROOT / "assets" / "models")
    manifest_path = root / "manifest.json"
    if not manifest_path.exists():
        return False
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False

    models = manifest.get("models") or {}
    if not models:
        return False

    for entry in models.values():
        model_root = root / entry.get("local_dir", "")
        for rel in (entry.get("files") or {}):
            if not (model_root / rel).exists():
                return False
    return True


def _speech_samples_present() -> bool:
    """True if the real-speech corpus used by the E4 behaviour test is cached."""
    try:
        import pyarrow.parquet
        from huggingface_hub import try_to_load_from_cache
    except ImportError:
        return False
    hit = try_to_load_from_cache(
        "hf-internal-testing/librispeech_asr_demo",
        "clean/validation-00000-of-00001.parquet",
        repo_type="dataset",
    )
    return isinstance(hit, str) and Path(hit).exists()


requires_weights = pytest.mark.skipif(
    not _manifest_complete(),
    reason="model weights not vendored; run: python scripts/fetch_models.py",
)

requires_speech_samples = pytest.mark.skipif(
    not _speech_samples_present(),
    reason="real speech corpus not cached; run: python scripts/fetch_speech_samples.py",
)


@pytest.fixture
def empty_models_dir(tmp_path, monkeypatch):
    """Point the loader at an empty directory to exercise graceful degradation."""
    from voiceshield.config import settings as live_settings

    models_dir = tmp_path / "models"
    models_dir.mkdir()
    monkeypatch.setattr(live_settings, "models_dir", str(models_dir))
    monkeypatch.setattr(live_settings, "models_manifest", str(models_dir / "manifest.json"))
    return models_dir


@pytest.fixture
def app():
    """Create test FastAPI application instance."""
    return create_app()


@pytest.fixture
def client(app):
    """Create test HTTP client."""
    return TestClient(app)


@pytest.fixture
def test_settings():
    """Create custom settings for testing."""
    return Settings(
        env="testing",
        debug=True,
        log_level="DEBUG",
    )


# --- audio fixtures -----------------------------------------------------------


@pytest.fixture
def wav_fixture(tmp_path) -> Path:
    """Deterministic 2.0 s WAV: silence / voiced / silence / voiced."""
    return write_wav(tmp_path / "fixture.wav", standard_fixture_samples())


@pytest.fixture
def silent_wav_fixture(tmp_path) -> Path:
    """1.0 s of digital silence."""
    return write_wav(tmp_path / "silence.wav", silence(1.0))


@pytest.fixture
def empty_wav_fixture(tmp_path) -> Path:
    """A structurally valid WAV containing zero audio frames."""
    return write_wav(tmp_path / "empty.wav", np.zeros(0, dtype=np.float64))


@pytest.fixture
def stereo_wav_fixture(tmp_path) -> Path:
    """0.5 s stereo WAV at 44.1 kHz: exercises downmix and resampling."""
    left = tone(0.5, 440.0, rate=44100)
    right = tone(0.5, 660.0, rate=44100)
    interleaved = np.empty(left.size * 2, dtype=np.float64)
    interleaved[0::2] = left
    interleaved[1::2] = right
    return write_wav(tmp_path / "stereo.wav", interleaved, rate=44100, channels=2)


@pytest.fixture
def corrupt_wav_fixture(tmp_path) -> Path:
    """A file with a .wav name whose bytes are not a WAV container."""
    path = tmp_path / "corrupt.wav"
    path.write_bytes(b"NOT-A-RIFF-HEADER" + b"\x00\x01\x02\x03" * 64)
    return path


@pytest.fixture
def eight_bit_wav_fixture(tmp_path) -> Path:
    """A valid WAV in an unsupported sample width (8-bit)."""
    path = tmp_path / "eight_bit.wav"
    samples = (np.clip(tone(0.2), -1.0, 1.0) * 127 + 128).astype(np.uint8)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(1)
        wav.setframerate(FIXTURE_RATE)
        wav.writeframes(samples.tobytes())
    return path
