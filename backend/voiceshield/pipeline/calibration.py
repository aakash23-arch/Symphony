"""Calibration and uncertainty estimation module."""

import numpy as np

from .contracts import CalibratedScore, ForensicEvidence, FusedScore, PreprocessingSummary


class ConfidenceCalibrator:
    """Calibrates fused probability and estimates uncertainty intervals."""

    def calibrate(
        self,
        fused: FusedScore,
        evidence: ForensicEvidence,
        preprocessing: PreprocessingSummary,
    ) -> CalibratedScore:
        """Apply quality-conditioned probability adjustment and uncertainty range."""
        p_raw = fused.fused_p_synthetic
        conf_raw = fused.raw_confidence

        # 1. Quality-based Shrinkage Factor:
        # If active speech duration is short (< 1.5s) or SNR < 12 dB, shrink towards prior (0.5)
        # and reduce confidence.
        shrinkage = evidence.quality_conditioned_weight

        # Pull probability slightly toward 0.5 under low quality
        p_calibrated = float(0.5 + (p_raw - 0.5) * shrinkage)
        p_calibrated = float(np.clip(p_calibrated, 0.001, 0.999))

        conf_calibrated = float(conf_raw * shrinkage)
        conf_calibrated = float(np.clip(conf_calibrated, 0.1, 0.98))

        # 2. Confidence Interval (Wilson-style or Gaussian variance approximation)
        # Margin of error is wider when confidence is low
        margin = (1.0 - conf_calibrated) * 0.45
        ci_low = float(np.clip(p_calibrated - margin, 0.0, 1.0))
        ci_high = float(np.clip(p_calibrated + margin, 0.0, 1.0))

        # 3. Categorize Uncertainty Level
        if conf_calibrated >= 0.80:
            uncertainty = "LOW"
        elif conf_calibrated >= 0.55:
            uncertainty = "MODERATE"
        else:
            uncertainty = "HIGH"

        return CalibratedScore(
            calibrated_p_synthetic=p_calibrated,
            calibrated_confidence=conf_calibrated,
            confidence_interval_low=ci_low,
            confidence_interval_high=ci_high,
            uncertainty_level=uncertainty,
            shrinkage_factor_applied=float(shrinkage),
        )
