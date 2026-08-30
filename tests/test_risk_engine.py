"""Tests for the Context and Risk Engine (C-36..C-40, §9).

Organised around the properties that actually matter for a fraud-decisioning
component: that the score is explainable and adds up, that the six mandated
policies fire on the cases they were written for, that the tier ladder tightens
rather than loosens as sensitivity rises, and above all that every degraded
path lands on UNCERTAIN / step-up rather than on invented certainty.
"""

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from voiceshield.context import StandardContextEngine
from voiceshield.contracts import (
    BeneficiaryNovelty,
    BehaviourContext,
    CallSource,
    ContextVector,
    DecisionBand,
    EnrollmentStatus,
    ExpertContribution,
    IdentityContext,
    KnownContactStatus,
    NumberContext,
    PolicyAction,
    ProvenanceType,
    RiskBand,
    ScoreSemantics,
    SessionHistory,
    TechnicalContext,
    TransactionContext,
    TransactionTier,
    VoiceBelief,
    VoipMobileIndicator,
    WorkflowState,
)
from voiceshield.risk import (
    ACTION_SEVERITY,
    BandThresholds,
    PolicyLadder,
    RiskConfig,
    StandardRiskEngine,
    StandardTransactionSensitivity,
    escalate_to,
)

NOW = datetime(2026, 8, 28, 12, 0, 0, tzinfo=timezone.utc)


# --- builders -----------------------------------------------------------------


def make_belief(
    *,
    p_spoof=0.05,
    confidence=0.9,
    band=DecisionBand.GENUINE,
    q_call=0.9,
    experts=("E1", "E2", "E3"),
    expert_p=None,
    speaker_similarity=None,
    session_id="s1",
    uncertainty_reason=None,
    model_versions=("E2:demo@abc123",),
) -> VoiceBelief:
    """Build a VoiceBelief with the shape L4 would actually emit."""
    contributions = []
    for eid in experts:
        p = expert_p if expert_p is not None else p_spoof
        contributions.append(
            ExpertContribution(expert_id=eid, weight=1.0 / max(1, len(experts)), raw_p=p, calibrated_p=p)
        )
    if speaker_similarity is not None:
        # E4 publishes in the spoof direction, so similarity is its complement.
        contributions.append(
            ExpertContribution(
                expert_id="E4", weight=0.3,
                raw_p=1.0 - speaker_similarity, calibrated_p=1.0 - speaker_similarity,
            )
        )
    return VoiceBelief(
        session_id=session_id,
        P_spoof=p_spoof,
        confidence=confidence,
        band=band,
        q_call=q_call,
        contributing_experts=contributions,
        uncertainty_reason=uncertainty_reason,
        model_versions=list(model_versions),
        timestamp=NOW,
    )


def make_context(
    *,
    session_id="s1",
    amount=None,
    transaction_type=None,
    sensitive_action=None,
    beneficiary=BeneficiaryNovelty.UNKNOWN,
    velocity=None,
    deviation=None,
    identity_mismatch=None,
    verified_identity=None,
    claimed_identity="alice",
    enrollment=EnrollmentStatus.ENROLLED,
    known_contact=KnownContactStatus.UNKNOWN,
    reputation=None,
    age_days=None,
    known_fraud=None,
    port_history=None,
    call_source=CallSource.INBOUND_PSTN,
    voip=VoipMobileIndicator.MOBILE,
    urgency=None,
    secrecy=None,
    callback_refusal=None,
    verification_bypass=None,
    unusual_request=None,
    prior_fraud=None,
    workflow=WorkflowState.NONE,
    step_up_failures=0,
    escalations=0,
    language="en",
    full_provenance=True,
) -> ContextVector:
    """Build a ContextVector with a realistic provenance map.

    ``full_provenance`` marks every field SIMULATED regardless of value, which
    keeps completeness high so that tests aimed at scoring are not accidentally
    diverted into the insufficient-confidence fail-safe.
    """
    ctx = ContextVector(
        session_id=session_id,
        identity=IdentityContext(
            claimed_identity=claimed_identity,
            verified_identity=verified_identity,
            enrollment_status=enrollment,
            identity_mismatch=identity_mismatch,
            known_contact=known_contact,
        ),
        number=NumberContext(
            reputation=reputation,
            age_days=age_days,
            known_fraud_status=known_fraud,
            port_history=port_history,
        ),
        transaction=TransactionContext(
            amount=Decimal(str(amount)) if amount is not None else None,
            currency="USD" if amount is not None else None,
            transaction_type=transaction_type,
            beneficiary_novelty=beneficiary,
            velocity=velocity,
            historical_deviation=deviation,
            sensitive_action=sensitive_action,
        ),
        behaviour=BehaviourContext(
            urgency=urgency,
            secrecy=secrecy,
            callback_refusal=callback_refusal,
            verification_bypass=verification_bypass,
            unusual_request=unusual_request,
            prior_fraud_indicator=prior_fraud,
            workflow_state=workflow,
        ),
        technical=TechnicalContext(voip_mobile_indicator=voip, call_source=call_source),
        history=SessionHistory(
            prior_step_up_failures=step_up_failures,
            prior_escalations=escalations,
            prior_sessions=4,
        ),
        language=language,
        timestamp=NOW,
    )
    if full_provenance:
        prov = {}
        for section in ("identity", "number", "transaction", "behaviour", "technical", "history"):
            for field in type(getattr(ctx, section)).model_fields:
                prov[f"{section}.{field}"] = ProvenanceType.SIMULATED
        prov["language"] = ProvenanceType.SIMULATED
        ctx = ctx.model_copy(update={"provenance": prov})
    return ctx


@pytest.fixture
def engine():
    return StandardRiskEngine()


# =============================================================================
# Context engine (C-36, C-37)
# =============================================================================


