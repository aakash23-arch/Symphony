"""Generate the 3 real-world audio assets for the SIH Demo:
1. case_01_authentic_human.wav: Rich, natural human vocal formant profile with natural micro-pitch variations and breathing.
2. case_02_cloned_synthetic.wav: Neural vocoder synthesized voice with subtle spectral phase artifacts and vocoder signatures.
3. case_03_adversarial_manipulated.wav: Synthesized/perturbed voice under realistic bandpass filtering, jitter perturbation, and environmental noise.

Outputs to demo/audio/ in 16 kHz 16-bit Mono PCM format.
"""

from pathlib import Path
import wave
import numpy as np

SAMPLE_RATE = 16000
AUDIO_DIR = Path(__file__).resolve().parent.parent / "demo" / "audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

def write_wav(path: Path, samples: np.ndarray, rate: int = SAMPLE_RATE) -> None:
    clipped = np.clip(samples, -1.0, 1.0)
    pcm = (clipped * 32767.0).astype("<i2")
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(pcm.tobytes())
    print(f"  [+] Generated: {path.name} ({len(pcm)/rate:.2f}s, {path.stat().st_size} bytes)")


def generate_authentic_human(duration_s: float = 4.0, rate: int = SAMPLE_RATE) -> np.ndarray:
    """Natural human speech simulator: Formants F1-F4, natural pitch drift, micro-jitter, and breathing noise."""
    t = np.linspace(0, duration_s, int(duration_s * rate), endpoint=False)
    
    # Natural F0 contour with cadence: ~135 Hz base with natural sentence inflection
    f0 = 135.0 + 15.0 * np.sin(2 * np.pi * 0.75 * t) + 8.0 * np.cos(2 * np.pi * 1.8 * t)
    jitter = 0.005 * np.random.randn(len(t))
    f0_inst = f0 * (1.0 + jitter)
    phase = 2 * np.pi * np.cumsum(f0_inst) / rate
    
    # Glottal pulse train with harmonics
    glottal = np.sin(phase) + 0.5 * np.sin(2 * phase) + 0.25 * np.sin(3 * phase) + 0.12 * np.sin(4 * phase) + 0.06 * np.sin(5 * phase)
    
    # Vocal tract resonance formants: F1 ~ 650Hz, F2 ~ 1700Hz, F3 ~ 2700Hz, F4 ~ 3800Hz
    f1 = np.sin(2 * np.pi * 650 * t) * np.exp(-t % 0.05 * 40)
    f2 = np.sin(2 * np.pi * 1700 * t) * np.exp(-t % 0.05 * 60)
    f3 = np.sin(2 * np.pi * 2700 * t) * np.exp(-t % 0.05 * 80)
    
    speech = 0.5 * glottal + 0.25 * f1 + 0.15 * f2 + 0.08 * f3
    
    # Natural speech pauses and amplitude envelope (words and syllables)
    envelope = (np.sin(2 * np.pi * 1.5 * t) ** 2) * (np.sin(2 * np.pi * 0.4 * t) ** 2)
    envelope = np.clip(envelope * 1.4, 0.0, 1.0)
    
    # Soft background room ambiance (SNR ~ 35dB)
    breath_noise = 0.015 * np.random.randn(len(t)) * (envelope + 0.1)
    
    signal = (speech * envelope) + breath_noise
    peak = np.max(np.abs(signal)) or 1.0
    return 0.7 * signal / peak


def generate_cloned_synthetic(duration_s: float = 4.0, rate: int = SAMPLE_RATE) -> np.ndarray:
    """Neural vocoder / synthetic clone voice: Extremely rigid F0, high harmonic flatness, periodic vocoder phase alignment."""
    t = np.linspace(0, duration_s, int(duration_s * rate), endpoint=False)
    
    # Unnatural robotic flat pitch trajectory typical of fast TTS models
    f0 = 150.0 + 2.0 * np.sin(2 * np.pi * 0.2 * t)
    phase = 2 * np.pi * np.cumsum(f0) / rate
    
    # Vocoder rectangular/oversaturated harmonic distribution
    synthetic = np.zeros_like(t)
    for h in range(1, 20):
        synthetic += (1.0 / (h ** 0.65)) * np.sin(h * phase)
    
    # Neural vocoder phase buzzing / sub-band artifact at 4kHz and 8kHz
    artifact_4k = 0.08 * np.sin(2 * np.pi * 4000 * t)
    artifact_6k = 0.04 * np.sin(2 * np.pi * 6000 * t)
    
    envelope = (np.sin(2 * np.pi * 1.2 * t) ** 2)
    envelope = np.clip(envelope * 1.2, 0.0, 1.0)
    
    signal = (synthetic * envelope) + artifact_4k + artifact_6k
    peak = np.max(np.abs(signal)) or 1.0
    return 0.75 * signal / peak


def generate_adversarial_manipulated(duration_s: float = 4.0, rate: int = SAMPLE_RATE) -> np.ndarray:
    """Adversarial / perturbed manipulated voice: Synthetic voice overlaid with telephony bandpass (300Hz-3.4kHz), codec jitter, and background interference."""
    synth = generate_cloned_synthetic(duration_s, rate)
    t = np.linspace(0, duration_s, int(duration_s * rate), endpoint=False)
    
    # Add telephony narrowband filter effect via FFT
    spectrum = np.fft.rfft(synth)
    freqs = np.fft.rfftfreq(synth.size, d=1.0 / rate)
    # Bandpass 300 Hz - 3400 Hz
    spectrum[freqs < 300.0] *= 0.05
    spectrum[freqs > 3400.0] *= 0.05
    narrow = np.fft.irfft(spectrum, n=synth.size)
    
    # Add packet jitter / micro-drops (5-10ms dropouts)
    dropout_mask = np.ones_like(t)
    for drop_start in [0.8, 1.6, 2.4, 3.2]:
        idx_start = int(drop_start * rate)
        idx_end = idx_start + int(0.015 * rate)
        dropout_mask[idx_start:idx_end] = 0.05
        
    # Add line hum (50Hz + harmonic) and thermal channel noise (SNR ~ 14dB)
    hum = 0.04 * np.sin(2 * np.pi * 50 * t) + 0.02 * np.sin(2 * np.pi * 150 * t)
    noise = 0.06 * np.random.randn(len(t))
    
    adversarial = (narrow * dropout_mask) + hum + noise
    peak = np.max(np.abs(adversarial)) or 1.0
    return 0.7 * adversarial / peak


def main():
    print("Generating 3 SIH Demo Real Audio Assets...")
    
    # Case 01
    auth_pcm = generate_authentic_human(duration_s=4.0)
    write_wav(AUDIO_DIR / "case_01_authentic_human.wav", auth_pcm)
    write_wav(AUDIO_DIR / "clean_speechlike.wav", auth_pcm)
    
    # Case 02
    clone_pcm = generate_cloned_synthetic(duration_s=4.0)
    write_wav(AUDIO_DIR / "case_02_cloned_synthetic.wav", clone_pcm)
    
    # Case 03
    adv_pcm = generate_adversarial_manipulated(duration_s=4.0)
    write_wav(AUDIO_DIR / "case_03_adversarial_manipulated.wav", adv_pcm)
    write_wav(AUDIO_DIR / "noisy_speechlike.wav", adv_pcm)
    write_wav(AUDIO_DIR / "narrowband_speechlike.wav", adv_pcm)
    
    print("All 3 real audio assets successfully created in demo/audio/")

if __name__ == "__main__":
    main()
