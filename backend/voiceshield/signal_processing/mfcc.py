import numpy as np
import librosa
from typing import Tuple
from .config import MFCCConfig, SpectrogramConfig
from .spectrogram import compute_log_mel_spectrogram

def compute_mfcc(pcm: np.ndarray, spec_config: SpectrogramConfig, mfcc_config: MFCCConfig, t_start: float = 0.0) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Computes MFCC, delta, and delta-delta features.
    Returns:
        mfcc: np.ndarray of shape (n_mfcc, t)
        delta: np.ndarray of shape (n_mfcc, t) or empty
        delta_delta: np.ndarray of shape (n_mfcc, t) or empty
        timestamps: np.ndarray of shape (t,)
    """
    log_mel, _, timestamps = compute_log_mel_spectrogram(pcm, spec_config, t_start)
    
    if log_mel.size == 0:
        return np.array([[]]), np.array([[]]), np.array([[]]), np.array([])
        
    mfcc = librosa.feature.mfcc(
        S=log_mel, 
        n_mfcc=mfcc_config.n_mfcc,
        dct_type=mfcc_config.dct_type,
        lifter=mfcc_config.lifter
    )
    
    delta = np.array([[]])
    delta_delta = np.array([[]])
    
    if mfcc_config.include_delta and mfcc.shape[1] > 2:
        delta = librosa.feature.delta(mfcc)
        
    if mfcc_config.include_delta_delta and mfcc.shape[1] > 2:
        delta_delta = librosa.feature.delta(mfcc, order=2)
        
    return mfcc, delta, delta_delta, timestamps