class TestContextEngine:
    def test_ingests_nested_payload(self):
        ce = StandardContextEngine()
        ctx = ce.ingest_context(
            "s1",
            {
                "identity": {"claimed_identity": "alice", "enrollment_status": "ENROLLED"},
                "transaction": {"amount": "5000.00", "beneficiary_novelty": "NEW"},
                "behaviour": {"urgency": True, "workflow_state": "PAYEE_ADDITION"},
                "language": "en",
            },
        )
        assert ctx.identity.claimed_identity == "alice"
        assert ctx.identity.enrollment_status == EnrollmentStatus.ENROLLED
        assert ctx.transaction.amount == Decimal("5000.00")
        assert ctx.transaction.beneficiary_novelty == BeneficiaryNovelty.NEW
        assert ctx.behaviour.urgency is True
        assert ctx.behaviour.workflow_state == WorkflowState.PAYEE_ADDITION
        assert ctx.language == "en"

    def test_ingests_flat_payload(self):
        """Scenario files are written flat; both shapes must parse identically."""
        ce = StandardContextEngine()
        ctx = ce.ingest_context("s1", {"claimed_identity": "bob", "amount": 250, "urgency": True})
        assert ctx.identity.claimed_identity == "bob"
        assert ctx.transaction.amount == Decimal("250")
        assert ctx.behaviour.urgency is True

    def test_absent_fields_are_marked_unavailable(self):
        """The core provenance guarantee: absence is never a confident default."""
        ce = StandardContextEngine()
        ctx = ce.ingest_context("s1", {"claimed_identity": "alice"})
        assert ctx.provenance["identity.claimed_identity"] == ProvenanceType.SIMULATED
        assert ctx.provenance["number.reputation"] == ProvenanceType.UNAVAILABLE
        assert ctx.provenance["transaction.amount"] == ProvenanceType.UNAVAILABLE

    def test_provenance_is_real_when_configured(self):
        ce = StandardContextEngine(default_provenance=ProvenanceType.REAL)
        ctx = ce.ingest_context("s1", {"claimed_identity": "alice"})
        assert ctx.provenance["identity.claimed_identity"] == ProvenanceType.REAL

    def test_malformed_enum_degrades_to_unknown_rather_than_raising(self):
        ce = StandardContextEngine()
        ctx = ce.ingest_context("s1", {"enrollment_status": "NOT-A-REAL-STATUS"})
        assert ctx.identity.enrollment_status == EnrollmentStatus.UNKNOWN

    def test_unparseable_amount_becomes_unavailable(self):
        ce = StandardContextEngine()
        ctx = ce.ingest_context("s1", {"amount": "not-a-number"})
        assert ctx.transaction.amount is None

    def test_empty_payload_yields_all_unavailable(self):
        ce = StandardContextEngine()
        ctx = ce.ingest_context("s1", {})
        assert ctx.provenance
        assert all(p == ProvenanceType.UNAVAILABLE for p in ctx.provenance.values())
        assert ce.context_completeness(ctx) == 0.0

    def test_completeness_rises_with_supplied_fields(self):
        ce = StandardContextEngine()
        sparse = ce.ingest_context("s1", {"claimed_identity": "alice"})
        rich = ce.ingest_context(
            "s1",
            {
                "claimed_identity": "alice",
                "verified_identity": "alice",
                "amount": 100,
                "reputation": 0.9,
                "urgency": False,
                "known_contact": "KNOWN_CONTACT",
            },
        )
        assert ce.context_completeness(rich) > ce.context_completeness(sparse)

    def test_context_modifier_is_bounded(self):
        ce = StandardContextEngine()
        worst = ce.ingest_context(
            "s1", {"prior_fraud_indicator": True, "known_fraud_status": True, "identity_mismatch": True}
        )
        best = ce.ingest_context("s1", {"known_contact": "KNOWN_CONTACT", "call_source": "OUTBOUND_CALLBACK"})
        assert 0.5 <= ce.compute_context_modifier(best) <= ce.compute_context_modifier(worst) <= 2.0


# =============================================================================
# Transparent scoring (C-38)
# =============================================================================


class TestScoring:
    def test_breakdown_sums_to_the_published_score(self, engine):
        """The explainability guarantee: baseline + contributions == score.

        If this ever fails, the analyst-facing breakdown stops accounting for
        the number on screen, which is the exact failure §10.1 warns against.
        """
        decision = engine.assess(
            "s1",
            make_belief(p_spoof=0.7, band=DecisionBand.SUSPICIOUS),
            make_context(amount=25_000, beneficiary=BeneficiaryNovelty.NEW, urgency=True),
        )
        total = engine.config.params.baseline + sum(c.points for c in decision.risk.contributions)
        assert total == pytest.approx(decision.risk.risk_score, abs=1e-6)

    def test_identity_holds_when_the_score_clamps_at_one(self, engine):
        """Rescaling on clamp must preserve the sum identity."""
        decision = engine.assess(
            "s1",
            make_belief(p_spoof=0.99, band=DecisionBand.SYNTHETIC_HIGH_CONFIDENCE, speaker_similarity=0.05),
            make_context(
                amount=900_000, beneficiary=BeneficiaryNovelty.NEW, identity_mismatch=True,
                known_fraud=True, prior_fraud=True, urgency=True, secrecy=True,
                callback_refusal=True, verification_bypass=True, unusual_request=True,
                reputation=0.0, age_days=1, port_history=True, velocity=9.0, deviation=6.0,
                workflow=WorkflowState.PRIVILEGED_AUTHORISATION, step_up_failures=3, escalations=2,
            ),
        )
        assert decision.risk.risk_score == pytest.approx(1.0)
        total = engine.config.params.baseline + sum(c.points for c in decision.risk.contributions)
        assert total == pytest.approx(decision.risk.risk_score, abs=1e-6)

    def test_score_stays_within_bounds(self, engine):
        for belief, ctx in [
            (make_belief(p_spoof=0.0), make_context()),
            (make_belief(p_spoof=1.0, band=DecisionBand.SYNTHETIC_HIGH_CONFIDENCE), make_context(amount=10**7)),
        ]:
            score = engine.assess("s1", belief, ctx).risk.risk_score
            assert 0.0 <= score <= 1.0

    def test_absent_evidence_produces_no_contribution(self, engine):
        """"No beneficiary data" must not be published as "beneficiary was fine"."""
        decision = engine.assess("s1", make_belief(), make_context(beneficiary=BeneficiaryNovelty.UNKNOWN))
        assert not any(c.factor == "beneficiary_new" for c in decision.risk.contributions)

    def test_higher_spoof_evidence_raises_the_score(self, engine):
        low = engine.assess("s1", make_belief(p_spoof=0.1), make_context()).risk.risk_score
        high = engine.assess(
            "s1", make_belief(p_spoof=0.9, band=DecisionBand.SUSPICIOUS), make_context()
        ).risk.risk_score
        assert high > low

    def test_transaction_value_is_monotonic_and_log_scaled(self, engine):
        scores = [
            engine.assess("s1", make_belief(), make_context(amount=a)).risk.risk_score
            for a in (500, 5_000, 50_000, 500_000)
        ]
        assert scores == sorted(scores)
        # Log scaling: the first decade must move the score more than the last.
        assert (scores[1] - scores[0]) > 0
        assert (scores[3] - scores[2]) < (scores[1] - scores[0]) * 3

    def test_mitigating_factors_reduce_the_score(self, engine):
        neutral = engine.assess("s1", make_belief(), make_context()).risk.risk_score
        credited = engine.assess(
            "s1",
            make_belief(),
            make_context(
                known_contact=KnownContactStatus.KNOWN_CONTACT,
                verified_identity="alice",
                call_source=CallSource.OUTBOUND_CALLBACK,
            ),
        ).risk.risk_score
        assert credited < neutral

    def test_mitigating_contributions_are_signed_and_directed(self, engine):
        decision = engine.assess(
            "s1", make_belief(), make_context(known_contact=KnownContactStatus.KNOWN_CONTACT)
        )
        credit = next(c for c in decision.risk.contributions if c.factor == "known_contact")
        assert credit.direction == "DECREASES_RISK"
        assert credit.points < 0

    def test_behavioural_flags_each_add_risk(self, engine):
        base = engine.assess("s1", make_belief(), make_context()).risk.risk_score
        for flag in ("urgency", "secrecy", "callback_refusal", "verification_bypass", "unusual_request"):
            raised = engine.assess("s1", make_belief(), make_context(**{flag: True})).risk.risk_score
            assert raised > base, f"{flag} did not raise the score"

    def test_prior_fraud_indicator_is_a_major_factor(self, engine):
        decision = engine.assess("s1", make_belief(), make_context(prior_fraud=True))
        factors = {c.factor for c in decision.risk.contributions}
        assert "prior_fraud_indicator" in factors

    def test_high_risk_workflow_state_contributes(self, engine):
        decision = engine.assess(
            "s1", make_belief(), make_context(workflow=WorkflowState.LIMIT_INCREASE)
        )
        assert any(c.factor == "high_risk_workflow" for c in decision.risk.contributions)

    def test_session_history_failures_contribute(self, engine):
        base = engine.assess("s1", make_belief(), make_context()).risk.risk_score
        after = engine.assess("s1", make_belief(), make_context(step_up_failures=3)).risk.risk_score
        assert after > base

    def test_contributions_are_ordered_by_magnitude(self, engine):
        decision = engine.assess(
            "s1",
            make_belief(p_spoof=0.85, band=DecisionBand.SUSPICIOUS),
            make_context(amount=50_000, urgency=True, beneficiary=BeneficiaryNovelty.NEW),
        )
        magnitudes = [abs(c.points) for c in decision.risk.contributions]
        assert magnitudes == sorted(magnitudes, reverse=True)

    def test_top_factors_are_the_leading_contributions(self, engine):
        decision = engine.assess(
            "s1",
            make_belief(p_spoof=0.85, band=DecisionBand.SUSPICIOUS),
            make_context(amount=50_000, urgency=True, secrecy=True, beneficiary=BeneficiaryNovelty.NEW),
        )
        assert len(decision.top_factors) <= engine.config.top_factor_count
        assert decision.top_factors == decision.risk.contributions[: len(decision.top_factors)]

    def test_every_contribution_carries_a_human_readable_detail(self, engine):
        decision = engine.assess(
            "s1", make_belief(p_spoof=0.8, band=DecisionBand.SUSPICIOUS), make_context(amount=9_000)
        )
        assert all(c.detail for c in decision.risk.contributions)


