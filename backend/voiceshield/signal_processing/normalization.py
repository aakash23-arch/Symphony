import numpy as np
from typing import Optional

class AudioNormalizer:
    @staticmethod
    def normalize_peak(pcm: np.ndarray, target_peak: float = 0.95, floor: float = 1e-4) -> np.ndarray:
        """
        Normalizes the peak amplitude of the signal to the target_peak.
        If the signal is near silence (peak < floor), it returns the signal unmodified.
        """
        if not np.isfinite(pcm).all():
            pcm = np.nan_to_num(pcm)
        
        peak = np.max(np.abs(pcm))
        if peak < floor:
            return pcm.copy()
            
        scaling_factor = target_peak / peak
        return pcm * scaling_factor

    @staticmethod
    def normalize_rms(pcm: np.ndarray, target_rms: float = 0.1, floor: float = 1e-4) -> np.ndarray:
        """
        Normalizes the RMS amplitude of the signal to the target_rms.
        If the signal is near silence (RMS < floor), it returns the signal unmodified.
        """
        if not np.isfinite(pcm).all():
            pcm = np.nan_to_num(pcm)
            
        rms = np.sqrt(np.mean(pcm**2))
        if rms < floor:
            return pcm.copy()
            
        scaling_factor = target_rms / rms
        return pcm * scaling_factor
