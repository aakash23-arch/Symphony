import argparse
import sys
import matplotlib.pyplot as plt
import numpy as np
import librosa
from pathlib import Path

# Add the project root to sys.path so we can import voiceshield
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from backend.voiceshield.signal_processing.config import SignalProcessingConfig
from backend.voiceshield.signal_processing.spectrogram import compute_log_mel_spectrogram
from backend.voiceshield.signal_processing.pitch import compute_pitch_pyin
from backend.voiceshield.signal_processing.temporal import compute_rms_energy

def main():
    parser = argparse.ArgumentParser(description="Render Spectrogram Diagnostic")
    parser.add_argument("--fixture", type=str, default="standard", help="Audio fixture name or path to wav file")
    parser.add_argument("--output", type=str, default="assets/spectrogram_diagnostic.png", help="Output image path")
    args = parser.parse_args()

    # Load audio
    if args.fixture == "standard":
        # Use a built-in librosa example if no file is provided
        audio_path = librosa.ex('trumpet')
    else:
        audio_path = args.fixture

    try:
        pcm, sr = librosa.load(audio_path, sr=16000)
    except Exception as e:
        print(f"Error loading audio: {e}")
        return

    config = SignalProcessingConfig()

    log_mel, mel_freqs, timestamps = compute_log_mel_spectrogram(pcm, config.spectrogram)
    f0, voiced_flag, _, _ = compute_pitch_pyin(pcm, config.pitch, sr, config.spectrogram.hop_length)
    rms, db_contour, _, _ = compute_rms_energy(pcm, config.spectrogram.win_length, config.spectrogram.hop_length, sr)

    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 8), sharex=True)

    # Plot Log-Mel Spectrogram
    img = librosa.display.specshow(log_mel, x_axis='time', y_axis='mel', sr=sr, hop_length=config.spectrogram.hop_length, fmax=8000, ax=ax1, cmap='magma')
    fig.colorbar(img, ax=ax1, format='%+2.0f dB')
    ax1.set(title='Log-Mel Spectrogram')

    # Plot Pitch
    ax2.plot(timestamps, f0, label='F0 (Hz)', color='blue')
    ax2.set(title='Pitch Contour', ylabel='Frequency (Hz)')
    ax2.legend()
    ax2.grid(True)

    # Plot Energy
    ax3.plot(timestamps, db_contour, label='RMS Energy (dB)', color='red')
    ax3.set(title='Energy Contour', ylabel='Magnitude (dB)')
    ax3.legend()
    ax3.grid(True)

    plt.tight_layout()
    
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_path)
    print(f"Diagnostic image saved to {out_path}")

if __name__ == "__main__":
    main()
