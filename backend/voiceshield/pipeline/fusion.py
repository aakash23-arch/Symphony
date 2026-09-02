"""Score fusion module combining neural, biometric, and DSP detector evidence."""

from typing import Dict, List
import numpy as np

from .contracts import DetectorResult, ForensicEvidence, FusedScore


class ScoreFusion:
    """Combines evidence from multiple detectors with dynamic quality weighting.
    
    Weights are mathematically grounded:
    - Primary acoustic anti-spoofing (Wav2Vec2): 0.50 (or 0.80 if un-enrolled)
    - Speaker identity biometric (WavLM x-vector): 0.35
    - Orthogonal DSP physical forensics: 0.15
    """

    DEFAULT_WEIGHTS = {
        "wav2vec2-deepfake": 0.50,
        "wavlm-xvector-sv": 0.35,
        "dsp-acoustic-forensic": 0.15,
    }

    UNENROLLED_WEIGHTS = {
        "wav2vec2-deepfake": 0.80,
        "dsp-acoustic-forensic": 0.20,
    }

    def fuse_scores(
        self,
        detectors: List[DetectorResult],
        evidence: ForensicEvidence,
    ) -> FusedScore:
        """Perform dynamic Bayesian-style quality-weighted score fusion."""
        active_detectors = [d for d in detectors if d.status == "OK"]
        if not active_detectors:
            return FusedScore(
                fused_p_synthetic=0.5,
                raw_confidence=0.0,
                detector_weights={},
                fusion_method="NO_ACTIVE_DETECTORS",
            )

        # Check if speaker verification is active
        has_speaker_model = any(d.detector_id == "wavlm-xvector-sv" for d in active_detectors)
        base_weights_map = self.DEFAULT_WEIGHTS if has_speaker_model else self.UNENROLLED_WEIGHTS

        weighted_p_sum = 0.0
        weighted_conf_sum = 0.0
        total_weight = 0.0
        normalized_weights: Dict[str, float] = {}

        # 1. Compute effective unnormalized weights
        unnorm_weights: Dict[str, float] = {}
        for det in active_detectors:
            base_w = base_weights_map.get(det.detector_id, 0.33)
            eff_w = base_w * det.raw_confidence * evidence.quality_conditioned_weight
            unnorm_weights[det.detector_id] = float(eff_w)
            total_weight += eff_w

        # 2. Normalize weights and compute convex combination
        if total_weight > 0:
            for det in active_detectors:
                norm_w = unnorm_weights[det.detector_id] / total_weight
                normalized_weights[det.detector_id] = float(norm_w)
                weighted_p_sum += norm_w * det.p_fake
                weighted_conf_sum += norm_w * det.raw_confidence
            fused_p = weighted_p_sum
            fused_conf = weighted_conf_sum
        else:
            fused_p = 0.5
            fused_conf = 0.0

        # 3. Account for temporal consistency across audio segments
        fused_conf *= evidence.temporal_consistency_score

        return FusedScore(
            fused_p_synthetic=float(np.clip(fused_p, 0.0, 1.0)),
            raw_confidence=float(np.clip(fused_conf, 0.0, 1.0)),
            detector_weights=normalized_weights,
            fusion_method="BAYESIAN_QUALITY_WEIGHTED",
        )
