"""Audio quality estimation (C-09).

Computes q_t in [0,1] from an SNR estimate, clipping ratio, effective bandwidth
and level.

q_t describes how good the AUDIO is, not how authentic the speaker is. It is
never evidence of spoofing. On estimator error q_t is None (unknown), which
widens downstream uncertainty -- it never falls back to a flattering value.
"""

from dataclasses import dataclass
from typing import Optional

import numpy as np

# SNR ramp: at or below SNR_FLOOR_DB the sub-score is 0, at or above
# SNR_CEIL_DB it is 1.
SNR_FLOOR_DB = 5.0
SNR_CEIL_DB = 35.0

#: Fraction of the frame's own peak at or above which a sample counts as clipped.
CLIP_THRESHOLD = 0.999
#: Peak below which a frame is treated as silence for clipping purposes.
SILENCE_PEAK_FLOOR = 1e-4
#: Consecutive pinned samples required to count as a clipped run. A clean sine
#: touches its peak briefly; a clipped waveform holds it flat.
MIN_CLIP_RUN = 3
#: Clipping ratio at which the clipping sub-score reaches 0.
CLIP_RATIO_FULL_PENALTY = 0.05

#: RMS dBFS band considered healthy for speech.
LEVEL_LOW_DB = -45.0
LEVEL_GOOD_LOW_DB = -26.0
LEVEL_GOOD_HIGH_DB = -8.0
LEVEL_HIGH_DB = -1.0

#: Bandwidth (Hz) at or above which the bandwidth sub-score is 1. Narrowband
#: telephony tops out here, so a 3.4 kHz channel is "full marks for its kind":
#: q_t rates usability, and must not penalise a call for being a phone call.
BANDWIDTH_FULL_HZ = 3400.0
#: Bandwidth (Hz) at or below which the bandwidth sub-score is 0.
BANDWIDTH_FLOOR_HZ = 300.0

#: Lower bound applied to each sub-score before the geometric mean. A single
#: zero component must drag q_t down without collapsing it to exactly 0, which
#: would assert certainty the estimator does not have.
COMPONENT_FLOOR = 0.05

# Relative weights for the geometric mean.
WEIGHTS = {"snr": 0.4, "clipping": 0.2, "bandwidth": 0.2, "level": 0.2}

_EPS = 1e-12


@dataclass
class QualityReport:
    """q_t plus its component sub-scores (sub-scores are telemetry only)."""

    q_t: Optional[float]
    snr_db: Optional[float] = None
    snr_score: Optional[float] = None
    clipping_ratio: Optional[float] = None
    clipping_score: Optional[float] = None
    bandwidth_score: Optional[float] = None
    rms_dbfs: Optional[float] = None
    level_score: Optional[float] = None


def _ramp(value: float, low: float, high: float) -> float:
    """Linear 0->1 ramp between low and high, clamped."""
    if high <= low:
        return 0.0
    return float(min(max((value - low) / (high - low), 0.0), 1.0))


