"""Configurable risk scoring and policy parameters (C-38, C-39, C-40).

Everything the risk engine treats as a tunable lives here, as plain frozen
dataclasses. Nothing in :mod:`voiceshield.risk.scoring` or
:mod:`voiceshield.risk.policies` hard-codes a number that an operator might
reasonably want to change, because a policy whose thresholds are buried in
branching logic cannot be reviewed by the people accountable for it.
"""

import dataclasses
from typing import Dict, Tuple

from voiceshield.contracts import PolicyAction, TransactionTier

#: Version stamped onto every RiskDecision. Bump on any change to weights,
#: band edges, tier mapping or the policy ladder - the evidence record is only
#: defensible if the exact rule set that produced it can be identified.
POLICY_VERSION = "risk-1.0.0"


@dataclasses.dataclass(frozen=True)
class ScoringWeights:
    """Maximum risk points each factor may contribute, on the [0, 1] score scale.

    These are additive contribution ceilings, not probabilities and not model
    coefficients. A factor at full strength adds its full weight; a factor at
    half strength adds half. This is what makes the score explainable: the
    published breakdown sums to the score exactly.
    """

    # --- Voice signals -------------------------------------------------------
    spoof_evidence: float = 0.40
    speaker_mismatch: float = 0.30
    acoustic_evidence: float = 0.10
    prosody_evidence: float = 0.06

    # --- Call context --------------------------------------------------------
    identity_mismatch: float = 0.18
    not_enrolled: float = 0.05
    unknown_contact: float = 0.05
    number_reputation: float = 0.12
    number_known_fraud: float = 0.25
    number_recently_created: float = 0.07
    number_port_history: float = 0.06
    call_source_risk: float = 0.06
    language_switch: float = 0.04
    session_step_up_failures: float = 0.15
    session_prior_escalations: float = 0.10

    # --- Transaction context -------------------------------------------------
    transaction_value: float = 0.20
    beneficiary_new: float = 0.12
    transaction_velocity: float = 0.08
    historical_deviation: float = 0.08
    sensitive_action: float = 0.10

    # --- Behavioural / security context --------------------------------------
    urgency: float = 0.08
    secrecy: float = 0.08
    callback_refusal: float = 0.10
    verification_bypass: float = 0.12
    unusual_request: float = 0.08
    prior_fraud_indicator: float = 0.25
    high_risk_workflow: float = 0.10

    # --- Mitigating factors (negative contributions) -------------------------
    known_contact_credit: float = 0.08
    verified_identity_credit: float = 0.10
    outbound_callback_credit: float = 0.10
    genuine_voice_credit: float = 0.12


@dataclasses.dataclass(frozen=True)
class ScoringParams:
    """Shape parameters for turning raw context values into factor strengths."""

    #: Baseline score for a call with no evidence either way. Not zero: an
    #: unverified inbound caller asking for something is not risk-free.
    baseline: float = 0.10

    #: P_spoof below this contributes nothing; the spoof factor ramps from here
    #: to 1.0. Below ~0.3 the experts are effectively saying "genuine".
    spoof_floor: float = 0.30

    #: P_spoof at or below this earns the genuine-voice mitigating credit.
    genuine_ceiling: float = 0.15

    #: Speaker similarity at or below this is a full mismatch. Mirrors
    #: settings.e4_similarity_threshold, restated here so the risk layer does
    #: not silently inherit an L3 tuning change.
    speaker_match_threshold: float = 0.70
    speaker_full_mismatch: float = 0.40

    #: Acoustic quality below this starts contributing risk of its own (a
    #: degraded channel is mildly adverse) and starts eroding confidence.
    quality_floor: float = 0.55

    #: Transaction amount is scored log-scaled between these bounds, so the
    #: curve is steep across ordinary retail values and flat above them.
    amount_low: float = 1_000.0
    amount_high: float = 500_000.0

    #: Velocity and deviation are normalised against these as "fully abnormal".
    velocity_full: float = 5.0
    deviation_full: float = 3.0

    #: Number reputation is [0, 1] where 1 is clean; below this it contributes.
    reputation_clean: float = 0.70
    #: A number younger than this is treated as freshly provisioned.
    number_new_days: int = 30

    #: Step-up failures reaching this count contribute the full weight.
    step_up_failures_full: int = 3
    escalations_full: int = 2


@dataclasses.dataclass(frozen=True)
class BandThresholds:
    """Score boundaries for the four configurable risk bands.

    Read as half-open intervals: LOW is [0, medium), MEDIUM is [medium, high),
    HIGH is [high, critical), CRITICAL is [critical, 1]. UNCERTAIN is not a
    score band - it is asserted by the fail-safe paths regardless of score.
    """

    medium: float = 0.35
    high: float = 0.60
    critical: float = 0.80

    def __post_init__(self):
        if not 0.0 < self.medium < self.high < self.critical < 1.0:
            raise ValueError(
                "band thresholds must satisfy 0 < medium < high < critical < 1, "
                f"got medium={self.medium}, high={self.high}, critical={self.critical}"
            )


@dataclasses.dataclass(frozen=True)
class ConfidenceParams:
    """How much confidence the engine claims in its own assessment.

    Confidence is a product of three independent adequacy terms: how sure the
    voice layer is, how much context arrived, and how good the audio was. Any
    one of them being poor caps the whole thing, which is what drives the
    UNCERTAIN fail-safe.
    """

    #: Weight of voice-belief confidence in the product (remainder is a floor,
    #: so a voice-blind assessment is not automatically zero-confidence when
    #: the contextual case is strong and complete).
    voice_weight: float = 0.60
    context_weight: float = 0.25
    quality_weight: float = 0.15

    #: Below this the engine must not assert a scored band (fail-safe P5).
    min_actionable: float = 0.35

    #: Context completeness below this marks the assessment context-degraded.
    min_context_completeness: float = 0.25


