"""Transparent additive risk scoring (C-38).

The scoring mechanism is deliberately a weighted sum of bounded factors rather
than a learned model. §9.3 permits a gradient-boosted contextual model, but it
also forbids that model from having the final say; until such a model exists
and has been calibrated, an additive breakdown is the honest implementation,
because it has a property no boosted ensemble gives for free:

    baseline + sum(contribution.points) == risk_score

That identity is asserted in the tests. It is what lets the explanation service
publish a breakdown that genuinely accounts for the number shown to an analyst,
rather than a post-hoc attribution that only approximates it.

What the score is NOT
---------------------
It is not a probability. Nothing here has been fitted against labelled fraud
outcomes, so 0.80 does not mean "80% likely fraudulent" - it means "this call
accumulated 0.80 of the concern this policy set knows how to express". The
output carries ``ScoreSemantics.UNCALIBRATED_RISK_SCORE`` to force that
distinction downstream, and only a real fitted calibration may change it.
"""

from decimal import Decimal
from math import log10
from typing import List, Optional, Tuple

from voiceshield.contracts import (
    BeneficiaryNovelty,
    CallSource,
    ContextVector,
    DecisionBand,
    EnrollmentStatus,
    KnownContactStatus,
    RiskContribution,
    VoiceBelief,
    VoipMobileIndicator,
    WorkflowState,
)

from .config import RiskConfig

INCREASES = "INCREASES_RISK"
DECREASES = "DECREASES_RISK"

#: Workflow states that count as a high-risk workflow in progress.
HIGH_RISK_WORKFLOWS = {
    WorkflowState.CREDENTIAL_RESET,
    WorkflowState.PAYEE_ADDITION,
    WorkflowState.LIMIT_INCREASE,
    WorkflowState.HIGH_VALUE_TRANSFER,
    WorkflowState.PRIVILEGED_AUTHORISATION,
}

#: Call sources that carry inherent origin risk, and how much of the weight
#: each attracts. An outbound callback is the bank dialling a number it already
#: holds, so it earns a credit elsewhere rather than a penalty here.
CALL_SOURCE_RISK = {
    CallSource.INBOUND_VOIP: 1.0,
    CallSource.INBOUND_PSTN: 0.35,
    CallSource.UNKNOWN: 0.5,
    CallSource.IN_APP: 0.0,
    CallSource.BRANCH: 0.0,
    CallSource.OUTBOUND_CALLBACK: 0.0,
}


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _ramp(value: float, floor: float, ceiling: float) -> float:
    """Linear 0..1 ramp of ``value`` between ``floor`` and ``ceiling``."""
    if ceiling <= floor:
        return 1.0 if value >= ceiling else 0.0
    return _clamp01((value - floor) / (ceiling - floor))