class QualityEstimator:
    """Estimate per-frame audio quality q_t."""

    def __init__(self, sub_window_ms: int = 20):
        self.sub_window_ms = sub_window_ms
        self.error_count = 0

    # -- components -----------------------------------------------------------

    def estimate_snr_db(self, pcm: np.ndarray, sample_rate: int) -> Optional[float]:
        """Estimate SNR as active-speech energy over the residual noise floor.

        The noise floor is taken from the quietest sub-windows, but is bounded
        below by the signal's own residual energy: a perfectly steady signal has
        no quiet window, and treating that as "no SNR" would confuse a clean
        stationary tone with a noisy one.
        """
        if pcm.size == 0 or sample_rate <= 0:
            return None
        win = max(int(sample_rate * self.sub_window_ms / 1000.0), 1)
        if pcm.size < win * 2:
            return None
        usable = (pcm.size // win) * win
        windows = pcm[:usable].reshape(-1, win).astype(np.float64)
        energies = np.mean(windows**2, axis=1)
        if energies.size < 2:
            return None

        signal = float(np.percentile(energies, 90))
        if signal <= _EPS:
            return None

        noise = float(np.percentile(energies, 10))
        # For a stationary signal the percentile split collapses. Fall back to
        # the high-frequency residual, which tracks broadband noise rather than
        # the amplitude envelope.
        if noise >= signal * 0.5:
            noise = self._residual_noise_energy(pcm)

        return float(10.0 * np.log10((signal + _EPS) / (noise + _EPS)))

    @staticmethod
    def _residual_noise_energy(pcm: np.ndarray) -> float:
        """Energy of the sample-to-sample residual, a broadband-noise proxy."""
        if pcm.size < 3:
            return _EPS
        # Second difference suppresses smooth (tonal/voiced) structure and keeps
        # broadband noise; the 1/6 factor is its variance gain on white noise.
        residual = np.diff(pcm.astype(np.float64), n=2)
        return float(np.mean(residual**2) / 6.0)

    @staticmethod
    def clipping_ratio(pcm: np.ndarray) -> float:
        """Fraction of samples inside a FLAT RUN pinned at the frame's own peak.

        The threshold is relative, not absolute: C-07 peak-normalises every frame,
        so an absolute full-scale test could never fire. But peak proximity alone
        is not clipping -- a clean sine sits near its peak on every cycle. What
        distinguishes clipping is a flat top: consecutive samples pinned at the
        peak with no slope between them. Counting only runs of at least
        MIN_CLIP_RUN keeps clean tonal audio from being scored as clipped.
        """
        if pcm.size == 0:
            return 0.0
        peak = float(np.max(np.abs(pcm)))
        if peak < SILENCE_PEAK_FLOOR:
            return 0.0

        pinned = np.abs(pcm) >= peak * CLIP_THRESHOLD
        if not pinned.any():
            return 0.0

        # Count samples belonging to runs of >= MIN_CLIP_RUN pinned samples.
        padded = np.concatenate(([False], pinned, [False]))
        edges = np.flatnonzero(padded[1:] != padded[:-1])
        starts, ends = edges[0::2], edges[1::2]
        lengths = ends - starts
        clipped_samples = int(lengths[lengths >= MIN_CLIP_RUN].sum())
        return float(clipped_samples / pcm.size)

    @staticmethod
    def rms_dbfs(pcm: np.ndarray) -> Optional[float]:
        if pcm.size == 0:
            return None
        rms = float(np.sqrt(np.mean(pcm.astype(np.float64) ** 2)))
        if rms <= _EPS:
            return -120.0
        return float(20.0 * np.log10(rms))

    @staticmethod
    def level_score(rms_db: Optional[float]) -> float:
        """Penalise both too-quiet and near-clipping levels."""
        if rms_db is None:
            return 0.0
        if LEVEL_GOOD_LOW_DB <= rms_db <= LEVEL_GOOD_HIGH_DB:
            return 1.0
        if rms_db < LEVEL_GOOD_LOW_DB:
            return _ramp(rms_db, LEVEL_LOW_DB, LEVEL_GOOD_LOW_DB)
        return 1.0 - _ramp(rms_db, LEVEL_GOOD_HIGH_DB, LEVEL_HIGH_DB)

    @staticmethod
    def bandwidth_score(bandwidth: Optional[float], sample_rate: int) -> float:
        """Ramp from BANDWIDTH_FLOOR_HZ (unusable) to BANDWIDTH_FULL_HZ (fine)."""
        if bandwidth is None or bandwidth <= 0:
            return 0.0
        nyquist = sample_rate / 2.0
        full = min(BANDWIDTH_FULL_HZ, nyquist) if nyquist > 0 else BANDWIDTH_FULL_HZ
        return _ramp(bandwidth, BANDWIDTH_FLOOR_HZ, full)

    # -- combination ----------------------------------------------------------

    def estimate(
        self,
        pcm: np.ndarray,
        sample_rate: int,
        bandwidth: Optional[float] = None,
    ) -> QualityReport:
        """Compute q_t and its sub-scores. Any failure yields q_t = None."""
        try:
            if pcm.size == 0:
                return QualityReport(q_t=None)

            snr_db = self.estimate_snr_db(pcm, sample_rate)
            snr_score = _ramp(snr_db, SNR_FLOOR_DB, SNR_CEIL_DB) if snr_db is not None else None

            clip_ratio = self.clipping_ratio(pcm)
            clip_score = 1.0 - _ramp(clip_ratio, 0.0, CLIP_RATIO_FULL_PENALTY)

            bw_score = self.bandwidth_score(bandwidth, sample_rate)

            rms_db = self.rms_dbfs(pcm)
            lvl_score = self.level_score(rms_db)

            components = {
                "snr": snr_score,
                "clipping": clip_score,
                "bandwidth": bw_score,
                "level": lvl_score,
            }

            # Weighted geometric mean over the components we could measure, so a
            # single bad component drags q_t down instead of being averaged away.
            # Each score is floored before the log: one zero component must pull
            # q_t down hard, but it must not annihilate the whole estimate --
            # q_t = 0 would claim certainty that the audio is worthless.
            log_sum = 0.0
            weight_sum = 0.0
            for name, score in components.items():
                if score is None:
                    continue
                weight = WEIGHTS[name]
                log_sum += weight * np.log(max(float(score), COMPONENT_FLOOR))
                weight_sum += weight

            if weight_sum <= 0:
                return QualityReport(q_t=None)

            q_t = float(np.exp(log_sum / weight_sum))
            q_t = float(min(max(q_t, 0.0), 1.0))

            return QualityReport(
                q_t=q_t,
                snr_db=snr_db,
                snr_score=snr_score,
                clipping_ratio=clip_ratio,
                clipping_score=clip_score,
                bandwidth_score=bw_score,
                rms_dbfs=rms_db,
                level_score=lvl_score,
            )
        except Exception:
            self.error_count += 1
            return QualityReport(q_t=None)