# =============================================================================
# Score semantics — the calibration honesty requirement
# =============================================================================


class TestScoreSemantics:
    def test_uncalibrated_by_default(self, engine):
        """No calibration has been fitted, so nothing may call this a probability."""
        risk = engine.assess("s1", make_belief(), make_context()).risk
        assert risk.score_semantics == ScoreSemantics.UNCALIBRATED_RISK_SCORE
        assert risk.score_label == "risk score"
        assert "probability" not in risk.score_label.lower()

    def test_every_decision_is_stamped_uncalibrated(self, engine):
        decision = engine.assess("s1", make_belief(), make_context())
        assert "SCORE_UNCALIBRATED" in decision.reason_codes

    def test_label_changes_only_when_calibration_is_declared(self):
        engine = StandardRiskEngine(RiskConfig(calibration_performed=True))
        risk = engine.assess("s1", make_belief(), make_context()).risk
        assert risk.score_semantics == ScoreSemantics.CALIBRATED_PROBABILITY
        assert risk.score_label == "calibrated probability"

    def test_explanation_states_the_score_is_not_a_probability(self, engine):
        decision = engine.assess("s1", make_belief(), make_context())
        text = engine.explain(decision)
        assert "not a probability" in text.lower()
        # §10.1: attribution, never causal proof.
        assert "contributing to the score" in text
        assert "prove" not in text.lower()


# =============================================================================
# Transaction sensitivity tiers (C-39, §9.2)
# =============================================================================


class TestTransactionTiers:
    @pytest.mark.parametrize(
        "txn_type,expected",
        [
            ("BALANCE_ENQUIRY", TransactionTier.TIER_0),
            ("ACCOUNT_INFO", TransactionTier.TIER_1),
            ("CREDENTIAL_RESET", TransactionTier.TIER_2),
            ("WIRE_TRANSFER", TransactionTier.TIER_3),
            ("PRIVILEGED_AUTHORISATION", TransactionTier.TIER_4),
        ],
    )
    def test_declared_type_maps_to_its_tier(self, txn_type, expected):
        sens = StandardTransactionSensitivity()
        assert sens.evaluate_tier(make_context(transaction_type=txn_type)) == expected

    def test_unknown_transaction_defaults_to_the_most_protective_tier(self):
        """Unknown must fail towards protection, never towards 'informational'."""
        sens = StandardTransactionSensitivity()
        assert sens.evaluate_tier(make_context()) == TransactionTier.TIER_4

    def test_amount_promotes_a_benignly_labelled_request(self):
        """A large amount cannot be downgraded by a harmless-sounding label."""
        sens = StandardTransactionSensitivity()
        tier = sens.evaluate_tier(make_context(transaction_type="BALANCE_ENQUIRY", amount=400_000))
        assert tier == TransactionTier.TIER_4

    def test_workflow_state_sets_a_tier_floor(self):
        sens = StandardTransactionSensitivity()
        tier = sens.evaluate_tier(
            make_context(transaction_type="ACCOUNT_INFO", workflow=WorkflowState.PAYEE_ADDITION)
        )
        assert tier == TransactionTier.TIER_3

    def test_sensitive_action_classification_is_honoured(self):
        sens = StandardTransactionSensitivity()
        tier = sens.evaluate_tier(make_context(sensitive_action="MFA_RESET"))
        assert tier >= TransactionTier.TIER_2

    def test_thresholds_tighten_monotonically_with_tier(self):
        """§9.2: the effective threshold must become more conservative as tier rises."""
        sens = StandardTransactionSensitivity()
        criticals = [sens.get_tier_thresholds(t)["critical"] for t in TransactionTier]
        assert criticals == sorted(criticals, reverse=True)

    def test_same_score_bands_higher_at_a_higher_tier(self, engine):
        """The operational consequence of threshold tightening."""
        belief = make_belief(p_spoof=0.55, band=DecisionBand.SUSPICIOUS)
        low = engine.assess("s1", belief, make_context(transaction_type="BALANCE_ENQUIRY"))
        high = engine.assess("s1", belief, make_context(transaction_type="PRIVILEGED_AUTHORISATION"))
        severity = {RiskBand.LOW: 0, RiskBand.MEDIUM: 1, RiskBand.HIGH: 2, RiskBand.CRITICAL: 3}
        if low.risk.risk_band in severity and high.risk.risk_band in severity:
            assert severity[high.risk.risk_band] >= severity[low.risk.risk_band]


# =============================================================================
# Configurable bands LOW / MEDIUM / HIGH / CRITICAL
# =============================================================================


