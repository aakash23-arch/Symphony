import numpy as np
import librosa
from typing import Dict, Any, Tuple
from .config import ProsodyConfig

def compute_pause_statistics(db_contour: np.ndarray, hop_duration_s: float, config: ProsodyConfig) -> Dict[str, float]:
    """
    Computes statistics on pauses based on the dB contour.
    A pause is a contiguous segment below config.pause_threshold_db longer than config.min_pause_duration_ms.
    """
    if len(db_contour) == 0:
        return {
            "pause_count": 0.0,
            "total_pause_duration_s": 0.0,
            "pause_percentage": 0.0,
            "mean_pause_duration_s": 0.0
        }
        
    is_pause_frame = db_contour < config.pause_threshold_db
    
    # Find contiguous pause segments
    pause_segments = []
    current_pause_len = 0
    
    for p in is_pause_frame:
        if p:
            current_pause_len += 1
        else:
            if current_pause_len > 0:
                duration_ms = current_pause_len * hop_duration_s * 1000
                if duration_ms >= config.min_pause_duration_ms:
                    pause_segments.append(current_pause_len)
                current_pause_len = 0
                
    if current_pause_len > 0:
        duration_ms = current_pause_len * hop_duration_s * 1000
        if duration_ms >= config.min_pause_duration_ms:
            pause_segments.append(current_pause_len)
            
    total_frames = len(db_contour)
    total_duration_s = total_frames * hop_duration_s
    
    if not pause_segments:
        return {
            "pause_count": 0.0,
            "total_pause_duration_s": 0.0,
            "pause_percentage": 0.0,
            "mean_pause_duration_s": 0.0
        }
        
    pause_count = len(pause_segments)
    total_pause_frames = sum(pause_segments)
    total_pause_duration_s = total_pause_frames * hop_duration_s
    
    return {
        "pause_count": float(pause_count),
        "total_pause_duration_s": float(total_pause_duration_s),
        "pause_percentage": float((total_pause_duration_s / total_duration_s) * 100.0) if total_duration_s > 0 else 0.0,
        "mean_pause_duration_s": float(total_pause_duration_s / pause_count)
    }

def compute_speaking_rate(rms_contour: np.ndarray, hop_duration_s: float, config: ProsodyConfig) -> float:
    """
    Estimates speaking rate in syllables per second using an amplitude envelope peak picking approach.
    """
    if len(rms_contour) < 3:
        return 0.0
        
    # Smooth the RMS contour to get a rough syllabic envelope
    # Window size approx 50-100ms
    win_len = max(3, int(0.05 / hop_duration_s))
    if win_len % 2 == 0:
        win_len += 1
    
    import scipy.signal
    try:
        smoothed_rms = scipy.signal.savgol_filter(rms_contour, win_len, 2)
    except Exception:
        smoothed_rms = rms_contour
        
    # Find peaks
    peaks, _ = scipy.signal.find_peaks(smoothed_rms, distance=max(1, int(0.1 / hop_duration_s)))
    
    num_syllables = len(peaks)
    total_duration_s = len(rms_contour) * hop_duration_s
    
    if total_duration_s == 0:
        return 0.0
        
    return float(num_syllables / total_duration_s)

def compute_shimmer(pcm: np.ndarray, f0: np.ndarray, voiced_flag: np.ndarray, sample_rate: int, hop_length: int) -> float:
    """
    Computes shimmer (local amplitude perturbation).
    Uses RMS energy of voiced frames.
    """
    if len(pcm) == 0 or not np.any(voiced_flag):
        return 0.0
        
    rms = librosa.feature.rms(y=pcm, hop_length=hop_length, center=True)[0]
    # align rms with f0 (should be same length if both used center=True and same hop_length)
    min_len = min(len(rms), len(voiced_flag))
    voiced_rms = rms[:min_len][voiced_flag[:min_len]]
    
    if len(voiced_rms) < 2:
        return 0.0
        
    diffs = np.abs(np.diff(voiced_rms))
    mean_rms = np.mean(voiced_rms)
    
    if mean_rms == 0.0:
        return 0.0
        
    shimmer = np.mean(diffs) / mean_rms
    return float(shimmer)
