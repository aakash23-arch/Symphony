import numpy as np
import librosa

class AudioResampler:
    @staticmethod
    def resample(pcm: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
        """
        Resamples the audio to the target sample rate using high-quality polyphase filtering.
        If orig_sr == target_sr, returns the original array.
        """
        if orig_sr == target_sr:
            return pcm.copy()
            
        # Using soxr_hq if available, else standard polyphase via librosa
        resampled_pcm = librosa.resample(pcm, orig_sr=orig_sr, target_sr=target_sr, res_type='soxr_hq')
        return resampled_pcm