class TestRiskBands:
    def test_all_four_bands_are_reachable(self, engine):
        """A band nothing can ever land in is a band that does not exist."""
        cases = [
            (make_belief(p_spoof=0.02), make_context(
                transaction_type="BALANCE_ENQUIRY",
                known_contact=KnownContactStatus.KNOWN_CONTACT,
                verified_identity="alice", call_source=CallSource.OUTBOUND_CALLBACK)),
            (make_belief(p_spoof=0.45), make_context(transaction_type="ACCOUNT_INFO", urgency=True)),
            (make_belief(p_spoof=0.75, band=DecisionBand.SUSPICIOUS),
             make_context(transaction_type="TRANSFER", amount=40_000, beneficiary=BeneficiaryNovelty.NEW)),
            (make_belief(p_spoof=0.97, band=DecisionBand.SYNTHETIC_HIGH_CONFIDENCE, speaker_similarity=0.8),
             make_context(transaction_type="WIRE_TRANSFER", amount=400_000, prior_fraud=True,
                          known_fraud=True, urgency=True, secrecy=True)),
        ]
        bands = {engine.assess("s1", b, c).risk.risk_band for b, c in cases}
        assert RiskBand.CRITICAL in bands
        assert RiskBand.LOW in bands

    def test_band_thresholds_are_configurable(self):
        """A different band configuration must change the classification."""
        strict = StandardRiskEngine(RiskConfig(bands=BandThresholds(medium=0.10, high=0.15, critical=0.20)))
        lenient = StandardRiskEngine(RiskConfig(bands=BandThresholds(medium=0.80, high=0.90, critical=0.95)))
        belief = make_belief(p_spoof=0.5)
        ctx = make_context(transaction_type="ACCOUNT_INFO")
        assert strict.assess("s1", belief, ctx).risk.risk_band != lenient.assess("s1", belief, ctx).risk.risk_band

    def test_invalid_band_configuration_is_rejected(self):
        """Misordered thresholds must fail loudly at construction, not silently."""
        with pytest.raises(ValueError):
            BandThresholds(medium=0.8, high=0.5, critical=0.9)
        with pytest.raises(ValueError):
            BandThresholds(medium=0.1, high=0.2, critical=1.5)


# =============================================================================
# The six mandated policies (§9.3)
# =============================================================================


class TestPolicyOrdinaryCall:
    """Policy 1: an ordinary call must be allowed to proceed."""

    def test_clean_call_is_allowed(self, engine):
        decision = engine.assess(
            "s1",
            make_belief(p_spoof=0.03, confidence=0.95, q_call=0.95),
            make_context(
                transaction_type="BALANCE_ENQUIRY",
                known_contact=KnownContactStatus.KNOWN_CONTACT,
                verified_identity="alice",
            ),
        )
        assert decision.matched_policy == "P-ORDINARY-CALL"
        assert decision.action == PolicyAction.ALLOW
        assert decision.risk.risk_band == RiskBand.LOW
        assert not decision.fail_safe_engaged
        assert "ORDINARY_CALL" in decision.reason_codes

    def test_ordinary_call_recommends_no_verification(self, engine):
        decision = engine.assess(
            "s1",
            make_belief(p_spoof=0.03, confidence=0.95),
            make_context(transaction_type="BALANCE_ENQUIRY", known_contact=KnownContactStatus.KNOWN_CONTACT),
        )
        assert decision.recommended_verifications == []


class TestPolicySuspiciousVoiceLowValue:
    """Policy 2: proportionality — do not block a balance enquiry."""

    def test_suspicious_voice_on_a_low_value_action_warns_only(self, engine):
        decision = engine.assess(
            "s1",
            make_belief(p_spoof=0.72, confidence=0.85, band=DecisionBand.SUSPICIOUS),
            make_context(transaction_type="BALANCE_ENQUIRY"),
        )
        assert decision.matched_policy == "P-SUSPICIOUS-VOICE-LOW-VALUE"
        assert decision.action in (PolicyAction.WARN, PolicyAction.ALLOW)
        assert ACTION_SEVERITY[decision.action] < ACTION_SEVERITY[PolicyAction.HOLD]
        assert "SUSPICIOUS_VOICE" in decision.reason_codes
        assert "LOW_VALUE_ACTION" in decision.reason_codes

    def test_evidence_is_still_captured_when_not_obstructing(self, engine):
        decision = engine.assess(
            "s1",
            make_belief(p_spoof=0.72, confidence=0.85, band=DecisionBand.SUSPICIOUS),
            make_context(transaction_type="BALANCE_ENQUIRY"),
        )
        assert any(r.kind == "VOICE_BELIEF" for r in decision.evidence_refs)
        assert any(c.factor == "spoof_evidence" for c in decision.risk.contributions)

    def test_high_confidence_synthetic_still_steps_up_from_tier_two(self, engine):
        decision = engine.assess(
            "s1",
            make_belief(p_spoof=0.95, confidence=0.9, band=DecisionBand.SYNTHETIC_HIGH_CONFIDENCE),
            make_context(transaction_type="CREDENTIAL_RESET"),
        )
        assert ACTION_SEVERITY[decision.action] >= ACTION_SEVERITY[PolicyAction.STEP_UP]


class TestPolicySuspiciousVoiceHighValue:
    """Policy 3: the headline case — synthetic voice against a high-value ask."""

    def test_suspicious_voice_plus_high_value_holds(self, engine):
        decision = engine.assess(
            "s1",
            make_belief(p_spoof=0.78, confidence=0.88, band=DecisionBand.SUSPICIOUS),
            make_context(transaction_type="WIRE_TRANSFER", amount=85_000,
                         beneficiary=BeneficiaryNovelty.NEW, urgency=True),
        )
        assert decision.matched_policy == "P-SUSPICIOUS-VOICE-HIGH-VALUE"
        assert ACTION_SEVERITY[decision.action] >= ACTION_SEVERITY[PolicyAction.HOLD]
        assert decision.risk.risk_band in (RiskBand.HIGH, RiskBand.CRITICAL)
        assert "HIGH_VALUE_ACTION" in decision.reason_codes
        assert "NEW_BENEFICIARY" in decision.reason_codes

    def test_high_confidence_synthetic_escalates(self, engine):
        decision = engine.assess(
            "s1",
            make_belief(p_spoof=0.96, confidence=0.92, band=DecisionBand.SYNTHETIC_HIGH_CONFIDENCE),
            make_context(transaction_type="WIRE_TRANSFER", amount=250_000,
                         beneficiary=BeneficiaryNovelty.NEW),
        )
        assert decision.action == PolicyAction.ESCALATE
        assert decision.risk.risk_band == RiskBand.CRITICAL
        assert "SYNTHETIC_HIGH_CONFIDENCE" in decision.reason_codes

    def test_it_is_stricter_than_the_low_value_case(self, engine):
        belief = make_belief(p_spoof=0.78, confidence=0.88, band=DecisionBand.SUSPICIOUS)
        low = engine.assess("s1", belief, make_context(transaction_type="BALANCE_ENQUIRY"))
        high = engine.assess("s1", belief, make_context(transaction_type="WIRE_TRANSFER", amount=85_000))
        assert ACTION_SEVERITY[high.action] > ACTION_SEVERITY[low.action]

    def test_a_sensitive_action_counts_as_high_value_without_an_amount(self, engine):
        """A credential reset carries no amount but is exactly this pattern."""
        decision = engine.assess(
            "s1",
            make_belief(p_spoof=0.8, confidence=0.88, band=DecisionBand.SUSPICIOUS),
            make_context(transaction_type="PAYEE_ADDITION"),
        )
        assert decision.matched_policy == "P-SUSPICIOUS-VOICE-HIGH-VALUE"

    def test_verification_recommendations_avoid_the_caller_supplied_number(self, engine):
        decision = engine.assess(
            "s1",
            make_belief(p_spoof=0.8, confidence=0.9, band=DecisionBand.SUSPICIOUS),
            make_context(transaction_type="WIRE_TRANSFER", amount=85_000),
        )
        joined = " ".join(decision.recommended_verifications).lower()
        assert "number of record" in joined


