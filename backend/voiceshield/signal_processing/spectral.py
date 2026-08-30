import numpy as np
import librosa
from typing import Dict, Any
from .config import SpectrogramConfig
from .spectrogram import compute_spectrogram

def compute_spectral_features(pcm: np.ndarray, config: SpectrogramConfig, sample_rate: int) -> Dict[str, np.ndarray]:
    """
    Computes spectral statistics: centroid, bandwidth, flatness, rolloff, flux, contrast.
    """
    spec, _ = compute_spectrogram(pcm, config)
    
    if spec.size == 0:
        empty = np.array([])
        return {
            "centroid": empty,
            "bandwidth": empty,
            "flatness": empty,
            "rolloff": empty,
            "flux": empty,
            "contrast": empty
        }

    # librosa functions typically take S (magnitude spectrogram)
    centroid = librosa.feature.spectral_centroid(S=spec, sr=sample_rate, n_fft=config.n_fft, hop_length=config.hop_length)[0]
    bandwidth = librosa.feature.spectral_bandwidth(S=spec, sr=sample_rate, n_fft=config.n_fft, hop_length=config.hop_length)[0]
    flatness = librosa.feature.spectral_flatness(S=spec, power=config.power)[0]
    rolloff = librosa.feature.spectral_rolloff(S=spec, sr=sample_rate, n_fft=config.n_fft, hop_length=config.hop_length, roll_percent=0.85)[0]
    
    # Spectral Flux (frame-to-frame difference of magnitude spectrum)
    # prepend the first frame to keep shape consistent
    spec_padded = np.pad(spec, ((0, 0), (1, 0)), mode='edge')
    flux = np.sum(np.maximum(0, spec - spec_padded[:, :-1])**2, axis=0)
    
    # Spectral Contrast
    contrast = librosa.feature.spectral_contrast(S=spec, sr=sample_rate, n_fft=config.n_fft, hop_length=config.hop_length)
    # average contrast across bands to get a 1D contour, or we can just keep the mean across bands per frame
    contrast_mean = np.mean(contrast, axis=0)
    
    return {
        "centroid": centroid,
        "bandwidth": bandwidth,
        "flatness": flatness,
        "rolloff": rolloff,
        "flux": flux,
        "contrast": contrast_mean
    }
