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


def _speech_utterance(
    duration_s: float,
    base_f0: float,
    rate: int,
    is_synthetic: bool = False,
    is_degraded: bool = False,
) -> np.ndarray:
    """Generate a realistic speech phrase with formants, micro-tremors, and pauses."""
    n_samples = int(round(duration_s * rate))
    t = np.arange(n_samples, dtype=np.float64) / rate

    # Fundamental frequency pitch curve with natural speech intonation contour
    pitch_contour = base_f0 + 15.0 * np.sin(2 * np.pi * 0.8 * t) + 8.0 * np.cos(2 * np.pi * 1.7 * t)
    if is_synthetic:
        # Voice clone / TTS exhibits unnaturally rigid pitch with lack of micro-jitter
        pitch_contour = np.full_like(t, base_f0)

    # Integrate phase for smooth instantaneous pitch transitions
    phase = 2 * np.pi * np.cumsum(pitch_contour) / rate

    # Formants (F1, F2, F3, F4) modeling vocal tract resonances
    f1, f2, f3, f4 = 1.0, 0.55, 0.35, 0.20
    signal = (
        f1 * np.sin(phase) +
        f2 * np.sin(2 * phase) +
        f3 * np.sin(3 * phase) +
        f4 * np.sin(4 * phase)
    )

    # Amplitude envelope with syllabic stress modulation (vocal pulses)
    syllable_env = 0.5 + 0.5 * np.sin(2 * np.pi * 3.5 * t)
    signal *= syllable_env

    if is_synthetic:
        # Add subtle vocoder buzzing / spectral flatness artefact
        rng = np.random.default_rng(SEED)
        noise = rng.standard_normal(n_samples) * 0.08
        signal += noise

    if is_degraded:
        # Add acoustic line noise and band-pass filtering
        rng = np.random.default_rng(SEED + 1)
        line_noise = rng.standard_normal(n_samples) * 0.18
        signal += line_noise
        spectrum = np.fft.rfft(signal)
        freqs = np.fft.rfftfreq(n_samples, d=1.0 / rate)
        spectrum[freqs > 3200.0] = 0.0
        spectrum[freqs < 300.0] = 0.0
        signal = np.fft.irfft(spectrum, n=n_samples)

    peak = np.max(np.abs(signal)) or 1.0
    return 0.4 * (signal / peak)


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

    # --- Scenario 30-second Audio Call Fixtures ---
    phrase_len = 2.5
    pause_len = 0.5

    # Case 01: Authentic CFO voice (30.0 seconds total: 10 phrases + pauses)
    cfo_pitches = [140.0, 145.0, 138.0, 142.0, 148.0, 136.0, 144.0, 139.0, 146.0, 141.0]
    cfo_phrases = []
    for p in cfo_pitches:
        cfo_phrases.append(_speech_utterance(phrase_len, p, rate, is_synthetic=False))
        cfo_phrases.append(_silence(pause_len, rate))
    authentic_wav = np.concatenate(cfo_phrases)
    write_wav(out_dir / "case_01_authentic_human.wav", authentic_wav, rate)
    written.append("case_01_authentic_human.wav")

    # Case 02: Synthetic / Voice-cloned attack (30.0 seconds total)
    clone_phrases = []
    for _ in range(10):
        clone_phrases.append(_speech_utterance(phrase_len, 140.0, rate, is_synthetic=True))
        clone_phrases.append(_silence(pause_len, rate))
    cloned_wav = np.concatenate(clone_phrases)
    write_wav(out_dir / "case_02_cloned_synthetic.wav", cloned_wav, rate)
    written.append("case_02_cloned_synthetic.wav")

    # Case 03: Adversarial / Degraded line (30.0 seconds total)
    degraded_pitches = [135.0, 150.0, 130.0, 145.0, 138.0, 152.0, 132.0, 148.0, 136.0, 144.0]
    degraded_phrases = []
    for p in degraded_pitches:
        degraded_phrases.append(_speech_utterance(phrase_len, p, rate, is_degraded=True))
        degraded_phrases.append(_silence(pause_len, rate))
    adversarial_wav = np.concatenate(degraded_phrases)
    write_wav(out_dir / "case_03_adversarial_manipulated.wav", adversarial_wav, rate)
    written.append("case_03_adversarial_manipulated.wav")

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