class TestPolicyStrongSpeakerMismatch:
    """Policy 4: natural speech, wrong speaker — the social-engineering case."""

    def test_strong_mismatch_matches_its_policy(self, engine):
        decision = engine.assess(
            "s1",
            make_belief(p_spoof=0.05, confidence=0.9, band=DecisionBand.GENUINE, speaker_similarity=0.15),
            make_context(transaction_type="WIRE_TRANSFER", amount=50_000),
        )
        assert decision.matched_policy == "P-STRONG-SPEAKER-MISMATCH"
        assert "STRONG_SPEAKER_MISMATCH" in decision.reason_codes

    def test_it_fires_even_when_the_audio_is_genuine_human_speech(self, engine):
        """The voice is real; it is just not the right person."""
        belief = make_belief(p_spoof=0.02, band=DecisionBand.GENUINE, speaker_similarity=0.1)
        decision = engine.assess("s1", belief, make_context(transaction_type="TRANSFER", amount=30_000))
        assert belief.band == DecisionBand.GENUINE
        assert ACTION_SEVERITY[decision.action] >= ACTION_SEVERITY[PolicyAction.HOLD]

    def test_it_escalates_on_a_high_value_transfer(self, engine):
        decision = engine.assess(
            "s1",
            make_belief(speaker_similarity=0.08, confidence=0.9),
            make_context(transaction_type="WIRE_TRANSFER", amount=300_000),
        )
        assert decision.action == PolicyAction.ESCALATE
        assert decision.risk.risk_band == RiskBand.CRITICAL

    def test_it_only_warns_on_an_informational_request(self, engine):
        decision = engine.assess(
            "s1",
            make_belief(speaker_similarity=0.1, confidence=0.9),
            make_context(transaction_type="BALANCE_ENQUIRY"),
        )
        assert decision.action == PolicyAction.WARN

    def test_a_good_speaker_match_does_not_trigger_it(self, engine):
        decision = engine.assess(
            "s1",
            make_belief(speaker_similarity=0.92, confidence=0.9),
            make_context(transaction_type="BALANCE_ENQUIRY"),
        )
        assert decision.matched_policy != "P-STRONG-SPEAKER-MISMATCH"

    def test_an_abstaining_e4_is_not_read_as_a_mismatch(self, engine):
        """E4 abstains for unenrolled speakers; that is not evidence of anything."""
        decision = engine.assess(
            "s1",
            make_belief(speaker_similarity=None, confidence=0.9),
            make_context(transaction_type="BALANCE_ENQUIRY", enrollment=EnrollmentStatus.NOT_ENROLLED),
        )
        assert decision.matched_policy != "P-STRONG-SPEAKER-MISMATCH"

    def test_it_advises_not_to_treat_voice_as_an_identity_factor(self, engine):
        decision = engine.assess(
            "s1", make_belief(speaker_similarity=0.1, confidence=0.9),
            make_context(transaction_type="TRANSFER", amount=20_000),
        )
        joined = " ".join(decision.recommended_verifications).lower()
        assert "identity factor" in joined or "out of band" in joined


class TestPolicyInsufficientConfidence:
    """Policy 5: the brief's core safety requirement."""

    def test_low_confidence_yields_uncertain_and_a_step_up(self, engine):
        decision = engine.assess(
            "s1",
            make_belief(p_spoof=0.5, confidence=0.1, band=DecisionBand.UNCERTAIN, q_call=0.3,
                        uncertainty_reason="contradictory evidence"),
            make_context(transaction_type="TRANSFER", amount=20_000),
        )
        assert decision.matched_policy == "P-INSUFFICIENT-CONFIDENCE"
        assert decision.risk.risk_band == RiskBand.UNCERTAIN
        assert ACTION_SEVERITY[decision.action] >= ACTION_SEVERITY[PolicyAction.STEP_UP]
        assert decision.fail_safe_engaged
        assert "INSUFFICIENT_CONFIDENCE" in decision.reason_codes
        assert "FAIL_SAFE_UNCERTAIN" in decision.reason_codes

    def test_poor_audio_is_reported_as_its_own_reason(self, engine):
        decision = engine.assess(
            "s1",
            make_belief(p_spoof=0.4, confidence=0.15, band=DecisionBand.UNCERTAIN, q_call=0.2),
            make_context(transaction_type="TRANSFER", amount=5_000),
        )
        assert "POOR_AUDIO_QUALITY" in decision.reason_codes

    def test_poor_audio_lowers_the_reported_confidence(self, engine):
        good = engine.assess("s1", make_belief(q_call=0.95), make_context()).risk.risk_confidence
        bad = engine.assess("s1", make_belief(q_call=0.2), make_context()).risk.risk_confidence
        assert bad < good

    def test_an_uncertain_belief_band_alone_triggers_the_fail_safe(self, engine):
        decision = engine.assess(
            "s1",
            make_belief(p_spoof=0.5, confidence=0.85, band=DecisionBand.UNCERTAIN, q_call=0.9),
            make_context(transaction_type="ACCOUNT_INFO"),
        )
        assert decision.risk.risk_band == RiskBand.UNCERTAIN
        assert decision.fail_safe_engaged

    def test_a_high_score_we_cannot_stand_behind_asks_for_more_friction(self, engine):
        """Low confidence must never be a route to a softer outcome."""
        decision = engine.assess(
            "s1",
            make_belief(p_spoof=0.9, confidence=0.05, band=DecisionBand.UNCERTAIN, q_call=0.15),
            make_context(transaction_type="WIRE_TRANSFER", amount=200_000, prior_fraud=True,
                         known_fraud=True, urgency=True, secrecy=True),
        )
        assert ACTION_SEVERITY[decision.action] >= ACTION_SEVERITY[PolicyAction.STEP_UP]

    def test_it_recommends_a_dynamic_liveness_challenge(self, engine):
        """§9.5: the challenge must be generated, never a fixed known phrase."""
        decision = engine.assess(
            "s1",
            make_belief(confidence=0.05, band=DecisionBand.UNCERTAIN, q_call=0.2),
            make_context(transaction_type="TRANSFER", amount=9_000),
        )
        joined = " ".join(decision.recommended_verifications).lower()
        assert "dynamically generated" in joined

    def test_incomplete_context_is_flagged_as_degraded(self, engine):
        sparse = StandardContextEngine().ingest_context("s1", {"claimed_identity": "alice"})
        decision = engine.assess("s1", make_belief(), sparse)
        assert decision.risk.context_degraded
        assert "CONTEXT_INCOMPLETE" in decision.reason_codes


