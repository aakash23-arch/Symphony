"""Digital signal processing interfaces (C-15, C-16)."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List
import numpy as np
import librosa

class SignalProcessor(ABC):
    """Abstract interface for DSP operations (filtering, normalization, STFT)."""

    @abstractmethod
    def compute_stft(self, audio_pcm: np.ndarray, n_fft: int = 512, hop_length: int = 160) -> np.ndarray:
        """Compute short-time Fourier transform."""
        pass

    @abstractmethod
    def estimate_snr(self, audio_pcm: np.ndarray) -> float:
        """Estimate signal-to-noise ratio in dB."""
        pass

class StandardSignalProcessor(SignalProcessor):
    """Concrete implementation of DSP operations."""

    def compute_stft(self, audio_pcm: np.ndarray, n_fft: int = 512, hop_length: int = 160) -> np.ndarray:
        if len(audio_pcm) == 0:
            return np.array([[]])
        return librosa.stft(y=audio_pcm, n_fft=n_fft, hop_length=hop_length, center=True)

    def estimate_snr(self, audio_pcm: np.ndarray) -> float:
        """
        Estimates SNR using a WADA-SNR like approach or simpler energy percentile.
        Here we use the ratio of the 90th percentile energy to the 10th percentile energy.
        """
        if len(audio_pcm) == 0:
            return 0.0
            
        # compute RMS energy across small windows
        rms = librosa.feature.rms(y=audio_pcm, frame_length=512, hop_length=160)[0]
        if len(rms) < 2:
            return 0.0
            
        rms = np.sort(rms)
        noise_floor = np.mean(rms[:max(1, len(rms)//10)])
        signal_peak = np.mean(rms[int(len(rms)*0.9):])
        
        if noise_floor < 1e-10:
            return 80.0 # max db limit
            
        snr = 20 * np.log10(signal_peak / noise_floor)
        return float(max(0.0, min(snr, 80.0)))
