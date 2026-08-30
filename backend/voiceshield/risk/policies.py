"""Explicit, inspectable policy rules (C-39, C-40, §9.2, §9.3).

The score does not decide anything. It is one input to an ordered ladder of
named rules, each of which either matches and mandates an action or declines
and passes the case down. §9.3 requires exactly this separation: no opaque
model may be the thing that decides whether a financial transaction executes.

Rules are evaluated in priority order, highest first. The first match wins and
its identifier is published as ``matched_policy``, so any decision can be traced
to the one rule that produced it.

The six mandated policies
-------------------------
1. ordinary call                    -> P-ORDINARY-CALL
2. suspicious voice, low-value      -> P-SUSPICIOUS-VOICE-LOW-VALUE
3. suspicious voice + high value    -> P-SUSPICIOUS-VOICE-HIGH-VALUE
4. strong speaker mismatch          -> P-STRONG-SPEAKER-MISMATCH
5. poor audio / low confidence      -> P-INSUFFICIENT-CONFIDENCE
6. model unavailable                -> P-MODEL-UNAVAILABLE
"""

import dataclasses
from decimal import Decimal
from typing import Callable, Dict, List, Optional, Tuple

# pyrefly: ignore [missing-import]
from voiceshield.contracts import (
    ContextVector,
    DecisionBand,
    PolicyAction,
    RiskBand,
    TransactionTier,
    VoiceBelief,
)

from .config import RiskConfig

#: Experts whose absence means the anti-spoofing capability itself is gone.
#: E5/E6 are DEFERRED by design in this build, so their absence is expected and
#: must not be reported as an outage.
CORE_SPOOF_EXPERTS = ("E1", "E2", "E3")

#: Tiers at or above which a transaction counts as "high value / sensitive" for
#: the purposes of policy 3, regardless of the monetary amount. A credential
#: reset carries no amount but is exactly the action policy 3 exists to catch.
HIGH_VALUE_TIER = TransactionTier.TIER_3


@dataclasses.dataclass
class PolicyInput:
    """Everything the rule ladder is allowed to look at.

    A frozen bundle rather than loose arguments so that adding a signal to the
    ladder is a visible change to this contract, not an implicit widening of
    what a rule may reach for.
    """

    session_id: str
    belief: VoiceBelief
    context: ContextVector
    tier: TransactionTier
    score: float
    #: Band derived from the score after tier tightening, before fail-safes.
    scored_band: RiskBand
    confidence: float
    context_completeness: float
    #: True when the core anti-spoofing experts did not run at all.
    model_unavailable: bool
    #: True when audio quality was below the configured floor.
    poor_audio: bool
    config: RiskConfig


@dataclasses.dataclass(frozen=True)
class PolicyOutcome:
    """What a matched rule mandates."""

    policy_id: str
    action: PolicyAction
    reason_codes: Tuple[str, ...]
    #: Band override. None leaves the scored band in place.
    band: Optional[RiskBand] = None
    recommended_verifications: Tuple[str, ...] = ()
    #: True when this outcome is a fail-safe rather than a scored judgement.
    fail_safe: bool = False


@dataclasses.dataclass(frozen=True)
class PolicyRule:
    """One named rule in the ladder."""

    policy_id: str
    priority: int
    description: str
    matches: Callable[[PolicyInput], bool]
    decide: Callable[[PolicyInput], PolicyOutcome]


# --- predicates ---------------------------------------------------------------


def _is_high_value(inp: PolicyInput) -> bool:
    """True when the requested action is high-value or otherwise sensitive."""
    if inp.tier >= HIGH_VALUE_TIER:
        return True
    txn = inp.context.transaction
    if txn.amount is not None:
        return float(txn.amount) >= inp.config.params.amount_high * 0.02
    return False


def _speaker_similarity(belief: VoiceBelief) -> Optional[float]:
    for contrib in belief.contributing_experts:
        if contrib.expert_id == "E4":
            p = contrib.calibrated_p if contrib.calibrated_p is not None else contrib.raw_p
            if p is not None:
                return max(0.0, min(1.0, 1.0 - p))
    return None


def _voice_suspicious(belief: VoiceBelief) -> bool:
    return belief.band in (DecisionBand.SUSPICIOUS, DecisionBand.SYNTHETIC_HIGH_CONFIDENCE)