class FactorScorer:
    """Builds the ordered list of signed risk contributions for one assessment.

    Each ``_score_*`` method appends zero or more contributions. A factor whose
    evidence is absent appends nothing at all - it does not append a zero. That
    matters for explanation: "we had no beneficiary information" and "the
    beneficiary was known and added no risk" are different statements, and only
    the second should appear in a breakdown.
    """

    def __init__(self, config: Optional[RiskConfig] = None):
        self.config = config or RiskConfig()

    # --- contribution helper -------------------------------------------------

    def _add(
        self,
        out: List[RiskContribution],
        factor: str,
        strength: float,
        weight: float,
        detail: str,
        *,
        mitigating: bool = False,
    ) -> None:
        """Append one contribution scaled by ``strength`` in [0, 1]."""
        strength = _clamp01(strength)
        if strength <= 0.0:
            return
        points = weight * strength
        out.append(
            RiskContribution(
                factor=factor,
                weight=strength,
                direction=DECREASES if mitigating else INCREASES,
                points=-points if mitigating else points,
                detail=detail,
            )
        )

    # --- voice signals -------------------------------------------------------

    def _score_voice(self, out: List[RiskContribution], belief: VoiceBelief) -> None:
        p = self.config.params
        w = self.config.weights

        if belief.P_spoof is not None:
            self._add(
                out,
                "spoof_evidence",
                _ramp(belief.P_spoof, p.spoof_floor, 1.0),
                w.spoof_evidence,
                f"aggregated synthetic-speech evidence P_spoof={belief.P_spoof:.2f}",
            )
            if belief.P_spoof <= p.genuine_ceiling:
                # A confidently genuine voice is positive evidence, not merely
                # the absence of negative evidence; it should be able to pull a
                # borderline contextual case back down.
                self._add(
                    out,
                    "genuine_voice",
                    _ramp(p.genuine_ceiling - belief.P_spoof, 0.0, p.genuine_ceiling),
                    w.genuine_voice_credit,
                    f"voice evidence consistent with genuine speech (P_spoof={belief.P_spoof:.2f})",
                    mitigating=True,
                )

        similarity = self._speaker_similarity(belief)
        if similarity is not None:
            # Full weight at or below speaker_full_mismatch, tapering to zero at
            # the match threshold. Inverted ramp: lower similarity is worse.
            strength = 1.0 - _ramp(similarity, p.speaker_full_mismatch, p.speaker_match_threshold)
            self._add(
                out,
                "speaker_mismatch",
                strength,
                w.speaker_mismatch,
                f"speaker similarity {similarity:.2f} against enrolled reference",
            )

        acoustic = self._expert_probability(belief, ("E1", "E2", "E3"))
        if acoustic is not None:
            self._add(
                out,
                "acoustic_evidence",
                _ramp(acoustic, p.spoof_floor, 1.0),
                w.acoustic_evidence,
                f"spectro-temporal and waveform experts mean p={acoustic:.2f}",
            )

        prosody = self._expert_probability(belief, ("E5",))
        if prosody is not None:
            self._add(
                out,
                "prosody_evidence",
                _ramp(prosody, p.spoof_floor, 1.0),
                w.prosody_evidence,
                f"prosodic anomaly expert p={prosody:.2f}",
            )

        if belief.q_call is not None and belief.q_call < p.quality_floor:
            # Degraded audio is mildly adverse in its own right - it is what a
            # replay or a laundered synthetic stream looks like - but the far
            # larger consequence is the confidence penalty applied elsewhere.
            self._add(
                out,
                "audio_quality",
                1.0 - _ramp(belief.q_call, 0.0, p.quality_floor),
                w.acoustic_evidence * 0.5,
                f"degraded call audio quality q={belief.q_call:.2f}",
            )

    @staticmethod
    def _speaker_similarity(belief: VoiceBelief) -> Optional[float]:
        """Recover E4 speaker similarity from the belief's expert contributions.

        E4 publishes a spoof-direction probability, so similarity is its
        complement. Returns None when E4 abstained (unenrolled speaker), which
        is the common case and must not be mistaken for a mismatch.
        """
        for contrib in belief.contributing_experts:
            if contrib.expert_id == "E4":
                p = contrib.calibrated_p if contrib.calibrated_p is not None else contrib.raw_p
                if p is not None:
                    return _clamp01(1.0 - p)
        return None

    @staticmethod
    def _expert_probability(belief: VoiceBelief, expert_ids: Tuple[str, ...]) -> Optional[float]:
        """Mean calibrated probability across the named experts, or None."""
        values = [
            c.calibrated_p if c.calibrated_p is not None else c.raw_p
            for c in belief.contributing_experts
            if c.expert_id in expert_ids
        ]
        values = [v for v in values if v is not None]
        return sum(values) / len(values) if values else None

    # --- call context --------------------------------------------------------

    def _score_call_context(self, out: List[RiskContribution], ctx: ContextVector) -> None:
        w = self.config.weights
        p = self.config.params
        ident = ctx.identity
        num = ctx.number

        if ident.identity_mismatch is True:
            self._add(
                out, "identity_mismatch", 1.0, w.identity_mismatch,
                "claimed identity does not match the verified identity on record",
            )
        elif ident.verified_identity and ident.claimed_identity == ident.verified_identity:
            self._add(
                out, "identity_verified", 1.0, w.verified_identity_credit,
                "claimed identity matches an independently verified identity",
                mitigating=True,
            )

        if ident.enrollment_status == EnrollmentStatus.NOT_ENROLLED:
            self._add(
                out, "speaker_not_enrolled", 1.0, w.not_enrolled,
                "no enrolled voice reference exists for this identity",
            )

        if ident.known_contact == KnownContactStatus.FIRST_CONTACT:
            self._add(
                out, "first_contact", 1.0, w.unknown_contact,
                "caller has no established contact history with this identity",
            )
        elif ident.known_contact == KnownContactStatus.KNOWN_CONTACT:
            self._add(
                out, "known_contact", 1.0, w.known_contact_credit,
                "caller is an established contact of this identity",
                mitigating=True,
            )

        if num.known_fraud_status is True:
            self._add(
                out, "number_known_fraud", 1.0, w.number_known_fraud,
                "originating number carries a known-fraud marking",
            )

        if num.reputation is not None and num.reputation < p.reputation_clean:
            self._add(
                out, "number_reputation", 1.0 - _ramp(num.reputation, 0.0, p.reputation_clean),
                w.number_reputation,
                f"originating number reputation {num.reputation:.2f} below clean threshold",
            )

        if num.age_days is not None and num.age_days < p.number_new_days:
            self._add(
                out, "number_recently_created",
                1.0 - _ramp(float(num.age_days), 0.0, float(p.number_new_days)),
                w.number_recently_created,
                f"originating number provisioned {num.age_days} days ago",
            )

        if num.port_history is True:
            self._add(
                out, "number_port_history", 1.0, w.number_port_history,
                "originating number has recent porting history",
            )

        source = ctx.technical.call_source
        source_strength = CALL_SOURCE_RISK.get(source, 0.5)
        if source_strength > 0.0:
            self._add(
                out, "call_source", source_strength, w.call_source_risk,
                f"call arrived via {source.value}",
            )
        elif source == CallSource.OUTBOUND_CALLBACK:
            self._add(
                out, "outbound_callback", 1.0, w.outbound_callback_credit,
                "contact established by an outbound callback to a number already on record",
                mitigating=True,
            )

        if ctx.technical.voip_mobile_indicator == VoipMobileIndicator.VOIP and source in (
            CallSource.UNKNOWN,
            CallSource.INBOUND_PSTN,
        ):
            # The transport contradicts the declared source; treat as VoIP.
            self._add(
                out, "voip_transport", 0.5, w.call_source_risk,
                "transport telemetry indicates VoIP origination",
            )

        hist = ctx.history
        if hist.prior_step_up_failures > 0:
            self._add(
                out, "step_up_failures",
                _ramp(float(hist.prior_step_up_failures), 0.0, float(p.step_up_failures_full)),
                w.session_step_up_failures,
                f"{hist.prior_step_up_failures} failed step-up verification(s) this session",
            )
        if hist.prior_escalations > 0:
            self._add(
                out, "prior_escalations",
                _ramp(float(hist.prior_escalations), 0.0, float(p.escalations_full)),
                w.session_prior_escalations,
                f"{hist.prior_escalations} prior escalation(s) for this identity",
            )

    def _score_language(self, out: List[RiskContribution], belief: VoiceBelief, ctx: ContextVector) -> None:
        """Score a mismatch between the declared and the observed call language.

        Not inherently suspicious - VoiceShield is explicitly multilingual and
        code-switching is normal - so the weight is small. It matters only as a
        corroborating signal alongside stronger evidence.
        """
        declared = (ctx.language or "UNKNOWN").upper()
        if declared == "UNKNOWN":
            return
        if belief.switch_damping_events:
            self._add(
                out, "language_switch", 1.0, self.config.weights.language_switch,
                f"language switching observed on a call declared as {declared}",
            )

    # --- transaction context -------------------------------------------------

    def _score_transaction(self, out: List[RiskContribution], ctx: ContextVector) -> None:
        w = self.config.weights
        p = self.config.params
        txn = ctx.transaction

        if txn.amount is not None:
            amount = float(txn.amount) if isinstance(txn.amount, Decimal) else float(txn.amount)
            self._add(
                out, "transaction_value", _log_amount_strength(amount, p.amount_low, p.amount_high),
                w.transaction_value,
                f"transaction value {amount:,.2f} {txn.currency or ''}".strip(),
            )

        if txn.beneficiary_novelty == BeneficiaryNovelty.NEW:
            self._add(
                out, "beneficiary_new", 1.0, w.beneficiary_new,
                "funds directed to a beneficiary never used before",
            )

        if txn.velocity is not None and txn.velocity > 1.0:
            self._add(
                out, "transaction_velocity", _ramp(txn.velocity, 1.0, p.velocity_full),
                w.transaction_velocity,
                f"transaction velocity {txn.velocity:.2f}x the customary rate",
            )

        if txn.historical_deviation is not None and txn.historical_deviation > 0.0:
            self._add(
                out, "historical_deviation", _ramp(txn.historical_deviation, 0.0, p.deviation_full),
                w.historical_deviation,
                f"request deviates {txn.historical_deviation:.2f} sigma from this customer's history",
            )

        if txn.sensitive_action:
            self._add(
                out, "sensitive_action", 1.0, w.sensitive_action,
                f"request classified as the sensitive action {txn.sensitive_action}",
            )

    # --- behavioural / security context --------------------------------------

    def _score_behaviour(self, out: List[RiskContribution], ctx: ContextVector) -> None:
        w = self.config.weights
        beh = ctx.behaviour

        for flag, factor, weight, detail in (
            (beh.urgency, "urgency", w.urgency, "caller applied time pressure to the request"),
            (beh.secrecy, "secrecy", w.secrecy, "caller asked that the request be kept confidential"),
            (beh.callback_refusal, "callback_refusal", w.callback_refusal,
             "caller declined verification by callback to a number on record"),
            (beh.verification_bypass, "verification_bypass", w.verification_bypass,
             "caller attempted to bypass a standard verification step"),
            (beh.unusual_request, "unusual_request", w.unusual_request,
             "request is atypical for this customer profile"),
            (beh.prior_fraud_indicator, "prior_fraud_indicator", w.prior_fraud_indicator,
             "a previously confirmed fraud association exists for this identity or number"),
        ):
            if flag is True:
                self._add(out, factor, 1.0, weight, detail)

        if beh.workflow_state in HIGH_RISK_WORKFLOWS:
            self._add(
                out, "high_risk_workflow", 1.0, w.high_risk_workflow,
                f"session is inside the high-risk workflow {beh.workflow_state.value}",
            )

    # --- public entry point --------------------------------------------------

    def score(self, belief: VoiceBelief, ctx: ContextVector) -> Tuple[float, List[RiskContribution]]:
        """Return ``(risk_score, contributions)`` for one belief/context pair.

        The score is the baseline plus every signed contribution, clamped to
        [0, 1]. Contributions come back ordered by absolute magnitude so the
        caller can take the top N without re-sorting.
        """
        contributions: List[RiskContribution] = []
        self._score_voice(contributions, belief)
        self._score_call_context(contributions, ctx)
        self._score_language(contributions, belief, ctx)
        self._score_transaction(contributions, ctx)
        self._score_behaviour(contributions, ctx)

        raw = self.config.params.baseline + sum(c.points for c in contributions)
        score = _clamp01(raw)

        if raw != score and contributions:
            # Clamping would break the published identity
            # baseline + sum(points) == score, so rescale the contributions to
            # restore it. Without this the explanation would not add up to the
            # number on screen, which is precisely the failure §10.1 warns about.
            _rescale_to(contributions, score - self.config.params.baseline)

        contributions.sort(key=lambda c: abs(c.points), reverse=True)
        return score, contributions


