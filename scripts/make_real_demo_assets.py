"""Deterministic preparation and validation of canonical demo audio assets.

Prepares the 3 canonical demo cases:
1. case_01_authentic_human.wav: Genuine human speech (LibriSpeech corpus, CC-BY 4.0).
2. case_02_cloned_synthetic.wav: Real synthetic text-to-speech voice with linguistic phrasing (pyttsx3/SAPI5).
3. case_03_adversarial_manipulated.wav: Degraded telephone channel (bandpass 300Hz-3.4kHz, packet dropouts, channel noise SNR < 15dB).

All assets are formatted in 16 kHz 16-bit Mono PCM WAV without clipping.
Includes full validation verifying speech activity, SNR, and model response.
"""

from pathlib import Path
import os
import wave
import librosa
import numpy as np
import soundfile as sf

SAMPLE_RATE = 16000
AUDIO_DIR = Path(__file__).resolve().parent.parent / "demo" / "audio"
SOURCE_DIR = AUDIO_DIR / "sources"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)
SOURCE_DIR.mkdir(parents=True, exist_ok=True)


def write_wav(path: Path, samples: np.ndarray, rate: int = SAMPLE_RATE) -> None:
    """Write float samples to 16-bit Mono PCM WAV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    clipped = np.clip(samples, -1.0, 1.0)
    pcm = (clipped * 32767.0).astype("<i2")
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(pcm.tobytes())
    print(f"  [+] Generated: {path.name} ({len(pcm)/rate:.2f}s, {path.stat().st_size} bytes)")


def get_genuine_human_speech(duration_s: float = 2.8, rate: int = SAMPLE_RATE) -> np.ndarray:
    """Extract real human speech from local repository source or cached LibriSpeech."""
    source_path = SOURCE_DIR / "genuine_human_librispeech.wav"
    if source_path.exists():
        y, sr = librosa.load(str(source_path), sr=rate, mono=True)
    else:
        cached = librosa.ex("libri1")
        y, sr = librosa.load(cached, sr=rate, mono=True)
        sf.write(str(source_path), y, rate, subtype="PCM_16")

    # Take a 2.8s slice of clean active speech (skip initial 0.5s silence)
    start_sample = int(0.5 * rate)
    length = int(duration_s * rate)
    chunk = y[start_sample : start_sample + length]

    # Peak normalize to -1 dBFS (0.90 amplitude)
    peak = np.max(np.abs(chunk)) or 1.0
    normalized = (chunk / peak) * 0.90
    return normalized.astype(np.float32)


def get_cloned_synthetic_speech(duration_s: float = 2.8, rate: int = SAMPLE_RATE) -> np.ndarray:
    """Generate real synthetic speech containing linguistic content using local pyttsx3 TTS."""
    import pyttsx3

    engine = pyttsx3.init()
    temp_path = AUDIO_DIR / "temp_synth_gen.wav"

    # Financial disbursement context spoken by synthetic voice
    text = (
        "This is an urgent financial confirmation regarding an immediate wire transfer "
        "to a new offshore beneficiary account. Please authorize payment immediately."
    )
    engine.save_to_file(text, str(temp_path))
    engine.runAndWait()

    y, sr = librosa.load(str(temp_path), sr=rate, mono=True)
    if temp_path.exists():
        os.remove(temp_path)

    length = int(duration_s * rate)
    chunk = y[:length] if len(y) >= length else np.pad(y, (0, length - len(y)))

    # Peak normalize to -1 dBFS
    peak = np.max(np.abs(chunk)) or 1.0
    normalized = (chunk / peak) * 0.90
    return normalized.astype(np.float32)


def get_adversarial_manipulated_speech(
    clean_speech: np.ndarray, duration_s: float = 2.8, rate: int = SAMPLE_RATE
) -> np.ndarray:
    """Apply telephony bandpass filtering, packet jitter micro-drops, and channel noise (SNR < 15 dB)."""
    t = np.linspace(0, duration_s, len(clean_speech), endpoint=False)

    # Telephony narrowband filter (300 Hz - 3400 Hz) via FFT
    spectrum = np.fft.rfft(clean_speech)
    freqs = np.fft.rfftfreq(len(clean_speech), d=1.0 / rate)
    spectrum[freqs < 300.0] *= 0.05
    spectrum[freqs > 3400.0] *= 0.05
    narrow = np.fft.irfft(spectrum, n=len(clean_speech))

    # Packet jitter dropouts (15-20ms packet losses)
    dropout_mask = np.ones_like(t)
    for drop_start in [0.5, 1.2, 2.0]:
        idx_start = int(drop_start * rate)
        idx_end = idx_start + int(0.02 * rate)
        dropout_mask[idx_start:idx_end] = 0.05

    # Line hum (50Hz harmonic) + channel noise tuned for ~9-11 dB SNR
    hum = 0.03 * np.sin(2 * np.pi * 50 * t)
    noise = 0.07 * np.random.RandomState(20260828).randn(len(t))

    adversarial = (narrow * dropout_mask) + hum + noise
    peak = np.max(np.abs(adversarial)) or 1.0
    normalized = (adversarial / peak) * 0.90
    return normalized.astype(np.float32)


def validate_demo_assets() -> bool:
    """Validate all 3 canonical demo assets against requirements.

    Case 01: exists, decodes, 16kHz, voiced ratio > 0.3, active speech > 1.5s, SNR > 20 dB
    Case 02: exists, decodes, 16kHz, voiced ratio > 0.3, active speech > 1.5s, p_fake > 0.80
    Case 03: exists, decodes, degraded SNR < 15 dB
    """
    from voiceshield.pipeline.preprocessor import AudioPreprocessor
    from voiceshield.models.adapters.hf_wav2vec2_spoof import Wav2Vec2SpoofAdapter

    preprocessor = AudioPreprocessor()
    adapter = Wav2Vec2SpoofAdapter()
    adapter.load()

    print("\n--- Validating Canonical Demo Assets ---")
    all_ok = True

    # Case 01
    c1_path = AUDIO_DIR / "case_01_authentic_human.wav"
    assert c1_path.exists(), f"Missing Case 01: {c1_path}"
    raw1 = c1_path.read_bytes()
    pcm1, sr1 = preprocessor.decode_audio(raw1)
    pcm1 = preprocessor.downmix_to_mono(pcm1)
    pcm1 = preprocessor.resample(pcm1, sr1, 16000)
    snr1 = preprocessor.estimate_snr_db(pcm1, 16000)
    mask1, voiced_ratio1, active_dur1 = preprocessor.detect_voice_activity(pcm1, 16000)
    res1 = adapter.infer(pcm1, 16000) if adapter.is_loaded() else None
    p_fake1 = res1.p if res1 and res1.status.value == "OK" else 0.0

    print(f"Case 01: SNR={snr1:.1f}dB, voiced={voiced_ratio1:.2f}, active_speech={active_dur1:.2f}s, p_fake={p_fake1:.4f}")
    if snr1 < 20.0 or voiced_ratio1 < 0.3 or active_dur1 < 1.5 or p_fake1 > 0.20:
        print("  [FAIL] Case 01 validation criteria failed!")
        all_ok = False
    else:
        print("  [PASS] Case 01 is verified genuine human speech.")

    # Case 02
    c2_path = AUDIO_DIR / "case_02_cloned_synthetic.wav"
    assert c2_path.exists(), f"Missing Case 02: {c2_path}"
    raw2 = c2_path.read_bytes()
    pcm2, sr2 = preprocessor.decode_audio(raw2)
    pcm2 = preprocessor.downmix_to_mono(pcm2)
    pcm2 = preprocessor.resample(pcm2, sr2, 16000)
    snr2 = preprocessor.estimate_snr_db(pcm2, 16000)
    mask2, voiced_ratio2, active_dur2 = preprocessor.detect_voice_activity(pcm2, 16000)
    res2 = adapter.infer(pcm2, 16000) if adapter.is_loaded() else None
    p_fake2 = res2.p if res2 and res2.status.value == "OK" else 0.0

    print(f"Case 02: SNR={snr2:.1f}dB, voiced={voiced_ratio2:.2f}, active_speech={active_dur2:.2f}s, p_fake={p_fake2:.4f}")
    if voiced_ratio2 < 0.3 or active_dur2 < 1.5 or p_fake2 < 0.80:
        print("  [FAIL] Case 02 validation criteria failed!")
        all_ok = False
    else:
        print("  [PASS] Case 02 is verified synthetic speech.")

    # Case 03
    c3_path = AUDIO_DIR / "case_03_adversarial_manipulated.wav"
    assert c3_path.exists(), f"Missing Case 03: {c3_path}"
    raw3 = c3_path.read_bytes()
    pcm3, sr3 = preprocessor.decode_audio(raw3)
    pcm3 = preprocessor.downmix_to_mono(pcm3)
    pcm3 = preprocessor.resample(pcm3, sr3, 16000)
    snr3 = preprocessor.estimate_snr_db(pcm3, 16000)

    print(f"Case 03: SNR={snr3:.1f}dB (< 15 dB required)")
    if snr3 >= 15.0:
        print("  [FAIL] Case 03 SNR is too high for degraded channel test!")
        all_ok = False
    else:
        print("  [PASS] Case 03 has verified degraded channel characteristics.")

    return all_ok


def main():
    print("Generating 3 SIH Demo Canonical Audio Assets from Real Speech Sources...")

    # Case 01: Authentic Human Speech
    auth_pcm = get_genuine_human_speech(duration_s=2.8)
    write_wav(AUDIO_DIR / "case_01_authentic_human.wav", auth_pcm)
    write_wav(AUDIO_DIR / "clean_speechlike.wav", auth_pcm)

    # Case 02: Real Synthetic TTS Speech
    clone_pcm = get_cloned_synthetic_speech(duration_s=2.8)
    write_wav(AUDIO_DIR / "case_02_cloned_synthetic.wav", clone_pcm)

    # Case 03: Adversarial Manipulated / Degraded Channel Audio
    adv_pcm = get_adversarial_manipulated_speech(auth_pcm, duration_s=2.8)
    write_wav(AUDIO_DIR / "case_03_adversarial_manipulated.wav", adv_pcm)
    write_wav(AUDIO_DIR / "noisy_speechlike.wav", adv_pcm)
    write_wav(AUDIO_DIR / "narrowband_speechlike.wav", adv_pcm)

    # Validate
    ok = validate_demo_assets()
    if not ok:
        raise RuntimeError("Demo assets failed validation!")
    print("\nAll 3 canonical demo assets successfully generated and verified in demo/audio/")


if __name__ == "__main__":
    main()