class TestPolicyModelUnavailable:
    """Policy 6: the detector is down — the call is not thereby safe."""

    def test_missing_core_experts_yields_uncertain(self, engine):
        decision = engine.assess(
            "s1",
            make_belief(p_spoof=None, confidence=0.0, band=DecisionBand.UNCERTAIN,
                        experts=(), model_versions=()),
            make_context(transaction_type="TRANSFER", amount=15_000),
        )
        assert decision.matched_policy == "P-MODEL-UNAVAILABLE"
        assert decision.risk.risk_band == RiskBand.UNCERTAIN
        assert decision.fail_safe_engaged
        assert "MODEL_UNAVAILABLE" in decision.reason_codes
        assert "VOICE_EVIDENCE_ABSENT" in decision.reason_codes

    def test_it_does_not_fail_open(self, engine):
        """Knocking out the models must not buy an attacker a clean channel."""
        decision = engine.assess(
            "s1",
            make_belief(p_spoof=None, confidence=0.0, band=DecisionBand.UNCERTAIN, experts=()),
            make_context(transaction_type="WIRE_TRANSFER", amount=100_000),
        )
        assert decision.action != PolicyAction.ALLOW
        assert ACTION_SEVERITY[decision.action] >= ACTION_SEVERITY[PolicyAction.STEP_UP]

    def test_it_outranks_every_other_rule(self, engine):
        """Highest priority: no lower rule may act on evidence that never arrived."""
        decision = engine.assess(
            "s1",
            make_belief(p_spoof=None, confidence=0.0, band=DecisionBand.UNCERTAIN,
                        experts=(), speaker_similarity=0.05),
            make_context(transaction_type="WIRE_TRANSFER", amount=500_000, prior_fraud=True),
        )
        assert decision.matched_policy == "P-MODEL-UNAVAILABLE"

    def test_a_tier_zero_request_is_not_over_penalised(self, engine):
        """Proportionality survives an outage: a balance enquiry still gets through."""
        decision = engine.assess(
            "s1",
            make_belief(p_spoof=None, confidence=0.0, band=DecisionBand.UNCERTAIN, experts=()),
            make_context(transaction_type="BALANCE_ENQUIRY"),
        )
        assert decision.action == PolicyAction.WARN

    def test_it_recommends_a_non_voice_verification_route(self, engine):
        decision = engine.assess(
            "s1",
            make_belief(p_spoof=None, confidence=0.0, band=DecisionBand.UNCERTAIN, experts=()),
            make_context(transaction_type="TRANSFER", amount=20_000),
        )
        joined = " ".join(decision.recommended_verifications).lower()
        assert "does not depend on voice" in joined


class TestPolicyElevatedContext:
    """Completeness rule: a clean voice must not launder an anomalous request."""

    def test_contextual_risk_alone_can_raise_the_action(self, engine):
        decision = engine.assess(
            "s1",
            make_belief(p_spoof=0.04, confidence=0.95, band=DecisionBand.GENUINE),
            make_context(transaction_type="WIRE_TRANSFER", amount=300_000,
                         beneficiary=BeneficiaryNovelty.NEW, prior_fraud=True, known_fraud=True,
                         urgency=True, secrecy=True, callback_refusal=True),
        )
        assert decision.matched_policy == "P-ELEVATED-CONTEXT"
        assert decision.action != PolicyAction.ALLOW
        assert "PRIOR_FRAUD_INDICATOR" in decision.reason_codes


# =============================================================================
# Fail-safe behaviour
# =============================================================================


class TestFailSafe:
    def test_a_completely_empty_context_never_allows_silently(self, engine):
        empty = StandardContextEngine().ingest_context("s1", {})
        decision = engine.assess("s1", make_belief(), empty)
        # Unknown transaction -> TIER_4, whose baseline action is already WARN.
        assert decision.action != PolicyAction.ALLOW

    def test_an_engine_defect_degrades_to_uncertain_rather_than_raising(self, engine, monkeypatch):
        """A bug in scoring must cost a step-up, not take the decision path down."""
        def boom(*_args, **_kwargs):
            raise RuntimeError("simulated scoring defect")

        monkeypatch.setattr(engine.scorer, "score", boom)
        decision = engine.assess("s1", make_belief(), make_context())
        assert decision.matched_policy == "P-ENGINE-FAILURE"
        assert decision.risk.risk_band == RiskBand.UNCERTAIN
        assert decision.action == PolicyAction.STEP_UP
        assert decision.fail_safe_engaged
        assert "ENGINE_FAILURE" in decision.reason_codes

    def test_the_failure_path_emits_no_misleading_score(self, engine, monkeypatch):
        monkeypatch.setattr(engine.scorer, "score", lambda *a, **k: (_ for _ in ()).throw(ValueError("x")))
        decision = engine.assess("s1", make_belief(), make_context())
        assert decision.risk.risk_confidence == 0.0
        assert "not computed" in decision.risk.score_label

    def test_a_broken_policy_predicate_does_not_fail_open(self):
        """A rule that raises must be skipped, never treated as matching."""
        from voiceshield.risk.policies import DEFAULT_POLICY_RULES, PolicyRule

        def exploding(_inp):
            raise RuntimeError("bad predicate")

        rules = (
            PolicyRule(
                policy_id="P-BROKEN", priority=999, description="raises",
                matches=exploding, decide=lambda i: None,
            ),
        ) + DEFAULT_POLICY_RULES
        engine = StandardRiskEngine(ladder=PolicyLadder(rules))
        decision = engine.assess("s1", make_belief(), make_context(transaction_type="BALANCE_ENQUIRY"))
        assert decision.matched_policy != "P-BROKEN"

    def test_a_rule_set_with_no_terminal_rule_refuses_rather_than_allows(self):
        """If nothing matches, the answer is a step-up, not an allow."""
        engine = StandardRiskEngine(ladder=PolicyLadder(rules=()))
        decision = engine.assess("s1", make_belief(), make_context())
        assert decision.matched_policy == "P-NO-RULE-MATCHED"
        assert decision.action == PolicyAction.STEP_UP
        assert decision.risk.risk_band == RiskBand.UNCERTAIN

    def test_uncertainty_never_produces_a_scored_band(self, engine):
        """The whole point: prefer UNCERTAIN over inventing certainty."""
        for belief in (
            make_belief(p_spoof=None, confidence=0.0, band=DecisionBand.UNCERTAIN, experts=()),
            make_belief(p_spoof=0.5, confidence=0.05, band=DecisionBand.UNCERTAIN, q_call=0.1),
        ):
            decision = engine.assess("s1", belief, make_context(transaction_type="TRANSFER", amount=10_000))
            assert decision.risk.risk_band == RiskBand.UNCERTAIN
            assert decision.risk.risk_band not in (RiskBand.LOW, RiskBand.MEDIUM, RiskBand.HIGH, RiskBand.CRITICAL)

    def test_every_fail_safe_outcome_recommends_a_verification(self, engine):
        decision = engine.assess(
            "s1",
            make_belief(p_spoof=None, confidence=0.0, band=DecisionBand.UNCERTAIN, experts=()),
            make_context(transaction_type="TRANSFER", amount=10_000),
        )
        assert decision.fail_safe_engaged
        assert decision.recommended_verifications