def _log_amount_strength(amount: float, low: float, high: float) -> float:
    """Log-scaled strength for a monetary amount between ``low`` and ``high``.

    Log rather than linear because the difference between 500 and 5,000 matters
    far more than the difference between 400,000 and 405,000; a linear scale
    would leave every ordinary retail transaction indistinguishable near zero.
    """
    if amount <= 0.0:
        return 0.0
    if amount <= low:
        # Still scored, but only faintly - a small transfer is not risk-free.
        return _clamp01(amount / low) * 0.15
    if amount >= high:
        return 1.0
    span = log10(high) - log10(low)
    if span <= 0:
        return 1.0
    return 0.15 + 0.85 * _clamp01((log10(amount) - log10(low)) / span)


def _rescale_to(contributions: List[RiskContribution], target_delta: float) -> None:
    """Proportionally rescale contribution points to sum to ``target_delta``.

    Applied only when clamping bit. Directions are preserved: a mitigating
    factor stays mitigating, it just carries fewer points.
    """
    current = sum(c.points for c in contributions)
    if current == 0.0:
        return
    factor = target_delta / current
    for i, c in enumerate(contributions):
        contributions[i] = c.model_copy(update={"points": c.points * factor})


def band_from_belief(belief: VoiceBelief) -> DecisionBand:
    """Convenience re-export of the belief's own acoustic band."""
    return belief.band
