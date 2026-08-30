"""Deterministic synthetic audio helpers shared by the ingestion tests.

No audio binaries are committed to the repo: every fixture is generated from a
fixed seed at test time, so runs are reproducible on any machine.

These are synthetic signals, not speech recordings, and they carry no ground
truth about authenticity.
"""

import wave
from pathlib import Path

import numpy as np

FIXTURE_RATE = 16000
#: Fixed seed so every generated fixture is byte-identical between runs.
FIXTURE_SEED = 20260828

#: Segment layout of the standard `wav_fixture`, as (start_s, end_s, is_speech).
WAV_FIXTURE_SEGMENTS = [
    (0.00, 0.25, False),
    (0.25, 1.00, True),
    (1.00, 1.50, False),
    (1.50, 2.00, True),
]
WAV_FIXTURE_DURATION_S = 2.0


def tone(duration_s: float, freq_hz: float = 440.0, rate: int = FIXTURE_RATE,
         amplitude: float = 0.4) -> np.ndarray:
    """A pure sine tone."""
    t = np.arange(int(round(duration_s * rate)), dtype=np.float64) / rate
    return amplitude * np.sin(2 * np.pi * freq_hz * t)


def voiced(duration_s: float, f0: float = 130.0, rate: int = FIXTURE_RATE,
           amplitude: float = 0.35) -> np.ndarray:
    """A crude voiced-speech surrogate: f0 plus a few harmonics."""
    t = np.arange(int(round(duration_s * rate)), dtype=np.float64) / rate
    signal = np.zeros_like(t)
    for harmonic, weight in enumerate([1.0, 0.5, 0.3, 0.15], start=1):
        signal += weight * np.sin(2 * np.pi * f0 * harmonic * t)
    peak = np.max(np.abs(signal)) or 1.0
    return amplitude * signal / peak


def silence(duration_s: float, rate: int = FIXTURE_RATE) -> np.ndarray:
    return np.zeros(int(round(duration_s * rate)), dtype=np.float64)


def standard_fixture_samples() -> np.ndarray:
    """The 2.0 s silence/voiced/silence/voiced pattern used across the tests."""
    return np.concatenate([
        silence(0.25),
        voiced(0.75, f0=130.0),
        silence(0.50),
        voiced(0.50, f0=210.0),
    ])


def pcm_bytes(samples: np.ndarray) -> bytes:
    """Encode float samples as little-endian 16-bit PCM."""
    return (np.clip(samples, -1.0, 1.0) * 32767.0).astype("<i2").tobytes()


def write_wav(path: Path, samples: np.ndarray, rate: int = FIXTURE_RATE,
              channels: int = 1, sample_width: int = 2) -> Path:
    """Write mono/interleaved-stereo PCM to a WAV file and return the path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if sample_width != 2:
        raise ValueError(f"Unsupported sample width for fixtures: {sample_width}")
    pcm = (np.clip(samples, -1.0, 1.0) * 32767.0).astype("<i2")
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(sample_width)
        wav.setframerate(rate)
        wav.writeframes(pcm.tobytes())
    return path
