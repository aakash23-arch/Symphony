"""
features.py
-----------
Extracts interpretable acoustic features that the anti-spoofing / voice-forensics
literature associates with synthetic (TTS/cloned) speech vs genuine human speech:

  - Pitch (F0) jitter        -> synthetic voices tend to have unnaturally SMOOTH F0
  - Amplitude shimmer        -> synthetic voices have less natural micro-variation
  - Spectral flatness        -> synthetic voices are often spectrally "flatter"
  - Spectral flux            -> frame-to-frame spectral change (naturalness proxy)
  - MFCC delta variance      -> micro-prosody variation
  - Harmonic-to-noise proxy  -> ratio of harmonic to percussive/noise energy
  - Pause/silence uniformity -> TTS engines tend to insert unnaturally regular pauses

This is a classical-DSP substitute for the WavLM-based classifier described in the
full product architecture. It needs no GPU, no large labeled dataset, and no
internet access at run time — which makes it demo-safe — while still producing a
per-feature explainability breakdown, which is what actually gets shown on stage.
"""

from __future__ import annotations
import numpy as np
import librosa

FEATURE_NAMES = [
    "pitch_jitter",
    "amp_shimmer",
    "spectral_flatness",
    "spectral_flux",
    "mfcc_delta_var",
    "harmonic_ratio",
    "pause_uniformity",
]


def _safe(val, default=0.0):
    if val is None or (isinstance(val, float) and (np.isnan(val) or np.isinf(val))):
        return default
    return float(val)


def extract_features(y: np.ndarray, sr: int) -> dict:
    """Return a dict of raw (unnormalized) feature values for one audio clip."""
    y = librosa.util.normalize(y.astype(np.float32))
    if len(y) < sr * 0.3:
        # pad very short clips so downstream analysis windows don't break
        y = np.pad(y, (0, int(sr * 0.3) - len(y)))

    # --- Pitch jitter -----------------------------------------------------
    f0, voiced_flag, _ = librosa.pyin(
        y, fmin=librosa.note_to_hz("C2"), fmax=librosa.note_to_hz("C7"), sr=sr
    )
    f0_voiced = f0[voiced_flag] if f0 is not None else np.array([])
    if len(f0_voiced) > 3:
        diffs = np.abs(np.diff(f0_voiced))
        jitter = np.mean(diffs) / (np.mean(f0_voiced) + 1e-6)
    else:
        jitter = 0.0

    # --- Amplitude shimmer --------------------------------------------------
    rms = librosa.feature.rms(y=y)[0]
    if len(rms) > 3:
        rms_diffs = np.abs(np.diff(rms))
        shimmer = np.mean(rms_diffs) / (np.mean(rms) + 1e-6)
    else:
        shimmer = 0.0

    # --- Spectral flatness ---------------------------------------------------
    flatness = np.mean(librosa.feature.spectral_flatness(y=y))

    # --- Spectral flux --------------------------------------------------------
    S = np.abs(librosa.stft(y))
    if S.shape[1] > 1:
        flux = np.mean(np.sqrt(np.sum(np.diff(S, axis=1) ** 2, axis=0)))
    else:
        flux = 0.0

    # --- MFCC delta variance (micro-prosody) -----------------------------------
    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
    mfcc_delta = librosa.feature.delta(mfcc)
    delta_var = np.mean(np.var(mfcc_delta, axis=1))

    # --- Harmonic ratio ----------------------------------------------------
    harm, perc = librosa.effects.hpss(y)
    harm_energy = np.sum(harm ** 2)
    perc_energy = np.sum(perc ** 2)
    harmonic_ratio = harm_energy / (harm_energy + perc_energy + 1e-6)

    # --- Pause uniformity -----------------------------------------------------
    intervals = librosa.effects.split(y, top_db=30)
    if len(intervals) > 2:
        gaps = intervals[1:, 0] - intervals[:-1, 1]
        gaps = gaps[gaps > 0]
        pause_uniformity = 1.0 - (np.std(gaps) / (np.mean(gaps) + 1e-6)) if len(gaps) else 0.5
        pause_uniformity = float(np.clip(pause_uniformity, 0, 1))
    else:
        pause_uniformity = 0.5  # not enough pauses to judge

    return {
        "pitch_jitter": _safe(jitter),
        "amp_shimmer": _safe(shimmer),
        "spectral_flatness": _safe(flatness),
        "spectral_flux": _safe(flux),
        "mfcc_delta_var": _safe(delta_var),
        "harmonic_ratio": _safe(harmonic_ratio),
        "pause_uniformity": _safe(pause_uniformity),
    }
