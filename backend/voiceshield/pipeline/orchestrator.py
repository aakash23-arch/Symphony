"""Canonical pipeline orchestrator executing the full anti-spoofing workflow."""

import time
import uuid
from typing import Optional
import numpy as np

from .calibration import ConfidenceCalibrator
from .contracts import (
    AcousticFeaturesSummary,
    AudioFormat,
    AudioMetadata,
    AudioValidationResult,
    CalibratedScore,
    ConfidenceScore,
    DecisionVerdict,
    DetectorResult,
    DetectorScoreItem,
    EvidenceItem,
    ForensicEvidence,
    FusedScore,
    InferenceRequest,
    InferenceResponse,
    OverallRisk,
    PolicyVerdict,
    PreprocessingSummary,
    ProcessingLatency,
    RiskBand,
    RiskDecisionResult,
    StructuredExplanation,
    ValidationStatus,
)
from .decision import DecisionEngine
from .detectors import DetectorRegistry, get_default_detector_registry
from .evidence import EvidenceEngine
from .explanation import ExplanationEngine
from .features import FeatureExtractor
from .fusion import ScoreFusion
from .preprocessor import AudioPreprocessor
from .validator import AudioValidator


class InferenceOrchestrator:
    """Coordinates the modular audio anti-spoofing pipeline execution."""

    def __init__(
        self,
        validator: Optional[AudioValidator] = None,
        preprocessor: Optional[AudioPreprocessor] = None,
        features_extractor: Optional[FeatureExtractor] = None,
        detectors_registry: Optional[DetectorRegistry] = None,
        evidence_engine: Optional[EvidenceEngine] = None,
        score_fusion: Optional[ScoreFusion] = None,
        calibrator: Optional[ConfidenceCalibrator] = None,
        decision_engine: Optional[DecisionEngine] = None,
        explanation_engine: Optional[ExplanationEngine] = None,
    ):
        self.validator = validator or AudioValidator()
        self.preprocessor = preprocessor or AudioPreprocessor()
        self.features_extractor = features_extractor or FeatureExtractor()
        self.detectors_registry = detectors_registry or get_default_detector_registry()
        self.evidence_engine = evidence_engine or EvidenceEngine()
        self.score_fusion = score_fusion or ScoreFusion()
        self.calibrator = calibrator or ConfidenceCalibrator()
        self.decision_engine = decision_engine or DecisionEngine()
        self.explanation_engine = explanation_engine or ExplanationEngine()

    def _build_validation_failure_response(
        self,
        session_id: str,
        val_report: AudioValidationResult,
        t_start: float,
        val_ms: float,
        prep_ms: float = 0.0,
    ) -> InferenceResponse:
        """Construct structured error envelope when audio validation/decoding fails."""
        exec_time = (time.perf_counter() - t_start) * 1000.0
        overall = OverallRisk(
            risk_score=0.5,
            risk_band=RiskBand.UNCERTAIN,
            severity_level="UNCERTAIN",
            summary=f"Audio validation failed: {'; '.join(val_report.validation_notes)}",
        )
        dec_verdict = DecisionVerdict(
            verdict=PolicyVerdict.STEP_UP,
            matched_rule="P-INVALID-AUDIO-PAYLOAD",
            requires_step_up=True,
            requires_hold=False,
            action_narrative="Audio payload could not be decoded or failed integrity checks. Step-up verification required.",
        )
        conf = ConfidenceScore(
            score=0.0,
            uncertainty_level="HIGH",
            confidence_interval=[0.0, 1.0],
            shrinkage_applied=0.0,
        )
        lat = ProcessingLatency(
            total_ms=round(exec_time, 2),
            validation_ms=round(val_ms, 2),
            preprocessing_ms=round(prep_ms, 2),
            feature_extraction_ms=0.0,
            detector_breakdown_ms={},
            fusion_and_calibration_ms=0.0,
        )
        meta = AudioMetadata(
            duration_s=float(val_report.duration_seconds),
            active_speech_duration_s=0.0,
            sample_rate_hz=int(val_report.sample_rate),
            channels=int(val_report.channels),
            snr_db=0.0,
            voiced_ratio=0.0,
            clipping_detected=bool(val_report.clipping_ratio > 0.01),
            peak_amplitude_dbfs=0.0,
        )

        return InferenceResponse(
            request_id=session_id,
            session_id=session_id,
            is_valid_audio=False,
            pipeline_version="voiceshield-pipeline-v3.0",
            processing_time=round(exec_time, 2),
            overall_risk=overall,
            decision=dec_verdict,
            confidence=conf,
            detector_scores=[],
            evidence_items=[
                EvidenceItem(
                    signal="AUDIO_PAYLOAD_VALIDATION",
                    category="SIGNAL_QUALITY",
                    score=1.0,
                    severity="CRITICAL",
                    explanation=f"Audio decoding or validation failure: {'; '.join(val_report.validation_notes)}",
                )
            ],
            processing_latency=lat,
            model_versions={
                "wav2vec2_deepfake": "mo-thecreator/Deepfake-audio-detection-v1.0",
                "wavlm_base_plus_sv": "microsoft/wavlm-base-plus-sv-xvector-512d",
                "dsp_forensics": "voiceshield-acoustic-physics-v2.1",
                "pipeline_orchestrator": "voiceshield-pipeline-v3.0",
            },
            audio_metadata=meta,
            risk_score=0.5,
            confidence_score=0.0,
            processing_time_ms=round(exec_time, 2),
            models={
                "wav2vec2_deepfake": "mo-thecreator/Deepfake-audio-detection-v1.0",
                "wavlm_base_plus_sv": "microsoft/wavlm-base-plus-sv-xvector-512d",
                "dsp_forensics": "voiceshield-acoustic-physics-v2.1",
                "pipeline_orchestrator": "voiceshield-pipeline-v3.0",
            },
            verdict=PolicyVerdict.STEP_UP,
            risk_band=RiskBand.UNCERTAIN,
            calibrated_p_synthetic=0.5,
            validation=val_report,
            preprocessing=PreprocessingSummary(
                original_sample_rate=int(val_report.sample_rate),
                target_sample_rate=16000,
                original_channels=int(val_report.channels),
                original_duration_s=float(val_report.duration_seconds),
                active_speech_duration_s=0.0,
                voiced_ratio=0.0,
                snr_db=0.0,
                num_segments=0,
                peak_amplitude=0.0,
                normalization_gain_db=0.0,
            ),
            features=AcousticFeaturesSummary(
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
            ),
            detectors=[],
            evidence=ForensicEvidence(
                detectors_evaluated=[],
                active_detectors_count=0,
                anomalies_detected=[],
            ),
            calibration=CalibratedScore(
                calibrated_p_synthetic=0.5,
                calibrated_confidence=0.0,
                confidence_interval_low=0.0,
                confidence_interval_high=1.0,
                uncertainty_level="HIGH",
                shrinkage_factor_applied=0.0,
            ),
            explanation=StructuredExplanation(
                summary_statement=f"Audio validation failed: {'; '.join(val_report.validation_notes)}",
                primary_risk_drivers=[],
                forensic_anomaly_triggers=[],
                signal_quality_caveats=val_report.validation_notes,
            ),
            execution_time_ms=round(exec_time, 2),
        )

    def process_audio(
        self,
        audio_bytes: bytes,
        session_id: Optional[str] = None,
        request: Optional[InferenceRequest] = None,
    ) -> InferenceResponse:
        """Run the end-to-end anti-spoofing pipeline on raw audio bytes."""
        t_start = time.perf_counter()
        session_id = session_id or (request.session_id if request else None) or str(uuid.uuid4().hex)

        # 1. Validation
        t_val0 = time.perf_counter()
        is_valid, val_report = self.validator.validate_bytes(audio_bytes)
        val_ms = (time.perf_counter() - t_val0) * 1000.0
        if not is_valid and val_report.status != ValidationStatus.VALID:
            return self._build_validation_failure_response(
                session_id=session_id,
                val_report=val_report,
                t_start=t_start,
                val_ms=val_ms,
                prep_ms=0.0,
            )

        # 2. Decode & Preprocess (Resample to 16kHz, Peak Normalization, VAD, Segment)
        t_prep0 = time.perf_counter()
        try:
            pcm_16k, segments, prep_summary = self.preprocessor.process(audio_bytes)
        except Exception as exc:
            val_report = AudioValidationResult(
                status=ValidationStatus.CORRUPTED,
                is_valid=False,
                detected_format=AudioFormat.UNKNOWN,
                sample_rate=0,
                channels=0,
                duration_seconds=0.0,
                samples_count=0,
                clipping_ratio=0.0,
                is_silent=False,
                validation_notes=[f"Audio decoding failure: {str(exc)}"],
            )
            prep_ms = (time.perf_counter() - t_prep0) * 1000.0
            return self._build_validation_failure_response(
                session_id=session_id,
                val_report=val_report,
                t_start=t_start,
                val_ms=val_ms,
                prep_ms=prep_ms,
            )

        # Post-decode PCM validation
        pcm_val = self.validator.validate_pcm(pcm_16k, sample_rate=16000)
        prep_ms = (time.perf_counter() - t_prep0) * 1000.0
        if not pcm_val.is_valid:
            return self._build_validation_failure_response(
                session_id=session_id,
                val_report=pcm_val,
                t_start=t_start,
                val_ms=val_ms,
                prep_ms=prep_ms,
            )


        # 3. Acoustic Feature Extraction
        t_feat0 = time.perf_counter()
        features = self.features_extractor.extract_features(pcm_16k, sample_rate=16000)
        feat_ms = (time.perf_counter() - t_feat0) * 1000.0

        # 4. Model & Detector Inference (Neural Acoustic + Speaker Biometric + DSP Forensic)
        claimed_id = None
        if request:
            if request.transaction and request.transaction.caller_identity:
                claimed_id = request.transaction.caller_identity
            elif request.context_parameters and "claimed_identity" in request.context_parameters:
                claimed_id = str(request.context_parameters["claimed_identity"])

        detector_results = self.detectors_registry.run_all(
            full_pcm=pcm_16k,
            segments=segments,
            features=features,
            sample_rate=16000,
            claimed_identity=claimed_id,
        )

        # 5. Evidence Extraction
        evidence = self.evidence_engine.extract_evidence(
            detectors=detector_results,
            features=features,
            preprocessing=prep_summary,
        )

        # 6. Score Fusion & Calibration
        t_fuse0 = time.perf_counter()
        fused = self.score_fusion.fuse_scores(
            detectors=detector_results,
            evidence=evidence,
        )
        calibrated = self.calibrator.calibrate(
            fused=fused,
            evidence=evidence,
            preprocessing=prep_summary,
        )
        fuse_ms = (time.perf_counter() - t_fuse0) * 1000.0

        # 7. Decision Engine
        tx_context = request.transaction if request else None
        decision = self.decision_engine.decide(
            calibrated=calibrated,
            evidence=evidence,
            transaction=tx_context,
        )

        # 8. Structured Explanation
        explanation = self.explanation_engine.explain(
            decision=decision,
            calibrated=calibrated,
            evidence=evidence,
            detectors=detector_results,
            preprocessing=prep_summary,
            transaction=tx_context,
        )

        exec_time = (time.perf_counter() - t_start) * 1000.0

        # Structured Forensic Result Assembly
        severity_map = {
            RiskBand.LOW: "LOW",
            RiskBand.ELEVATED: "MEDIUM",
            RiskBand.HIGH: "HIGH",
            RiskBand.CRITICAL: "CRITICAL",
            RiskBand.UNCERTAIN: "UNCERTAIN",
        }
        overall = OverallRisk(
            risk_score=float(decision.risk_score),
            risk_band=decision.risk_band,
            severity_level=severity_map.get(decision.risk_band, "MEDIUM"),
            summary=explanation.summary_statement,
        )

        dec_verdict = DecisionVerdict(
            verdict=decision.policy_action,
            matched_rule=decision.matched_policy_rule,
            requires_step_up=decision.requires_step_up_verification,
            requires_hold=decision.requires_transaction_hold,
            action_narrative=f"Policy action {decision.policy_action.value} enforced under rule {decision.matched_policy_rule}.",
        )

        conf = ConfidenceScore(
            score=float(calibrated.calibrated_confidence),
            uncertainty_level=calibrated.uncertainty_level,
            confidence_interval=[float(calibrated.confidence_interval_low), float(calibrated.confidence_interval_high)],
            shrinkage_applied=float(calibrated.shrinkage_factor_applied),
        )

        det_scores: List[DetectorScoreItem] = []
        det_breakdown: Dict[str, float] = {}
        for d in detector_results:
            det_name = (
                "Wav2Vec2 Deepfake Sequence Classifier"
                if d.detector_id == "wav2vec2-deepfake"
                else (
                    "WavLM Speaker Biometric Verification"
                    if d.detector_id == "wavlm-xvector-sv"
                    else "Acoustic DSP Physics Forensics"
                )
            )
            w_fusion = 0.50 if d.detector_id == "wav2vec2-deepfake" else (0.35 if d.detector_id == "wavlm-xvector-sv" else 0.15)
            det_scores.append(
                DetectorScoreItem(
                    detector_id=d.detector_id,
                    detector_name=det_name,
                    detector_type=d.detector_type,
                    model_version=d.model_version,
                    p_synthetic=float(d.p_fake),
                    confidence=float(d.raw_confidence),
                    status=d.status,
                    latency_ms=float(d.latency_ms),
                    weight_in_fusion=w_fusion,
                )
            )
            det_breakdown[d.detector_id] = float(d.latency_ms)

        evidence_items: List[EvidenceItem] = []
        for factor in explanation.primary_risk_drivers:
            evidence_items.append(
                EvidenceItem(
                    signal=factor.factor_name,
                    category=factor.category,
                    score=float(factor.contribution),
                    severity="CRITICAL" if factor.contribution > 0.70 else ("HIGH" if factor.contribution > 0.40 else ("LOW" if factor.contribution < -0.40 else "MEDIUM")),
                    explanation=factor.description,
                )
            )
        for anomaly in evidence.anomalies_detected:
            evidence_items.append(
                EvidenceItem(
                    signal=f"DSP_ANOMALY_{anomaly.anomaly_code}",
                    category="PHYSICAL_DSP",
                    score=float(anomaly.observed_value),
                    severity=anomaly.severity,
                    explanation=anomaly.description,
                )
            )

        lat = ProcessingLatency(
            total_ms=round(exec_time, 2),
            validation_ms=round(val_ms, 2),
            preprocessing_ms=round(prep_ms, 2),
            feature_extraction_ms=round(feat_ms, 2),
            detector_breakdown_ms={k: round(v, 2) for k, v in det_breakdown.items()},
            fusion_and_calibration_ms=round(fuse_ms, 2),
        )

        meta = AudioMetadata(
            duration_s=float(prep_summary.original_duration_s),
            active_speech_duration_s=float(prep_summary.active_speech_duration_s),
            sample_rate_hz=int(prep_summary.target_sample_rate),
            channels=int(prep_summary.original_channels),
            snr_db=float(prep_summary.snr_db),
            voiced_ratio=float(prep_summary.voiced_ratio),
            clipping_detected=val_report.clipping_ratio > 0.01,
            peak_amplitude_dbfs=float(prep_summary.peak_amplitude),
        )

        return InferenceResponse(
            request_id=session_id,
            session_id=session_id,
            is_valid_audio=True,
            pipeline_version="voiceshield-pipeline-v3.0",
            processing_time=round(exec_time, 2),
            overall_risk=overall,
            decision=dec_verdict,
            confidence=conf,
            detector_scores=det_scores,
            evidence_items=evidence_items,
            processing_latency=lat,
            model_versions={
                "wav2vec2_deepfake": "mo-thecreator/Deepfake-audio-detection-v1.0",
                "wavlm_base_plus_sv": "microsoft/wavlm-base-plus-sv-xvector-512d",
                "dsp_forensics": "voiceshield-acoustic-physics-v2.1",
                "pipeline_orchestrator": "voiceshield-pipeline-v3.0",
            },
            audio_metadata=meta,
            risk_score=float(decision.risk_score),
            confidence_score=float(calibrated.calibrated_confidence),
            processing_time_ms=exec_time,
            models={
                "wav2vec2_deepfake": "mo-thecreator/Deepfake-audio-detection-v1.0",
                "wavlm_base_plus_sv": "microsoft/wavlm-base-plus-sv-xvector-512d",
                "dsp_forensics": "voiceshield-acoustic-physics-v2.1",
                "pipeline_orchestrator": "voiceshield-pipeline-v3.0",
            },
            verdict=decision.policy_action,
            risk_band=decision.risk_band,
            calibrated_p_synthetic=calibrated.calibrated_p_synthetic,
            validation=val_report,
            preprocessing=prep_summary,
            features=features,
            detectors=detector_results,
            evidence=evidence,
            calibration=calibrated,
            explanation=explanation,
            execution_time_ms=exec_time,
        )


# Singleton instance for application runtime
default_orchestrator = InferenceOrchestrator()
