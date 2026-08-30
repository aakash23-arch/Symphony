import numpy as np
import librosa
from typing import Tuple, Dict, Any
from .config import PitchConfig
from .temporal import compute_frame_timestamps

def compute_pitch_pyin(pcm: np.ndarray, config: PitchConfig, sample_rate: int, hop_length: int, t_start: float = 0.0) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Computes fundamental frequency (F0) using the probabilistic YIN (pYIN) algorithm.
    Returns:
        f0: np.ndarray of shape (t,) (unvoiced frames are set to np.nan)
        voiced_flag: np.ndarray of shape (t,) boolean
        voiced_prob: np.ndarray of shape (t,) float
        timestamps: np.ndarray of shape (t,)
    """
    if len(pcm) == 0:
        return np.array([]), np.array([]), np.array([]), np.array([])
        
    f0, voiced_flag, voiced_prob = librosa.pyin(
        y=pcm,
        fmin=config.f0_min,
        fmax=config.f0_max,
        sr=sample_rate,
        hop_length=hop_length,
        center=True,
        pad_mode='constant'
    )
    
    # pyin returns nan for unvoiced frames, which is standard but we want to ensure it handles silence
    rms = librosa.feature.rms(y=pcm, hop_length=hop_length, center=True)[0]
    silence_mask = rms < config.silence_threshold
    voiced_flag = voiced_flag & (~silence_mask)
    f0[~voiced_flag] = 0.0 # Set unvoiced to 0.0 as requested
    
    timestamps = compute_frame_timestamps(len(f0), hop_length, sample_rate, t_start)
    return f0, voiced_flag, voiced_prob, timestamps

def compute_f0_statistics(f0: np.ndarray, voiced_flag: np.ndarray) -> Dict[str, float]:
    """
    Computes statistics on the F0 contour for voiced frames.
    """
    voiced_f0 = f0[voiced_flag]
    if len(voiced_f0) == 0:
        return {
            "mean": 0.0,
            "std": 0.0,
            "median": 0.0,
            "min": 0.0,
            "max": 0.0
        }
        
    return {
        "mean": float(np.mean(voiced_f0)),
        "std": float(np.std(voiced_f0)),
        "median": float(np.median(voiced_f0)),
        "min": float(np.min(voiced_f0)),
        "max": float(np.max(voiced_f0))
    }

def compute_jitter(f0: np.ndarray, voiced_flag: np.ndarray) -> float:
    """
    Computes local jitter (relative average perturbation) across voiced cycles.
    Jitter is the absolute difference between consecutive periods divided by the average period.
    """
    voiced_f0 = f0[voiced_flag]
    if len(voiced_f0) < 2:
        return 0.0
        
    periods = 1.0 / voiced_f0
    diffs = np.abs(np.diff(periods))
    mean_period = np.mean(periods)
    
    if mean_period == 0.0:
        return 0.0
        
    jitter = np.mean(diffs) / mean_period
    return float(jitter)
