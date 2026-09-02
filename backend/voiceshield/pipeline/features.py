"""Acoustic feature extraction module for signal forensics and quality auditing."""

from typing import Dict, Any, Optional
import librosa
import numpy as np

from .contracts import AcousticFeaturesSummary


class FeatureExtractor:
    """Extracts DSP spectral, prosodic, pitch, and temporal feature summaries."""

    def extract_features(
        self, pcm: np.ndarray, sample_rate: int = 16000
    ) -> AcousticFeaturesSummary:
        """Extract spectral, temporal, and pitch metrics from 16kHz PCM."""
        if len(pcm) == 0:
            return AcousticFeaturesSummary(
                spectral_centroid_mean_hz=0.0,
                spectral_bandwidth_mean_hz=0.0,
                spectral_flatness_mean=0.0,
                spectral_rolloff_mean_hz=0.0,
                f0_mean_hz=None,
                f0_std_hz=None,
                f0_voiced_fraction=0.0,
                jitter_local=None,
                shimmer_local=None,
                rms_energy_mean=0.0,
                zero_crossing_rate_mean=0.0,
            )

        # 1. Spectral Features
        centroid = librosa.feature.spectral_centroid(y=pcm, sr=sample_rate)
        bandwidth = librosa.feature.spectral_bandwidth(y=pcm, sr=sample_rate)
        flatness = librosa.feature.spectral_flatness(y=pcm)
        rolloff = librosa.feature.spectral_rolloff(y=pcm, sr=sample_rate, roll_percent=0.85)

        centroid_mean = float(np.mean(centroid))
        bandwidth_mean = float(np.mean(bandwidth))
        flatness_mean = float(np.mean(flatness))
        rolloff_mean = float(np.mean(rolloff))

        # 2. Temporal Features
        rms = librosa.feature.rms(y=pcm)
        zcr = librosa.feature.zero_crossing_rate(y=pcm)
        rms_mean = float(np.mean(rms))
        zcr_mean = float(np.mean(zcr))

        # 3. Pitch (F0) & Voicing via pYIN
        f0_mean: Optional[float] = None
        f0_std: Optional[float] = None
        voiced_frac: float = 0.0
        jitter_val: Optional[float] = None
        shimmer_val: Optional[float] = None

        try:
            # Only run pYIN if there is sufficient sample length
            if len(pcm) >= int(0.2 * sample_rate):
                f0, voiced_flag, _ = librosa.pyin(
                    pcm,
                    fmin=librosa.note_to_hz("C2"),
                    fmax=librosa.note_to_hz("C7"),
                    sr=sample_rate,
                    frame_length=2048,
                    hop_length=512,
                )
                valid_f0 = f0[voiced_flag & np.isfinite(f0)] if voiced_flag is not None else np.array([])

                if len(valid_f0) > 3:
                    f0_mean = float(np.mean(valid_f0))
                    f0_std = float(np.std(valid_f0))
                    voiced_frac = float(len(valid_f0) / len(f0))

                    # Local Jitter: Relative cycle-to-cycle pitch period variation
                    periods = 1.0 / valid_f0
                    diff_periods = np.abs(np.diff(periods))
                    mean_period = np.mean(periods)
                    if mean_period > 1e-6:
                        jitter_val = float(np.mean(diff_periods) / mean_period)

                    # Local Shimmer: Relative cycle-to-cycle peak amplitude variation
                    # Sample peak amplitudes at voiced frame boundaries
                    frame_indices = np.where(voiced_flag)[0] * 512
                    frame_amps = []
                    for idx in frame_indices:
                        if idx + 512 <= len(pcm):
                            frame_amps.append(np.max(np.abs(pcm[idx : idx + 512])))
                    if len(frame_amps) > 3:
                        amps_arr = np.array(frame_amps)
                        diff_amps = np.abs(np.diff(amps_arr))
                        mean_amp = np.mean(amps_arr)
                        if mean_amp > 1e-4:
                            shimmer_val = float(np.mean(diff_amps) / mean_amp)
        except Exception:
            # Pitch extraction failed gracefully on degraded/noisy input
            pass

        return AcousticFeaturesSummary(
            spectral_centroid_mean_hz=centroid_mean,
            spectral_bandwidth_mean_hz=bandwidth_mean,
            spectral_flatness_mean=flatness_mean,
            spectral_rolloff_mean_hz=rolloff_mean,
            f0_mean_hz=f0_mean,
            f0_std_hz=f0_std,
            f0_voiced_fraction=voiced_frac,
            jitter_local=jitter_val,
            shimmer_local=shimmer_val,
            rms_energy_mean=rms_mean,
            zero_crossing_rate_mean=zcr_mean,
        )
