import numpy as np
from typing import Tuple
import librosa

def compute_frame_timestamps(num_frames: int, hop_length: int, sample_rate: int, t_start: float = 0.0) -> np.ndarray:
    """
    Computes an array of timestamps corresponding to the center of each frame.
    """
    if num_frames == 0:
        return np.array([])
    return t_start + librosa.frames_to_time(np.arange(num_frames), sr=sample_rate, hop_length=hop_length)

def compute_rms_energy(pcm: np.ndarray, frame_length: int, hop_length: int, sample_rate: int, t_start: float = 0.0) -> Tuple[np.ndarray, np.ndarray, float, np.ndarray]:
    """
    Computes RMS energy contour, dB contour, total energy, and timestamps.
    """
    if len(pcm) == 0:
        return np.array([]), np.array([]), 0.0, np.array([])
        
    rms_contour = librosa.feature.rms(y=pcm, frame_length=frame_length, hop_length=hop_length, center=True)[0]
    db_contour = librosa.amplitude_to_db(rms_contour, ref=np.max, top_db=80.0)
    total_energy = float(np.sum(pcm**2))
    
    timestamps = compute_frame_timestamps(len(rms_contour), hop_length, sample_rate, t_start)
    return rms_contour, db_contour, total_energy, timestamps

def compute_zcr(pcm: np.ndarray, frame_length: int, hop_length: int, sample_rate: int, t_start: float = 0.0) -> Tuple[np.ndarray, np.ndarray]:
    """
    Computes Zero-Crossing Rate contour and timestamps.
    """
    if len(pcm) == 0:
        return np.array([]), np.array([])
        
    zcr_contour = librosa.feature.zero_crossing_rate(y=pcm, frame_length=frame_length, hop_length=hop_length, center=True)[0]
    timestamps = compute_frame_timestamps(len(zcr_contour), hop_length, sample_rate, t_start)
    return zcr_contour, timestamps