def _tier_floor(inp: PolicyInput, action: PolicyAction) -> PolicyAction:
    """Raise ``action`` to the tier's baseline if the tier demands more."""
    policy = inp.config.tier_policies.get(inp.tier)
    if policy is None:
        return action
    return max(action, policy.baseline_action, key=ACTION_SEVERITY.get)


#: Ordering used whenever two actions must be combined - the more restrictive
#: one always wins. Never take the minimum of two actions.
ACTION_SEVERITY: Dict[PolicyAction, int] = {
    PolicyAction.ALLOW: 0,
    PolicyAction.WARN: 1,
    PolicyAction.ACTIVE_LIVENESS: 2,
    PolicyAction.STEP_UP: 3,
    PolicyAction.HOLD: 4,
    PolicyAction.ESCALATE: 5,
}


def escalate_to(a: PolicyAction, b: PolicyAction) -> PolicyAction:
    """Return the more restrictive of two actions."""
    return a if ACTION_SEVERITY[a] >= ACTION_SEVERITY[b] else b


# --- the six mandated rules ---------------------------------------------------


def _p_model_unavailable(inp: PolicyInput) -> PolicyOutcome:
    """Policy 6. The detector is down; the call is not thereby safe.

    Failing open here would mean an attacker who can knock out model loading
    gets an unmonitored channel, so the outcome is UNCERTAIN with a step-up
    scaled to what is being asked for.
    """
    tier_policy = inp.config.tier_policies[inp.tier]
    action = escalate_to(tier_policy.uncertain_action, PolicyAction.STEP_UP)
    if inp.tier == TransactionTier.TIER_0:
        action = tier_policy.uncertain_action
    return PolicyOutcome(
        policy_id="P-MODEL-UNAVAILABLE",
        action=action,
        reason_codes=("MODEL_UNAVAILABLE", "VOICE_EVIDENCE_ABSENT", "FAIL_SAFE_UNCERTAIN"),
        band=RiskBand.UNCERTAIN,
        recommended_verifications=(
            "Verify the caller through a channel that does not depend on voice analysis",
            "Call back on the number of record before actioning the request",
        ),
        fail_safe=True,
    )


def _p_insufficient_confidence(inp: PolicyInput) -> PolicyOutcome:
    """Policy 5. Poor audio or thin evidence; prefer UNCERTAIN over a guess.

    This is the rule the brief singles out: when evidence is insufficient the
    engine must say so and ask for verification, not manufacture a confident
    band from a score it cannot stand behind.
    """
    tier_policy = inp.config.tier_policies[inp.tier]
    reasons = ["INSUFFICIENT_CONFIDENCE", "FAIL_SAFE_UNCERTAIN"]
    if inp.poor_audio:
        reasons.insert(0, "POOR_AUDIO_QUALITY")
    if inp.context_completeness < inp.config.confidence.min_context_completeness:
        reasons.append("CONTEXT_INCOMPLETE")
    if inp.belief.uncertainty_reason:
        reasons.append("VOICE_BELIEF_UNCERTAIN")

    action = tier_policy.uncertain_action
    # A high score we cannot stand behind is still a reason for more friction,
    # not less: escalate the step-up to active liveness rather than waving it
    # through on low confidence.
    if inp.score >= inp.config.bands.high and inp.tier >= TransactionTier.TIER_2:
        action = escalate_to(action, PolicyAction.ACTIVE_LIVENESS)

    return PolicyOutcome(
        policy_id="P-INSUFFICIENT-CONFIDENCE",
        action=action,
        reason_codes=tuple(reasons),
        band=RiskBand.UNCERTAIN,
        recommended_verifications=(
            "Request a dynamically generated liveness challenge phrase",
            "Ask the caller to move to a better connection and re-attempt",
            "Confirm the request through a second factor before proceeding",
        ),
        fail_safe=True,
    )