@dataclasses.dataclass(frozen=True)
class TierPolicy:
    """Per-tier action ladder and threshold tightening (§9.2).

    ``score_multiplier`` below 1.0 is how "the effective threshold must become
    more conservative as transaction sensitivity increases" is implemented: the
    band edges are scaled down, so the same score lands in a higher band on a
    tier-4 privileged authorisation than on a tier-0 balance enquiry.
    """

    tier: TransactionTier
    score_multiplier: float
    #: Action floor: the least restrictive action this tier will ever emit.
    baseline_action: PolicyAction
    #: Action taken when evidence is insufficient at this tier.
    uncertain_action: PolicyAction


#: Frozen five-tier ladder from §9.2. Tier 0 tolerates uncertainty with a
#: warning; from tier 2 up, uncertainty always costs a step-up, and tier 4
#: holds outright rather than letting a privileged action through unverified.
DEFAULT_TIER_POLICIES: Dict[TransactionTier, TierPolicy] = {
    TransactionTier.TIER_0: TierPolicy(
        TransactionTier.TIER_0, 1.15, PolicyAction.ALLOW, PolicyAction.WARN
    ),
    TransactionTier.TIER_1: TierPolicy(
        TransactionTier.TIER_1, 1.00, PolicyAction.ALLOW, PolicyAction.WARN
    ),
    TransactionTier.TIER_2: TierPolicy(
        TransactionTier.TIER_2, 0.88, PolicyAction.ALLOW, PolicyAction.STEP_UP
    ),
    TransactionTier.TIER_3: TierPolicy(
        TransactionTier.TIER_3, 0.78, PolicyAction.ALLOW, PolicyAction.STEP_UP
    ),
    TransactionTier.TIER_4: TierPolicy(
        TransactionTier.TIER_4, 0.68, PolicyAction.WARN, PolicyAction.HOLD
    ),
}


@dataclasses.dataclass(frozen=True)
class TierMapping:
    """Rules mapping a transaction to a sensitivity tier (C-39).

    Unknown maps to TIER_4, not TIER_0. An unclassified request on a call the
    system cannot vouch for is the case most worth protecting, and defaulting
    it to "informational" would be exactly the wrong failure direction.
    """

    #: Explicit transaction_type / sensitive_action tokens, matched uppercased.
    type_tiers: Tuple[Tuple[str, TransactionTier], ...] = (
        ("BALANCE_ENQUIRY", TransactionTier.TIER_0),
        ("INFORMATIONAL", TransactionTier.TIER_0),
        ("STATEMENT_REQUEST", TransactionTier.TIER_0),
        ("ACCOUNT_INFO", TransactionTier.TIER_1),
        ("TRANSACTION_HISTORY", TransactionTier.TIER_1),
        ("CARD_ACTIVATION", TransactionTier.TIER_2),
        ("CREDENTIAL_RESET", TransactionTier.TIER_2),
        ("PASSWORD_RESET", TransactionTier.TIER_2),
        ("MFA_RESET", TransactionTier.TIER_2),
        ("PAYEE_ADDITION", TransactionTier.TIER_3),
        ("TRANSFER", TransactionTier.TIER_3),
        ("PAYMENT", TransactionTier.TIER_3),
        ("WIRE_TRANSFER", TransactionTier.TIER_3),
        ("LIMIT_INCREASE", TransactionTier.TIER_3),
        ("PRIVILEGED_AUTHORISATION", TransactionTier.TIER_4),
        ("ACCOUNT_TAKEOVER_SENSITIVE", TransactionTier.TIER_4),
        ("BENEFICIARY_BULK_UPDATE", TransactionTier.TIER_4),
    )

    #: A monetary amount at or above a bound promotes the tier to at least that
    #: level, whatever the declared type says. Ordered high to low.
    amount_tiers: Tuple[Tuple[float, TransactionTier], ...] = (
        (250_000.0, TransactionTier.TIER_4),
        (10_000.0, TransactionTier.TIER_3),
        (0.01, TransactionTier.TIER_3),
    )

    #: Tier when no transaction information of any kind was supplied.
    unknown_tier: TransactionTier = TransactionTier.TIER_4

    #: Tier for a call carrying no transaction at all but a declared workflow.
    default_tier: TransactionTier = TransactionTier.TIER_1


@dataclasses.dataclass(frozen=True)
class RiskConfig:
    """Complete, inspectable configuration for the Context and Risk Engine."""

    weights: ScoringWeights = dataclasses.field(default_factory=ScoringWeights)
    params: ScoringParams = dataclasses.field(default_factory=ScoringParams)
    bands: BandThresholds = dataclasses.field(default_factory=BandThresholds)
    confidence: ConfidenceParams = dataclasses.field(default_factory=ConfidenceParams)
    tier_mapping: TierMapping = dataclasses.field(default_factory=TierMapping)
    tier_policies: Dict[TransactionTier, TierPolicy] = dataclasses.field(
        default_factory=lambda: dict(DEFAULT_TIER_POLICIES)
    )
    policy_version: str = POLICY_VERSION

    #: Number of factors published as ``top_factors``.
    top_factor_count: int = 5

    #: Set True ONLY after a calibration set has been fitted and validated.
    #: While False the engine labels its output an uncalibrated risk score and
    #: refuses to describe it as a probability.
    calibration_performed: bool = False
