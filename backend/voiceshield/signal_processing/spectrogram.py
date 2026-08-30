import numpy as np
import librosa
from typing import Tuple
from .config import SpectrogramConfig
from .temporal import compute_frame_timestamps

def compute_stft(pcm: np.ndarray, config: SpectrogramConfig, t_start: float = 0.0) -> Tuple[np.ndarray, np.ndarray]:
    """
    Computes the Short-Time Fourier Transform (STFT) and corresponding timestamps.
    Returns:
        complex_stft: np.ndarray of shape (1 + n_fft/2, t)
        timestamps: np.ndarray of shape (t,)
    """
    if len(pcm) == 0:
        return np.array([[]]), np.array([])
        
    stft = librosa.stft(
        y=pcm,
        n_fft=config.n_fft,
        hop_length=config.hop_length,
        win_length=config.win_length,
        window=config.window,
        center=True
    )
    
    num_frames = stft.shape[1]
    timestamps = compute_frame_timestamps(num_frames, config.hop_length, config.sample_rate, t_start)
    return stft, timestamps

def compute_spectrogram(pcm: np.ndarray, config: SpectrogramConfig, t_start: float = 0.0) -> Tuple[np.ndarray, np.ndarray]:
    """
    Computes the magnitude or power spectrogram and corresponding timestamps.
    Returns:
        spec: np.ndarray of shape (1 + n_fft/2, t)
        timestamps: np.ndarray of shape (t,)
    """
    stft, timestamps = compute_stft(pcm, config, t_start)
    
    if stft.size == 0:
        return np.array([[]]), np.array([])
        
    mag_spec = np.abs(stft)
    if config.power != 1.0:
        mag_spec = mag_spec ** config.power
        
    return mag_spec, timestamps

def compute_log_mel_spectrogram(pcm: np.ndarray, config: SpectrogramConfig, t_start: float = 0.0) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Computes the Log-Mel Spectrogram and corresponding mel frequencies and timestamps.
    Returns:
        log_mel_spec: np.ndarray of shape (n_mels, t)
        mel_freqs: np.ndarray of shape (n_mels,)
        timestamps: np.ndarray of shape (t,)
    """
    spec, timestamps = compute_spectrogram(pcm, config, t_start)
    
    if spec.size == 0:
        return np.array([[]]), np.array([]), np.array([])
        
    # Mel filterbank
    mel_basis = librosa.filters.mel(
        sr=config.sample_rate,
        n_fft=config.n_fft,
        n_mels=config.n_mels,
        fmin=config.f_min,
        fmax=config.f_max
    )
    
    mel_freqs = librosa.mel_frequencies(n_mels=config.n_mels, fmin=config.f_min, fmax=config.f_max)
    
    mel_spec = np.dot(mel_basis, spec)
    # Log scaling
    log_mel_spec = librosa.power_to_db(mel_spec, ref=1.0, top_db=config.top_db, amin=config.eps)
    
    return log_mel_spec, mel_freqs, timestamps