def _p_strong_speaker_mismatch(inp: PolicyInput) -> PolicyOutcome:
    """Policy 4. The voice is not the enrolled speaker's.

    Distinct from a spoof finding: the audio may be perfectly natural human
    speech, just the wrong human. That is the classic social-engineering case
    and it warrants a hold on anything transactional regardless of score.
    """
    similarity = _speaker_similarity(inp.belief)
    detail = f"speaker similarity {similarity:.2f}" if similarity is not None else "speaker mismatch"

    if inp.tier >= TransactionTier.TIER_3:
        action = PolicyAction.ESCALATE if _is_high_value(inp) else PolicyAction.HOLD
    elif inp.tier >= TransactionTier.TIER_1:
        action = PolicyAction.STEP_UP
    else:
        action = PolicyAction.WARN

    band = RiskBand.CRITICAL if inp.tier >= TransactionTier.TIER_3 else RiskBand.HIGH
    return PolicyOutcome(
        policy_id="P-STRONG-SPEAKER-MISMATCH",
        action=action,
        reason_codes=("STRONG_SPEAKER_MISMATCH", "IDENTITY_NOT_CONFIRMED", f"TIER_{int(inp.tier)}"),
        band=band,
        recommended_verifications=(
            f"Voice does not match the enrolled reference ({detail}); verify identity out of band",
            "Do not accept voice as an identity factor for this session",
        ),
    )


def _p_suspicious_voice_high_value(inp: PolicyInput) -> PolicyOutcome:
    """Policy 3. Synthetic-speech evidence against a high-value request.

    The headline case. Both halves are individually survivable; together they
    are the fraud pattern the system exists to stop, so the action is a hold
    and, at the top tiers or on strong evidence, an escalation.
    """
    strong = inp.belief.band == DecisionBand.SYNTHETIC_HIGH_CONFIDENCE
    action = PolicyAction.ESCALATE if (strong or inp.tier == TransactionTier.TIER_4) else PolicyAction.HOLD

    reasons = ["SUSPICIOUS_VOICE", "HIGH_VALUE_ACTION", f"TIER_{int(inp.tier)}"]
    if strong:
        reasons.append("SYNTHETIC_HIGH_CONFIDENCE")
    if inp.context.transaction.beneficiary_novelty.value == "NEW":
        reasons.append("NEW_BENEFICIARY")

    return PolicyOutcome(
        policy_id="P-SUSPICIOUS-VOICE-HIGH-VALUE",
        action=action,
        reason_codes=tuple(reasons),
        band=RiskBand.CRITICAL if strong else RiskBand.HIGH,
        recommended_verifications=(
            "Hold the transaction pending out-of-band confirmation with the account holder",
            "Call back on the number of record; do not use a number supplied on this call",
            "Route to the fraud desk with the evidence record attached",
        ),
    )


def _p_suspicious_voice_low_value(inp: PolicyInput) -> PolicyOutcome:
    """Policy 2. Synthetic-speech evidence, but nothing much is being asked for.

    Proportionality. Blocking a balance enquiry because the codec made the
    caller sound synthetic trains staff to ignore the system, so this warns and
    records rather than obstructing - the evidence is still captured.
    """
    action = _tier_floor(inp, PolicyAction.WARN)
    if inp.belief.band == DecisionBand.SYNTHETIC_HIGH_CONFIDENCE and inp.tier >= TransactionTier.TIER_2:
        action = escalate_to(action, PolicyAction.STEP_UP)

    return PolicyOutcome(
        policy_id="P-SUSPICIOUS-VOICE-LOW-VALUE",
        action=action,
        reason_codes=("SUSPICIOUS_VOICE", "LOW_VALUE_ACTION", f"TIER_{int(inp.tier)}"),
        band=RiskBand.MEDIUM,
        recommended_verifications=(
            "Record the evidence and monitor; do not obstruct a low-sensitivity request",
            "Re-assess if the caller escalates to a transactional request",
        ),
    )


