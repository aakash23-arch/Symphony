"""Generate deterministic demo WAV fixtures into demo/audio/.

These are synthetic signals for exercising the ingestion path end to end. They
are NOT speech samples and carry no ground-truth label of any kind: nothing
downstream may treat a fixture name as evidence of authenticity.

Usage:
    python scripts/make_demo_fixtures.py [--out demo/audio] [--rate 16000]
"""

import argparse
import struct
import sys
import wave
from pathlib import Path

import numpy as np

SAMPLE_RATE = 16000
#: Fixed seed so regenerated fixtures are byte-identical.
SEED = 20260828


def _tone(duration_s: float, freq_hz: float, rate: int, amplitude: float = 0.4) -> np.ndarray:
    t = np.arange(int(round(duration_s * rate)), dtype=np.float64) / rate
    return amplitude * np.sin(2 * np.pi * freq_hz * t)


def _silence(duration_s: float, rate: int) -> np.ndarray:
    return np.zeros(int(round(duration_s * rate)), dtype=np.float64)


def _voiced(duration_s: float, f0: float, rate: int, amplitude: float = 0.35) -> np.ndarray:
    """A crude voiced-speech surrogate: f0 plus a few harmonics."""
    t = np.arange(int(round(duration_s * rate)), dtype=np.float64) / rate
    signal = np.zeros_like(t)
    for harmonic, weight in enumerate([1.0, 0.5, 0.3, 0.15], start=1):
        signal += weight * np.sin(2 * np.pi * f0 * harmonic * t)
    peak = np.max(np.abs(signal)) or 1.0
    return amplitude * signal / peak


def write_wav(path: Path, samples: np.ndarray, rate: int) -> None:
    """Write mono 16-bit PCM."""
    path.parent.mkdir(parents=True, exist_ok=True)
    clipped = np.clip(samples, -1.0, 1.0)
    pcm = (clipped * 32767.0).astype("<i2")
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(pcm.tobytes())


def build_fixtures(out_dir: Path, rate: int) -> list:
    rng = np.random.default_rng(SEED)
    written = []

    # A clean alternating speech/silence pattern: exercises VAD boundaries.
    clean = np.concatenate([
        _silence(0.25, rate),
        _voiced(0.75, 130.0, rate),
        _silence(0.50, rate),
        _voiced(0.75, 210.0, rate),
        _silence(0.25, rate),
    ])
    write_wav(out_dir / "clean_speechlike.wav", clean, rate)
    written.append("clean_speechlike.wav")

    # Same signal degraded with noise: q_t must be materially lower.
    noisy = clean + 0.12 * rng.standard_normal(clean.size)
    write_wav(out_dir / "noisy_speechlike.wav", noisy, rate)
    written.append("noisy_speechlike.wav")

    # Band-limited, as a narrowband telephone channel would be.
    spectrum = np.fft.rfft(clean)
    freqs = np.fft.rfftfreq(clean.size, d=1.0 / rate)
    spectrum[freqs > 3400.0] = 0.0
    narrowband = np.fft.irfft(spectrum, n=clean.size)
    write_wav(out_dir / "narrowband_speechlike.wav", narrowband, rate)
    written.append("narrowband_speechlike.wav")

    # Pure silence: must yield zero speech frames, never a fabricated one.
    write_wav(out_dir / "silence.wav", _silence(1.0, rate), rate)
    written.append("silence.wav")

    # A steady tone, useful as a known-content golden vector.
    write_wav(out_dir / "tone_440.wav", _tone(1.0, 440.0, rate), rate)
    written.append("tone_440.wav")

    return written


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="demo/audio", help="Output directory")
    parser.add_argument("--rate", type=int, default=SAMPLE_RATE, help="Sample rate in Hz")
    args = parser.parse_args(argv)

    out_dir = Path(args.out)
    written = build_fixtures(out_dir, args.rate)
    print(f"Wrote {len(written)} fixtures to {out_dir.resolve()}:")
    for name in written:
        print(f"  - {name}")
    print("\nThese are synthetic signals, not labelled speech. They carry no "
          "ground truth about authenticity.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