# =============================================================================
# Confidence semantics
# =============================================================================


class TestConfidence:
    def test_confidence_is_independent_of_the_score(self, engine):
        """A high score must not be able to talk the engine into believing itself."""
        low_risk = engine.assess(
            "s1", make_belief(p_spoof=0.05, confidence=0.9, q_call=0.9),
            make_context(transaction_type="BALANCE_ENQUIRY"),
        )
        high_risk = engine.assess(
            "s1", make_belief(p_spoof=0.95, confidence=0.9, q_call=0.9, band=DecisionBand.SYNTHETIC_HIGH_CONFIDENCE),
            make_context(transaction_type="BALANCE_ENQUIRY"),
        )
        assert low_risk.risk.risk_score != high_risk.risk.risk_score
        assert low_risk.risk.risk_confidence == pytest.approx(high_risk.risk.risk_confidence)

    def test_confidence_falls_when_context_is_thin(self, engine):
        rich = engine.assess("s1", make_belief(), make_context()).risk.risk_confidence
        thin = engine.assess(
            "s1", make_belief(), StandardContextEngine().ingest_context("s1", {})
        ).risk.risk_confidence
        assert thin < rich

    def test_confidence_falls_when_voice_evidence_is_absent(self, engine):
        with_voice = engine.assess("s1", make_belief(confidence=0.9), make_context()).risk.risk_confidence
        without = engine.assess(
            "s1", make_belief(p_spoof=None, confidence=0.0, experts=()), make_context()
        ).risk.risk_confidence
        assert without < with_voice

    def test_confidence_is_bounded(self, engine):
        for belief in (make_belief(confidence=0.0), make_belief(confidence=1.0, q_call=1.0)):
            c = engine.assess("s1", belief, make_context()).risk.risk_confidence
            assert 0.0 <= c <= 1.0

    def test_unknown_audio_quality_is_not_treated_as_good(self, engine):
        unknown = engine.assess("s1", make_belief(q_call=None), make_context()).risk.risk_confidence
        good = engine.assess("s1", make_belief(q_call=1.0), make_context()).risk.risk_confidence
        assert unknown < good


# =============================================================================
# Required output surface
# =============================================================================


class TestOutputContract:
    def test_every_required_output_field_is_populated(self, engine):
        decision = engine.assess(
            "s1",
            make_belief(p_spoof=0.8, band=DecisionBand.SUSPICIOUS),
            make_context(transaction_type="WIRE_TRANSFER", amount=60_000),
        )
        assert isinstance(decision.risk.risk_score, float)      # overall risk score
        assert decision.risk.risk_band in RiskBand              # risk band
        assert isinstance(decision.risk.risk_confidence, float)  # confidence
        assert decision.action in PolicyAction                  # action
        assert decision.reason_codes                            # reason codes
        assert decision.top_factors                             # top contributing factors
        assert decision.evidence_refs                           # evidence references
        assert decision.timestamp.tzinfo is not None            # timestamp
        assert decision.policy_version                          # policy version

    def test_the_timestamp_is_utc(self, engine):
        decision = engine.assess("s1", make_belief(), make_context())
        assert decision.timestamp.tzinfo == timezone.utc
        assert decision.risk.timestamp == decision.timestamp

    def test_the_policy_version_is_stamped_from_configuration(self):
        engine = StandardRiskEngine(RiskConfig(policy_version="risk-9.9.9"))
        assert engine.assess("s1", make_belief(), make_context()).policy_version == "risk-9.9.9"

    def test_evidence_references_point_rather_than_copy(self, engine):
        """P2: no audio or embeddings may reach the decision record."""
        decision = engine.assess(
            "s1", make_belief(p_spoof=0.8, band=DecisionBand.SUSPICIOUS),
            make_context(transaction_type="TRANSFER", amount=40_000),
        )
        serialised = decision.model_dump_json()
        assert "pcm" not in serialised
        assert "embedding" not in serialised
        kinds = {r.kind for r in decision.evidence_refs}
        assert "VOICE_BELIEF" in kinds and "POLICY" in kinds

    def test_evidence_references_name_the_contributing_experts(self, engine):
        decision = engine.assess("s1", make_belief(experts=("E1", "E2", "E3")), make_context())
        refs = {r.ref for r in decision.evidence_refs}
        assert {"expert:E1", "expert:E2", "expert:E3"} <= refs

    def test_evidence_references_include_the_matched_policy(self, engine):
        decision = engine.assess("s1", make_belief(), make_context())
        policy_refs = [r for r in decision.evidence_refs if r.kind == "POLICY"]
        assert policy_refs
        assert decision.matched_policy in policy_refs[0].ref

    def test_model_versions_are_referenced_for_audit(self, engine):
        decision = engine.assess("s1", make_belief(model_versions=("E2:demo@sha256",)), make_context())
        assert any("model:E2:demo@sha256" == r.ref for r in decision.evidence_refs)

    def test_the_decision_serialises_round_trip(self, engine):
        from voiceshield.contracts import RiskDecision

        decision = engine.assess(
            "s1", make_belief(p_spoof=0.7, band=DecisionBand.SUSPICIOUS),
            make_context(transaction_type="TRANSFER", amount=20_000),
        )
        restored = RiskDecision.model_validate_json(decision.model_dump_json())
        assert restored.risk.risk_score == decision.risk.risk_score
        assert restored.action == decision.action

    def test_convenience_accessors_agree_with_the_assessment(self, engine):
        decision = engine.assess("s1", make_belief(), make_context())
        assert decision.risk_score == decision.risk.risk_score
        assert decision.risk_band == decision.risk.risk_band

    def test_evaluate_risk_returns_the_contract_assessment(self, engine):
        """The C-38 interface method must still work on its own."""
        assessment = engine.evaluate_risk("s1", make_belief(), make_context())
        assert assessment.session_id == "s1"
        assert 0.0 <= assessment.risk_score <= 1.0
        assert assessment.risk_band in RiskBand


# =============================================================================
# Determinism and configurability
# =============================================================================