def _p_elevated_context(inp: PolicyInput) -> PolicyOutcome:
    """Contextual risk without a voice finding.

    Not one of the six mandated rules, but required for completeness: a genuine
    voice making a wildly anomalous request must not fall through to "ordinary
    call" simply because the acoustics were clean.
    """
    if inp.scored_band == RiskBand.CRITICAL:
        action = PolicyAction.HOLD if inp.tier >= TransactionTier.TIER_2 else PolicyAction.STEP_UP
    elif inp.scored_band == RiskBand.HIGH:
        action = PolicyAction.STEP_UP if inp.tier >= TransactionTier.TIER_2 else PolicyAction.WARN
    else:
        action = PolicyAction.WARN
    action = _tier_floor(inp, action)

    reasons = ["ELEVATED_CONTEXTUAL_RISK", f"RISK_BAND_{inp.scored_band.value}", f"TIER_{int(inp.tier)}"]
    if inp.context.behaviour.prior_fraud_indicator:
        reasons.append("PRIOR_FRAUD_INDICATOR")
    if inp.context.number.known_fraud_status:
        reasons.append("NUMBER_KNOWN_FRAUD")

    return PolicyOutcome(
        policy_id="P-ELEVATED-CONTEXT",
        action=action,
        reason_codes=tuple(reasons),
        recommended_verifications=(
            "Confirm the request against the customer's established pattern",
            "Apply standard step-up verification before actioning",
        ),
    )


def _p_ordinary_call(inp: PolicyInput) -> PolicyOutcome:
    """Policy 1. Nothing is wrong; let the call proceed.

    The terminal rule, and the one that must fire most of the time. A system
    that cannot say "this is fine" has no operational value.
    """
    action = _tier_floor(inp, PolicyAction.ALLOW)
    reasons = ["ORDINARY_CALL", f"RISK_BAND_{inp.scored_band.value}", f"TIER_{int(inp.tier)}"]
    if inp.belief.band == DecisionBand.GENUINE:
        reasons.append("VOICE_CONSISTENT_WITH_GENUINE")

    return PolicyOutcome(
        policy_id="P-ORDINARY-CALL",
        action=action,
        reason_codes=tuple(reasons),
        recommended_verifications=(),
    )


#: The ladder. Priority order is the whole design: the two fail-safes sit above
#: everything, so a case the engine cannot assess never reaches a rule that
#: would let it through on a score the engine does not believe.
DEFAULT_POLICY_RULES: Tuple[PolicyRule, ...] = (
    PolicyRule(
        policy_id="P-MODEL-UNAVAILABLE",
        priority=100,
        description="Core anti-spoofing experts did not run",
        matches=lambda i: i.model_unavailable,
        decide=_p_model_unavailable,
    ),
    PolicyRule(
        policy_id="P-STRONG-SPEAKER-MISMATCH",
        priority=90,
        description="Voice does not match the enrolled speaker reference",
        matches=lambda i: (
            (sim := _speaker_similarity(i.belief)) is not None
            and sim <= i.config.params.speaker_full_mismatch
            and i.confidence >= i.config.confidence.min_actionable
        ),
        decide=_p_strong_speaker_mismatch,
    ),
    PolicyRule(
        policy_id="P-INSUFFICIENT-CONFIDENCE",
        priority=80,
        description="Poor audio or insufficient evidence to assert a band",
        matches=lambda i: (
            i.confidence < i.config.confidence.min_actionable
            or i.belief.band == DecisionBand.UNCERTAIN
            or i.belief.P_spoof is None
        ),
        decide=_p_insufficient_confidence,
    ),
    PolicyRule(
        policy_id="P-SUSPICIOUS-VOICE-HIGH-VALUE",
        priority=70,
        description="Synthetic-speech evidence against a high-value or sensitive action",
        matches=lambda i: _voice_suspicious(i.belief) and _is_high_value(i),
        decide=_p_suspicious_voice_high_value,
    ),
    PolicyRule(
        policy_id="P-SUSPICIOUS-VOICE-LOW-VALUE",
        priority=60,
        description="Synthetic-speech evidence against a low-value action",
        matches=lambda i: _voice_suspicious(i.belief) and not _is_high_value(i),
        decide=_p_suspicious_voice_low_value,
    ),
    PolicyRule(
        policy_id="P-ELEVATED-CONTEXT",
        priority=50,
        description="Contextual risk elevated without a voice finding",
        matches=lambda i: i.scored_band in (RiskBand.MEDIUM, RiskBand.HIGH, RiskBand.CRITICAL),
        decide=_p_elevated_context,
    ),
    PolicyRule(
        policy_id="P-ORDINARY-CALL",
        priority=0,
        description="No adverse evidence; proceed",
        matches=lambda i: True,
        decide=_p_ordinary_call,
    ),
)


