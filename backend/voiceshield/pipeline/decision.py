"""Multi-tier policy decision engine combining acoustic risk and contextual transaction parameters."""

from decimal import Decimal
from typing import Optional

from .contracts import (
    CalibratedScore,
    ForensicEvidence,
    PolicyVerdict,
    RiskBand,
    RiskDecisionResult,
    TransactionContext,
)


class DecisionEngine:
    """Evaluates multi-tier policy rules to produce an actionable verdict."""

    HIGH_VALUE_THRESHOLD = Decimal("1000000.00")  # 10 Lakh INR

    def decide(
        self,
        calibrated: CalibratedScore,
        evidence: ForensicEvidence,
        transaction: Optional[TransactionContext] = None,
    ) -> RiskDecisionResult:
        """Apply deterministic policy ladder to produce risk band and verdict."""
        p_fake = calibrated.calibrated_p_synthetic
        conf = calibrated.calibrated_confidence

        # 1. Base acoustic risk score (0.0 to 1.0)
        risk_score = p_fake

        # Context modifiers
        is_high_value = False
        is_new_beneficiary = False
        if transaction:
            if transaction.amount and transaction.amount >= self.HIGH_VALUE_THRESHOLD:
                is_high_value = True
            if transaction.beneficiary_novelty == "NEW":
                is_new_beneficiary = True

        # Policy Rule 1: High Synthetic Confidence -> HOLD
        if p_fake >= 0.65 and conf >= 0.55:
            if is_high_value or (transaction and transaction.urgency_claimed):
                return RiskDecisionResult(
                    risk_band=RiskBand.CRITICAL,
                    risk_score=float(min(1.0, risk_score + 0.1)),
                    policy_action=PolicyVerdict.HOLD,
                    matched_policy_rule="P-CRITICAL-VOICE-CLONE-HIGH-VALUE",
                    requires_step_up_verification=True,
                    requires_transaction_hold=True,
                )
            return RiskDecisionResult(
                risk_band=RiskBand.HIGH,
                risk_score=risk_score,
                policy_action=PolicyVerdict.HOLD,
                matched_policy_rule="P-SUSPICIOUS-SYNTHETIC-VOICE",
                requires_step_up_verification=True,
                requires_transaction_hold=True,
            )

        # Policy Rule 2: Low Confidence / High Uncertainty / Borderline -> STEP_UP
        if conf < 0.55 or (0.35 <= p_fake < 0.65):
            return RiskDecisionResult(
                risk_band=RiskBand.UNCERTAIN,
                risk_score=risk_score,
                policy_action=PolicyVerdict.STEP_UP,
                matched_policy_rule="P-INSUFFICIENT-CONFIDENCE-STEP-UP",
                requires_step_up_verification=True,
                requires_transaction_hold=is_high_value,
            )

        # Policy Rule 3: Genuine Voice with Context Anomaly -> STEP_UP or ALLOW
        if p_fake < 0.35:
            if is_new_beneficiary and is_high_value:
                return RiskDecisionResult(
                    risk_band=RiskBand.ELEVATED,
                    risk_score=float(risk_score + 0.15),
                    policy_action=PolicyVerdict.STEP_UP,
                    matched_policy_rule="P-GENUINE-VOICE-NEW-HIGH-VALUE-PAYEE",
                    requires_step_up_verification=True,
                    requires_transaction_hold=False,
                )
            return RiskDecisionResult(
                risk_band=RiskBand.LOW,
                risk_score=risk_score,
                policy_action=PolicyVerdict.ALLOW,
                matched_policy_rule="P-AUTHENTIC-VOICE-BASELINE",
                requires_step_up_verification=False,
                requires_transaction_hold=False,
            )

        # Default Fallback
        return RiskDecisionResult(
            risk_band=RiskBand.UNCERTAIN,
            risk_score=risk_score,
            policy_action=PolicyVerdict.STEP_UP,
            matched_policy_rule="P-DEFAULT-INSPECTION",
            requires_step_up_verification=True,
            requires_transaction_hold=False,
        )
