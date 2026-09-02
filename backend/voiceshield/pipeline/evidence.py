"""Evidence extraction and forensic anomaly aggregation engine."""

from typing import List
import numpy as np

from .contracts import (
    AcousticFeaturesSummary,
    DetectorResult,
    ForensicAnomaly,
    ForensicEvidence,
    PreprocessingSummary,
)


class EvidenceEngine:
    """Aggregates detector predictions and forensic indicators into structured evidence."""

    def extract_evidence(
        self,
        detectors: List[DetectorResult],
        features: AcousticFeaturesSummary,
        preprocessing: PreprocessingSummary,
    ) -> ForensicEvidence:
        """Analyze detector outputs, acoustic features, and preprocessing quality."""
        anomalies: List[ForensicAnomaly] = []
        detector_ids = [d.detector_id for d in detectors]
        active_count = len([d for d in detectors if d.status == "OK"])

        # 1. Inspect Inter-Segment Variance across neural detector
        neural_det = next((d for d in detectors if d.detector_type == "NEURAL_WAV2VEC2"), None)
        segment_variance = 0.0
        temporal_consistency = 1.0

        if neural_det and neural_det.segment_scores:
            scores = [s.p_fake for s in neural_det.segment_scores]
            if len(scores) > 1:
                segment_variance = float(np.var(scores))
                # High variance means inconsistent spoof signals across windows
                temporal_consistency = float(np.clip(1.0 - np.sqrt(segment_variance), 0.1, 1.0))

        # 2. Forensic Anomaly Checks
        # Anomaly A: Unnatural Pitch Rigidity
        if features.jitter_local is not None and features.f0_voiced_fraction > 0.3:
            if features.jitter_local < 0.002:
                anomalies.append(
                    ForensicAnomaly(
                        anomaly_code="SYNTHETIC_PITCH_RIGIDITY",
                        severity="HIGH",
                        description="Pitch period cycle-to-cycle perturbation (jitter) is unnaturally low (<0.002), characteristic of parametric neural vocoders.",
                        observed_value=float(features.jitter_local),
                        reference_threshold=0.005,
                    )
                )

        # Anomaly B: Elevated Spectral Flatness (Vocoder Artifacts)
        if features.spectral_flatness_mean > 0.035:
            anomalies.append(
                ForensicAnomaly(
                    anomaly_code="VOCODER_SPECTRAL_FLATNESS",
                    severity="MEDIUM",
                    description="Elevated average spectral flatness indicates high-frequency noise floor common in synthetic vocoder synthesis.",
                    observed_value=float(features.spectral_flatness_mean),
                    reference_threshold=0.02,
                )
            )

        # Anomaly C: Low Signal Quality / Telephony Degradation
        if preprocessing.snr_db < 10.0:
            anomalies.append(
                ForensicAnomaly(
                    anomaly_code="DEGRADED_CHANNEL_SNR",
                    severity="MEDIUM",
                    description=f"Acoustic channel SNR ({preprocessing.snr_db:.1f} dB) is severely degraded, introducing high uncertainty.",
                    observed_value=float(preprocessing.snr_db),
                    reference_threshold=15.0,
                )
            )

        # 3. Quality Conditioned Weight
        # Lower weight if SNR is low or active voiced speech is very short
        snr_factor = float(np.clip(preprocessing.snr_db / 20.0, 0.3, 1.0))
        duration_factor = float(np.clip(preprocessing.active_speech_duration_s / 2.0, 0.4, 1.0))
        quality_weight = float(snr_factor * duration_factor)

        return ForensicEvidence(
            detectors_evaluated=detector_ids,
            active_detectors_count=active_count,
            anomalies_detected=anomalies,
            segment_variance=float(segment_variance),
            temporal_consistency_score=float(temporal_consistency),
            quality_conditioned_weight=float(quality_weight),
        )