class PolicyLadder:
    """Evaluates the ordered rule set and returns the first match.

    Rules are sorted once at construction. The terminal rule must be total -
    the ladder asserts this rather than returning None, because a policy engine
    with no answer is a policy engine that has silently allowed something.
    """

    def __init__(self, rules: Optional[Tuple[PolicyRule, ...]] = None):
        # `is None` rather than falsy: an explicitly empty rule set is a caller
        # decision to be honoured, not an omission to be filled in with the
        # defaults. Silently restoring them would hide the misconfiguration.
        source = DEFAULT_POLICY_RULES if rules is None else rules
        self._rules: List[PolicyRule] = sorted(source, key=lambda r: r.priority, reverse=True)

    @property
    def rules(self) -> List[PolicyRule]:
        return list(self._rules)

    def evaluate(self, inp: PolicyInput) -> PolicyOutcome:
        """Return the outcome of the highest-priority matching rule."""
        for rule in self._rules:
            try:
                matched = rule.matches(inp)
            except Exception:  # noqa: BLE001 - a broken predicate must not fail open
                matched = False
            if matched:
                return rule.decide(inp)
        # Unreachable while P-ORDINARY-CALL is present, but if a caller supplies
        # a custom rule set with no terminal rule, refuse rather than allow.
        return PolicyOutcome(
            policy_id="P-NO-RULE-MATCHED",
            action=PolicyAction.STEP_UP,
            reason_codes=("NO_POLICY_MATCHED", "FAIL_SAFE_UNCERTAIN"),
            band=RiskBand.UNCERTAIN,
            recommended_verifications=("Verify the caller manually; no policy rule matched",),
            fail_safe=True,
        )


class StandardTransactionSensitivity:
    """Maps transaction context to a sensitivity tier (C-39, §9.2).

    Takes the maximum of every signal that implies a tier - declared type,
    sensitive-action classification, workflow state and monetary amount - so
    that a request cannot be downgraded by labelling it benignly while asking
    for a quarter of a million.
    """

    #: Workflow states that imply a tier floor of their own.
    WORKFLOW_TIERS = {
        "CREDENTIAL_RESET": TransactionTier.TIER_2,
        "PAYEE_ADDITION": TransactionTier.TIER_3,
        "LIMIT_INCREASE": TransactionTier.TIER_3,
        "HIGH_VALUE_TRANSFER": TransactionTier.TIER_3,
        "PRIVILEGED_AUTHORISATION": TransactionTier.TIER_4,
    }

    def __init__(self, config: Optional[RiskConfig] = None):
        self.config = config or RiskConfig()

    def evaluate_tier(self, context: ContextVector) -> TransactionTier:
        """Map transaction and workflow context to a sensitivity tier 0-4."""
        mapping = self.config.tier_mapping
        txn = context.transaction
        workflow = context.behaviour.workflow_state.value

        tokens = [t for t in (txn.transaction_type, txn.sensitive_action) if t]
        declared: Optional[TransactionTier] = None
        for token in tokens:
            key = str(token).strip().upper().replace(" ", "_").replace("-", "_")
            for name, tier in mapping.type_tiers:
                if key == name:
                    declared = tier if declared is None else max(declared, tier)
                    break

        amount_tier: Optional[TransactionTier] = None
        if txn.amount is not None:
            amount = float(txn.amount) if isinstance(txn.amount, Decimal) else float(txn.amount)
            for bound, tier in mapping.amount_tiers:
                if amount >= bound:
                    amount_tier = tier
                    break

        workflow_tier = self.WORKFLOW_TIERS.get(workflow)

        candidates = [t for t in (declared, amount_tier, workflow_tier) if t is not None]
        if candidates:
            return max(candidates)

        if workflow == "ROUTINE":
            return mapping.default_tier

        # Nothing was declared at all. Default to the most protective tier
        # rather than assuming the request is informational.
        return mapping.unknown_tier

    def get_tier_thresholds(self, tier: TransactionTier) -> Dict[str, float]:
        """Return the band edges as tightened for this tier."""
        policy = self.config.tier_policies[tier]
        bands = self.config.bands
        m = policy.score_multiplier
        return {
            "medium": min(0.999, bands.medium * m),
            "high": min(0.999, bands.high * m),
            "critical": min(0.999, bands.critical * m),
            "multiplier": m,
        }
