"""Feature bundle and extraction interfaces (C-17, C-18)."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict
import numpy as np

from .config import SignalProcessingConfig
from .dsp import StandardSignalProcessor
from .mfcc import compute_mfcc
from .temporal import compute_rms_energy, compute_zcr
from .pitch import compute_pitch_pyin, compute_f0_statistics, compute_jitter
from .prosody import compute_speaking_rate, compute_pause_statistics, compute_shimmer
from .spectral import compute_spectral_features
from .spectrogram import compute_log_mel_spectrogram


class FeatureBundle(BaseModel):
    """Container holding pre-extracted features for expert consumption."""
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    session_id: str
    frame_id: int
    spectral: Optional[Dict[str, Any]] = None
    raw_pcm: Optional[List[float]] = None
    prosody: Optional[Dict[str, Any]] = None
    temporal: Optional[Dict[str, Any]] = None
    quality: Optional[Dict[str, float]] = None


class FeatureExtractor(ABC):
    """Abstract interface for acoustic feature extraction."""

    @abstractmethod
    def extract_bundle(self, pcm: np.ndarray, sample_rate: int = 16000, session_id: str = "", frame_id: int = 0) -> FeatureBundle:
        """Extract spectral, raw, and prosodic features from raw PCM."""
        pass


class StandardFeatureExtractor(FeatureExtractor):
    """Concrete feature extractor combining all DSP modules."""
    
    def __init__(self, config: Optional[SignalProcessingConfig] = None):
        self.config = config or SignalProcessingConfig()
        self.dsp = StandardSignalProcessor()

    def extract_bundle(self, pcm: np.ndarray, sample_rate: int = 16000, session_id: str = "", frame_id: int = 0, include_raw: bool = False) -> FeatureBundle:
        """Extract spectral, raw, and prosodic features from raw PCM."""
        
        # Quality metrics
        snr_db = self.dsp.estimate_snr(pcm)
        clipping_ratio = float(np.mean(np.abs(pcm) >= 0.99)) if len(pcm) > 0 else 0.0
        
        # Temporal
        hop_length = self.config.spectrogram.hop_length
        rms_contour, db_contour, total_energy, timestamps = compute_rms_energy(
            pcm, self.config.spectrogram.win_length, hop_length, sample_rate
        )
        zcr_contour, _ = compute_zcr(
            pcm, self.config.spectrogram.win_length, hop_length, sample_rate
        )
        
        hop_duration_s = hop_length / sample_rate
        
        # Spectral & MFCC
        log_mel, mel_freqs, _ = compute_log_mel_spectrogram(pcm, self.config.spectrogram)
        mfcc, delta, delta_delta, _ = compute_mfcc(pcm, self.config.spectrogram, self.config.mfcc)
        spectral_stats = compute_spectral_features(pcm, self.config.spectrogram, sample_rate)
        
        # Pitch & Prosody
        f0, voiced_flag, _, _ = compute_pitch_pyin(pcm, self.config.pitch, sample_rate, hop_length)
        f0_stats = compute_f0_statistics(f0, voiced_flag)
        jitter = compute_jitter(f0, voiced_flag)
        shimmer = compute_shimmer(pcm, f0, voiced_flag, sample_rate, hop_length)
        
        speaking_rate = compute_speaking_rate(rms_contour, hop_duration_s, self.config.prosody)
        pause_stats = compute_pause_statistics(db_contour, hop_duration_s, self.config.prosody)
        
        voiced_fraction = float(np.mean(voiced_flag)) if len(voiced_flag) > 0 else 0.0
        
        return FeatureBundle(
            session_id=session_id,
            frame_id=frame_id,
            spectral={
                "log_mel": log_mel.tolist(),
                "mel_freqs": mel_freqs.tolist(),
                "mfcc": mfcc.tolist(),
                "mfcc_delta": delta.tolist(),
                "mfcc_delta_delta": delta_delta.tolist(),
                "centroid": spectral_stats["centroid"].tolist(),
                "bandwidth": spectral_stats["bandwidth"].tolist(),
                "flatness": spectral_stats["flatness"].tolist(),
                "rolloff": spectral_stats["rolloff"].tolist(),
                "flux": spectral_stats["flux"].tolist(),
                "contrast": spectral_stats["contrast"].tolist()
            },
            prosody={
                "f0_contour": f0.tolist(),
                "f0_mean": f0_stats["mean"],
                "f0_std": f0_stats["std"],
                "voiced_fraction": voiced_fraction,
                "speaking_rate_syl_per_sec": speaking_rate,
                "pause_ratio": pause_stats["pause_percentage"] / 100.0,
                "pause_count": pause_stats["pause_count"],
                "jitter": jitter,
                "shimmer": shimmer
            },
            temporal={
                "rms_contour": rms_contour.tolist(),
                "zcr_contour": zcr_contour.tolist(),
                "timestamps": timestamps.tolist(),
                "total_energy_db": db_contour.max() if len(db_contour) > 0 else 0.0
            },
            quality={
                "snr_db": snr_db,
                "clipping_ratio": clipping_ratio
            },
            raw_pcm=pcm.tolist() if include_raw else None
        )
