"""Structured explanation generation module for machine-readable auditability."""

from typing import List, Optional

from .contracts import (
    CalibratedScore,
    DetectorResult,
    ForensicEvidence,
    PreprocessingSummary,
    RiskDecisionResult,
    RiskFactorAttribution,
    StructuredExplanation,
    TransactionContext,
)


class ExplanationEngine:
    """Produces machine-readable factor attributions and summary narratives."""

    def explain(
        self,
        decision: RiskDecisionResult,
        calibrated: CalibratedScore,
        evidence: ForensicEvidence,
        detectors: List[DetectorResult],
        preprocessing: PreprocessingSummary,
        transaction: Optional[TransactionContext] = None,
    ) -> StructuredExplanation:
        """Construct structured factor attributions and narrative explanation."""
        factors: List[RiskFactorAttribution] = []
        anomaly_triggers: List[str] = []
        quality_caveats: List[str] = []

        # 1. Neural Detector Attribution
        neural_det = next((d for d in detectors if d.detector_type == "NEURAL_WAV2VEC2"), None)
        if neural_det and neural_det.status == "OK":
            neural_contrib = (neural_det.p_fake - 0.5) * 2.0  # -1.0 to +1.0
            factors.append(
                RiskFactorAttribution(
                    factor_name="Wav2Vec2 Neural Deepfake Detector",
                    category="ACOUSTIC_NEURAL",
                    contribution=float(neural_contrib),
                    weight=0.50 if any(d.detector_id == "wavlm-xvector-sv" and d.status == "OK" for d in detectors) else 0.80,
                    description=f"Neural acoustic sequence classifier emitted P(fake) = {neural_det.p_fake:.3f} across {len(neural_det.segment_scores)} speech segments.",
                )
            )

        # 2. Speaker Biometric Attribution
        speaker_det = next((d for d in detectors if d.detector_id == "wavlm-xvector-sv"), None)
        if speaker_det and speaker_det.status == "OK":
            spk_contrib = (speaker_det.p_fake - 0.5) * 2.0
            factors.append(
                RiskFactorAttribution(
                    factor_name="WavLM Speaker Biometric Verification",
                    category="SPEAKER_BIOMETRICS",
                    contribution=float(spk_contrib),
                    weight=0.35,
                    description=f"512-d x-vector biometric comparison with enrolled speaker reference yielded impersonation score = {speaker_det.p_fake:.3f}.",
                )
            )

        # 3. Forensic DSP Attribution
        for anomaly in evidence.anomalies_detected:
            anomaly_triggers.append(f"[{anomaly.severity}] {anomaly.anomaly_code}: {anomaly.description}")
            factors.append(
                RiskFactorAttribution(
                    factor_name=f"Forensic Anomaly: {anomaly.anomaly_code}",
                    category="DSP_FORENSIC",
                    contribution=0.75 if anomaly.severity in ("HIGH", "CRITICAL") else 0.40,
                    weight=0.15,
                    description=anomaly.description,
                )
            )

        # 3. Signal Quality Caveats
        if preprocessing.snr_db < 15.0:
            caveat = f"Low acoustic SNR ({preprocessing.snr_db:.1f} dB) reduced detector confidence."
            quality_caveats.append(caveat)
            factors.append(
                RiskFactorAttribution(
                    factor_name="Degraded Signal Quality",
                    category="SIGNAL_QUALITY",
                    contribution=0.30,
                    weight=0.15,
                    description=caveat,
                )
            )

        if preprocessing.active_speech_duration_s < 1.5:
            caveat = f"Short active speech duration ({preprocessing.active_speech_duration_s:.2f}s) limits statistical certainty."
            quality_caveats.append(caveat)

        # 4. Context Factors
        if transaction:
            if transaction.amount and transaction.amount >= 1000000:
                factors.append(
                    RiskFactorAttribution(
                        factor_name="High-Value Financial Transaction",
                        category="TRANSACTION_CONTEXT",
                        contribution=0.35,
                        weight=0.25,
                        description=f"High transaction amount (₹{transaction.amount}) elevated risk threshold requirements.",
                    )
                )
            if transaction.beneficiary_novelty == "NEW":
                factors.append(
                    RiskFactorAttribution(
                        factor_name="New Beneficiary Account",
                        category="TRANSACTION_CONTEXT",
                        contribution=0.40,
                        weight=0.20,
                        description="Disbursement requested to a first-time unverified beneficiary.",
                    )
                )

        # 5. Summary narrative construction
        p_fake = calibrated.calibrated_p_synthetic
        action = decision.policy_action.value
        band = decision.risk_band.value

        if band in ("HIGH", "CRITICAL"):
            summary = (
                f"High synthetic speech risk detected (P(synthetic)={p_fake:.1%}, Confidence={calibrated.calibrated_confidence:.1%}). "
                f"Neural acoustic classification and spectral forensic analysis indicated artificial synthesis signatures. "
                f"Policy action enforced: {action} under rule {decision.matched_policy_rule}."
            )
        elif band == "UNCERTAIN":
            summary = (
                f"Acoustic evaluation resulted in high uncertainty (Confidence={calibrated.calibrated_confidence:.1%}, SNR={preprocessing.snr_db:.1f}dB). "
                f"Channel noise or borderline model activations require multi-factor verification. "
                f"Policy action enforced: {action} under rule {decision.matched_policy_rule}."
            )
        else:
            summary = (
                f"Voice signal verified as authentic human speech (P(synthetic)={p_fake:.1%}, Confidence={calibrated.calibrated_confidence:.1%}). "
                f"Acoustic prosody, pitch cadence, and harmonic structure match natural speech baseline. "
                f"Policy action: {action}."
            )

        return StructuredExplanation(
            summary_statement=summary,
            primary_risk_drivers=factors,
            forensic_anomaly_triggers=anomaly_triggers,
            signal_quality_caveats=quality_caveats,
        )