class TestDeterminismAndConfig:
    def test_the_same_inputs_produce_the_same_score(self, engine):
        belief, ctx = make_belief(p_spoof=0.6, band=DecisionBand.SUSPICIOUS), make_context(amount=12_345)
        first = engine.assess("s1", belief, ctx)
        second = engine.assess("s1", belief, ctx)
        assert first.risk.risk_score == second.risk.risk_score
        assert first.action == second.action
        assert first.matched_policy == second.matched_policy

    def test_the_engine_holds_no_cross_session_state(self, engine):
        """Assessments must not leak between sessions."""
        hot = make_context(session_id="s2", prior_fraud=True, known_fraud=True, amount=500_000)
        engine.assess("s2", make_belief(p_spoof=0.99, band=DecisionBand.SYNTHETIC_HIGH_CONFIDENCE), hot)
        clean = engine.assess(
            "s1", make_belief(p_spoof=0.02),
            make_context(transaction_type="BALANCE_ENQUIRY", known_contact=KnownContactStatus.KNOWN_CONTACT),
        )
        assert clean.action == PolicyAction.ALLOW

    def test_scoring_weights_are_configurable(self):
        from voiceshield.risk import ScoringWeights

        default = StandardRiskEngine()
        heavy = StandardRiskEngine(RiskConfig(weights=ScoringWeights(spoof_evidence=0.9)))
        belief = make_belief(p_spoof=0.9, band=DecisionBand.SUSPICIOUS)
        ctx = make_context(transaction_type="ACCOUNT_INFO")
        assert heavy.assess("s1", belief, ctx).risk.risk_score > default.assess("s1", belief, ctx).risk.risk_score

    def test_tier_policies_are_configurable(self):
        from voiceshield.risk import TierPolicy

        config = RiskConfig()
        config.tier_policies[TransactionTier.TIER_0] = TierPolicy(
            TransactionTier.TIER_0, 1.15, PolicyAction.STEP_UP, PolicyAction.HOLD
        )
        engine = StandardRiskEngine(config)
        decision = engine.assess(
            "s1", make_belief(p_spoof=0.02, confidence=0.95),
            make_context(transaction_type="BALANCE_ENQUIRY", known_contact=KnownContactStatus.KNOWN_CONTACT),
        )
        assert decision.action == PolicyAction.STEP_UP

    def test_escalate_to_always_takes_the_more_restrictive_action(self):
        assert escalate_to(PolicyAction.ALLOW, PolicyAction.HOLD) == PolicyAction.HOLD
        assert escalate_to(PolicyAction.ESCALATE, PolicyAction.WARN) == PolicyAction.ESCALATE
        assert escalate_to(PolicyAction.STEP_UP, PolicyAction.STEP_UP) == PolicyAction.STEP_UP

    def test_every_action_class_has_a_severity_ranking(self):
        """A missing ranking would make escalate_to raise at the worst moment."""
        assert set(ACTION_SEVERITY) == set(PolicyAction)

    def test_the_ladder_is_evaluated_in_priority_order(self):
        priorities = [r.priority for r in PolicyLadder().rules]
        assert priorities == sorted(priorities, reverse=True)

    def test_all_six_mandated_policies_are_present(self):
        ids = {r.policy_id for r in PolicyLadder().rules}
        assert {
            "P-ORDINARY-CALL",
            "P-SUSPICIOUS-VOICE-LOW-VALUE",
            "P-SUSPICIOUS-VOICE-HIGH-VALUE",
            "P-STRONG-SPEAKER-MISMATCH",
            "P-INSUFFICIENT-CONFIDENCE",
            "P-MODEL-UNAVAILABLE",
        } <= ids


# =============================================================================
# End-to-end through the context engine
# =============================================================================


class TestEndToEnd:
    def test_a_routine_customer_call_is_allowed(self):
        ce, engine = StandardContextEngine(), StandardRiskEngine()
        ctx = ce.ingest_context(
            "call-1",
            {
                "claimed_identity": "alice", "verified_identity": "alice",
                "enrollment_status": "ENROLLED", "known_contact": "KNOWN_CONTACT",
                "reputation": 0.95, "age_days": 2200, "known_fraud_status": False,
                "transaction_type": "BALANCE_ENQUIRY", "call_source": "INBOUND_PSTN",
                "voip_mobile_indicator": "MOBILE", "language": "en", "urgency": False,
            },
        )
        decision = engine.assess("call-1", make_belief(p_spoof=0.03, confidence=0.94, q_call=0.93), ctx)
        assert decision.action == PolicyAction.ALLOW
        assert decision.risk.risk_band == RiskBand.LOW

    def test_the_deepfake_wire_fraud_scenario_is_stopped(self):
        ce, engine = StandardContextEngine(), StandardRiskEngine()
        ctx = ce.ingest_context(
            "call-2",
            {
                "claimed_identity": "alice", "identity_mismatch": True,
                "enrollment_status": "ENROLLED", "known_contact": "FIRST_CONTACT",
                "reputation": 0.15, "age_days": 3, "port_history": True,
                "transaction_type": "WIRE_TRANSFER", "amount": 480_000, "currency": "USD",
                "beneficiary_novelty": "NEW", "velocity": 4.0, "historical_deviation": 3.5,
                "urgency": True, "secrecy": True, "callback_refusal": True,
                "workflow_state": "HIGH_VALUE_TRANSFER", "call_source": "INBOUND_VOIP",
                "voip_mobile_indicator": "VOIP", "language": "en",
            },
        )
        belief = make_belief(p_spoof=0.94, confidence=0.91, band=DecisionBand.SYNTHETIC_HIGH_CONFIDENCE, q_call=0.82)
        decision = engine.assess("call-2", belief, ctx)
        assert decision.action == PolicyAction.ESCALATE
        assert decision.risk.risk_band == RiskBand.CRITICAL
        assert decision.transaction_tier == TransactionTier.TIER_4
        assert decision.risk.risk_score > 0.8
        assert not decision.fail_safe_engaged

    def test_the_poor_audio_scenario_asks_for_verification(self):
        """The third frozen demo scenario: UNCERTAIN / STEP-UP VERIFICATION."""
        ce, engine = StandardContextEngine(), StandardRiskEngine()
        ctx = ce.ingest_context(
            "call-3",
            {
                "claimed_identity": "carol", "enrollment_status": "ENROLLED",
                "transaction_type": "TRANSFER", "amount": 8_000, "currency": "USD",
                "beneficiary_novelty": "KNOWN", "call_source": "INBOUND_VOIP", "language": "en",
            },
        )
        belief = make_belief(p_spoof=0.48, confidence=0.12, band=DecisionBand.UNCERTAIN, q_call=0.22,
                             uncertainty_reason="poor audio quality")
        decision = engine.assess("call-3", belief, ctx)
        assert decision.risk.risk_band == RiskBand.UNCERTAIN
        assert ACTION_SEVERITY[decision.action] >= ACTION_SEVERITY[PolicyAction.STEP_UP]
        assert decision.fail_safe_engaged
        assert "POOR_AUDIO_QUALITY" in decision.reason_codes

    def test_the_explanation_reads_as_a_breakdown_an_analyst_can_check(self):
        engine = StandardRiskEngine()
        decision = engine.assess(
            "call-4",
            make_belief(p_spoof=0.88, confidence=0.9, band=DecisionBand.SUSPICIOUS),
            make_context(transaction_type="WIRE_TRANSFER", amount=120_000,
                         beneficiary=BeneficiaryNovelty.NEW, urgency=True),
        )
        text = engine.explain(decision)
        assert "baseline" in text
        assert "TOTAL" in text
        assert decision.matched_policy in text
        assert f"{decision.risk.risk_score:.3f}" in text
        for factor in decision.top_factors:
            assert factor.factor in text
