"""Composite risk calculation (C-38).

L4-rear. Combines the acoustic ``VoiceBelief`` with the ``ContextVector`` into a
scored, banded, explained ``RiskAssessment``, then runs the explicit policy
ladder over it to produce an actionable ``RiskDecision``.

Order of operations, and why
----------------------------
1. Score        - transparent additive factors (:mod:`.scoring`).
2. Tier         - transaction sensitivity (:mod:`.policies`).
3. Band         - score against tier-tightened thresholds.
4. Confidence   - how much of the needed evidence actually arrived.
5. Policy       - explicit rules decide the action, not the score.

Steps 4 and 5 are the safety-critical pair. Confidence is computed from
evidence adequacy alone and never from the score, so a high score can never
talk the engine into believing itself. The policy ladder then reads confidence
first: if it is below the actionable floor, the case is routed to UNCERTAIN /
step-up regardless of what the score said.

Failure direction
-----------------
Every failure mode in this module resolves towards more verification, never
less. Missing models, missing context, unparseable input and unexpected
exceptions all land on UNCERTAIN with a step-up, because the alternative -
inventing a confident band from evidence the system does not have - is the one
outcome a fraud-detection system must never produce.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from voiceshield.contracts import (
    ContextVector,
    EvidenceReference,
    PolicyAction,
    ProvenanceType,
    RiskAssessment,
    RiskBand,
    RiskContribution,
    RiskDecision,
    ScoreSemantics,
    TransactionTier,
    VoiceBelief,
)
from voiceshield.obs.logging import get_logger

from .config import RiskConfig
from .policies import (
    CORE_SPOOF_EXPERTS,
    PolicyInput,
    PolicyLadder,
    StandardTransactionSensitivity,
)
from .scoring import FactorScorer

logger = get_logger("voiceshield.risk.risk_engine")


class RiskEngine(ABC):
    """Abstract interface for combining acoustic VoiceBelief and ContextVector into RiskAssessment."""

    @abstractmethod
    def evaluate_risk(
        self,
        session_id: str,
        belief: VoiceBelief,
        context: ContextVector,
    ) -> RiskAssessment:
        """Compute composite risk score, risk band, and ordered factor contributions."""
        raise NotImplementedError("RiskEngine.evaluate_risk is not implemented yet")


class StandardRiskEngine(RiskEngine):
    """Concrete Context and Risk Engine (C-38, C-39, C-40)."""

    def __init__(
        self,
        config: Optional[RiskConfig] = None,
        ladder: Optional[PolicyLadder] = None,
    ):
        self.config = config or RiskConfig()
        self.scorer = FactorScorer(self.config)
        self.sensitivity = StandardTransactionSensitivity(self.config)
        self.ladder = ladder or PolicyLadder()

    # --- confidence ----------------------------------------------------------

    def _context_completeness(self, context: ContextVector) -> float:
        """Fraction of context fields that were actually supplied."""
        prov = context.provenance
        if not prov:
            # No provenance map at all means the context was hand-built rather
            # than ingested. Fall back to counting populated fields so that a
            # well-populated hand-built vector is not punished as empty.
            return self._structural_completeness(context)
        known = sum(1 for p in prov.values() if p != ProvenanceType.UNAVAILABLE)
        return known / len(prov)

    @staticmethod
    def _structural_completeness(context: ContextVector) -> float:
        """Completeness inferred from populated fields, for provenance-less vectors."""
        total = 0
        known = 0
        for section in ("identity", "number", "transaction", "behaviour", "technical", "history"):
            sub = getattr(context, section)
            for name, field in type(sub).model_fields.items():
                total += 1
                value = getattr(sub, name)
                if value is None:
                    continue
                # A field still sitting at its declared default carries no
                # information, so it must not count towards completeness.
                if value == field.default:
                    continue
                known += 1
        return known / total if total else 0.0

    def _compute_confidence(
        self,
        belief: VoiceBelief,
        completeness: float,
    ) -> Tuple[float, bool]:
        """Return ``(confidence, poor_audio)`` from evidence adequacy only.

        Never reads the risk score. Confidence answers "how much of what we
        needed did we get", which is independent of what that evidence said.
        """
        cp = self.config.confidence
        params = self.config.params

        voice_term = belief.confidence if belief.P_spoof is not None else 0.0

        quality = belief.q_call
        poor_audio = quality is not None and quality < params.quality_floor
        if quality is None:
            # Unknown quality is not good quality; assume the floor.
            quality_term = params.quality_floor
        else:
            quality_term = max(0.0, min(1.0, quality))

        confidence = (
            cp.voice_weight * max(0.0, min(1.0, voice_term))
            + cp.context_weight * max(0.0, min(1.0, completeness))
            + cp.quality_weight * quality_term
        )
        return max(0.0, min(1.0, confidence)), poor_audio

    # --- banding -------------------------------------------------------------

    def _band_for(self, score: float, tier: TransactionTier) -> RiskBand:
        """Classify ``score`` against the tier-tightened band edges.

        Tightening is what makes the threshold "more conservative as
        transaction sensitivity increases" (§9.2): the edges move down, so an
        identical score bands higher on a privileged authorisation than on a
        balance enquiry.
        """
        edges = self.sensitivity.get_tier_thresholds(tier)
        if score >= edges["critical"]:
            return RiskBand.CRITICAL
        if score >= edges["high"]:
            return RiskBand.HIGH
        if score >= edges["medium"]:
            return RiskBand.MEDIUM
        return RiskBand.LOW

    # --- evidence references -------------------------------------------------

    def _evidence_refs(
        self,
        belief: VoiceBelief,
        context: ContextVector,
        contributions: List[RiskContribution],
        policy_id: str,
    ) -> List[EvidenceReference]:
        """Build pointers to the artefacts this assessment rests on.

        References, never copies. The engine must be able to say where a signal
        came from without carrying audio or embeddings into the decision record
        (privacy principle P2).
        """
        refs: List[EvidenceReference] = [
            EvidenceReference(
                kind="VOICE_BELIEF",
                ref=f"belief:{belief.session_id}@{belief.timestamp.isoformat()}",
                detail=(
                    f"band={belief.band.value}, "
                    f"P_spoof={'n/a' if belief.P_spoof is None else format(belief.P_spoof, '.3f')}, "
                    f"confidence={belief.confidence:.3f}"
                ),
            )
        ]
        for expert in belief.contributing_experts:
            p = expert.calibrated_p if expert.calibrated_p is not None else expert.raw_p
            refs.append(
                EvidenceReference(
                    kind="EXPERT",
                    ref=f"expert:{expert.expert_id}",
                    detail=f"p={'n/a' if p is None else format(p, '.3f')}, fusion_weight={expert.weight:.3f}",
                )
            )
        for version in belief.model_versions:
            refs.append(EvidenceReference(kind="EXPERT", ref=f"model:{version}", detail="model version"))

        contributing_factors = {c.factor for c in contributions}
        for key, provenance in sorted(context.provenance.items()):
            # Only reference context fields that actually moved the score;
            # listing thirty untouched fields would bury the ones that mattered.
            if provenance == ProvenanceType.UNAVAILABLE:
                continue
            field = key.split(".")[-1]
            if any(field in factor or factor in key for factor in contributing_factors):
                refs.append(
                    EvidenceReference(
                        kind="CONTEXT",
                        ref=f"context:{key}",
                        detail=f"provenance={provenance.value}",
                    )
                )

        refs.append(
            EvidenceReference(
                kind="POLICY",
                ref=f"policy:{policy_id}@{self.config.policy_version}",
                detail="matched policy rule",
            )
        )
        return refs

    # --- public API ----------------------------------------------------------

    def evaluate_risk(
        self,
        session_id: str,
        belief: VoiceBelief,
        context: ContextVector,
    ) -> RiskAssessment:
        """Compute the composite risk assessment (C-38).

        Returns the scored assessment only. Callers that need an action must
        use :meth:`assess`, because the score alone is explicitly not permitted
        to decide anything (§9.3).
        """
        return self.assess(session_id, belief, context).risk

    def assess(
        self,
        session_id: str,
        belief: VoiceBelief,
        context: ContextVector,
    ) -> RiskDecision:
        """Full evaluation: score, band, confidence, policy, action, explanation.

        This is the engine's real entry point. Any exception raised inside it is
        caught and converted into a fail-safe UNCERTAIN decision rather than
        propagated, so a defect in scoring degrades the call to a step-up
        instead of taking the decision path down.
        """
        now = datetime.now(timezone.utc)
        try:
            return self._assess(session_id, belief, context, now)
        except Exception as exc:  # noqa: BLE001 - deliberate fail-safe boundary
            import traceback
            tb = traceback.format_exc()
            logger.error(
                "risk evaluation failed; falling back to UNCERTAIN",
                extra={"extra_fields": {"session_id": session_id, "error": repr(exc), "traceback": tb}},
            )
            print(f"EVALUATION_ERROR TRACEBACK: {tb}")
            return self._fail_safe_decision(session_id, now, f"EVALUATION_ERROR: {type(exc).__name__}")

    def _assess(
        self,
        session_id: str,
        belief: VoiceBelief,
        context: ContextVector,
        now: datetime,
    ) -> RiskDecision:
        cfg = self.config

        score, contributions = self.scorer.score(belief, context)
        tier = self.sensitivity.evaluate_tier(context)
        scored_band = self._band_for(score, tier)

        completeness = self._context_completeness(context)
        confidence, poor_audio = self._compute_confidence(belief, completeness)

        contributing_experts = {c.expert_id for c in belief.contributing_experts}
        model_unavailable = not (contributing_experts & set(CORE_SPOOF_EXPERTS))

        outcome = self.ladder.evaluate(
            PolicyInput(
                session_id=session_id,
                belief=belief,
                context=context,
                tier=tier,
                score=score,
                scored_band=scored_band,
                confidence=confidence,
                context_completeness=completeness,
                model_unavailable=model_unavailable,
                poor_audio=poor_audio,
                config=cfg,
            )
        )

        final_band = outcome.band or scored_band
        context_degraded = completeness < cfg.confidence.min_context_completeness

        reason_codes = list(outcome.reason_codes)
        if context_degraded and "CONTEXT_INCOMPLETE" not in reason_codes:
            reason_codes.append("CONTEXT_INCOMPLETE")
        if not cfg.calibration_performed:
            # Stamped on every decision so that no consumer downstream can read
            # the score as a probability without also seeing this.
            reason_codes.append("SCORE_UNCALIBRATED")

        assessment = RiskAssessment(
            session_id=session_id,
            risk_score=round(score, 6),
            risk_confidence=round(confidence, 6),
            risk_band=final_band,
            contributions=contributions,
            context_degraded=context_degraded,
            score_semantics=(
                ScoreSemantics.CALIBRATED_PROBABILITY
                if cfg.calibration_performed
                else ScoreSemantics.UNCALIBRATED_RISK_SCORE
            ),
            score_label=("calibrated probability" if cfg.calibration_performed else "risk score"),
            timestamp=now,
        )

        return RiskDecision(
            session_id=session_id,
            risk=assessment,
            action=outcome.action,
            matched_policy=outcome.policy_id,
            transaction_tier=tier,
            reason_codes=reason_codes,
            top_factors=contributions[: cfg.top_factor_count],
            evidence_refs=self._evidence_refs(belief, context, contributions, outcome.policy_id),
            recommended_verifications=list(outcome.recommended_verifications),
            fail_safe_engaged=outcome.fail_safe,
            policy_version=cfg.policy_version,
            timestamp=now,
        )

    def _fail_safe_decision(self, session_id: str, now: datetime, reason: str) -> RiskDecision:
        """The decision emitted when the engine itself could not complete.

        Deliberately does not carry a score: emitting a number here would imply
        an assessment took place. The band is UNCERTAIN and the action is a
        step-up, which is the correct answer to "we do not know".
        """
        assessment = RiskAssessment(
            session_id=session_id,
            risk_score=0.0,
            risk_confidence=0.0,
            risk_band=RiskBand.UNCERTAIN,
            contributions=[],
            context_degraded=True,
            score_semantics=ScoreSemantics.UNCALIBRATED_RISK_SCORE,
            score_label="risk score (not computed)",
            timestamp=now,
        )
        return RiskDecision(
            session_id=session_id,
            risk=assessment,
            action=PolicyAction.STEP_UP,
            matched_policy="P-ENGINE-FAILURE",
            transaction_tier=self.config.tier_mapping.unknown_tier,
            reason_codes=["ENGINE_FAILURE", reason, "FAIL_SAFE_UNCERTAIN", "SCORE_UNCALIBRATED"],
            top_factors=[],
            evidence_refs=[
                EvidenceReference(
                    kind="POLICY",
                    ref=f"policy:P-ENGINE-FAILURE@{self.config.policy_version}",
                    detail=reason,
                )
            ],
            recommended_verifications=[
                "Risk assessment could not be completed; verify the caller manually",
                "Do not action a sensitive request on this session without out-of-band confirmation",
            ],
            fail_safe_engaged=True,
            policy_version=self.config.policy_version,
            timestamp=now,
        )

    # --- explanation helper --------------------------------------------------

    def explain(self, decision: RiskDecision) -> str:
        """Render a plain-text breakdown of how the score was reached.

        Phrased as attribution, never as proof (§10.1): these are the factors
        that moved this policy set's score, not evidence that the call is
        fraudulent.
        """
        lines = [
            f"WHY THIS CALL SCORED {decision.risk.risk_score:.2f} "
            f"({decision.risk.risk_band.value})",
            "",
            f"This is an uncalibrated {decision.risk.score_label}, not a probability of fraud."
            if decision.risk.score_semantics == ScoreSemantics.UNCALIBRATED_RISK_SCORE
            else f"This is a calibrated probability ({decision.risk.score_label}).",
            "",
            "These are the features contributing to the score, not proof of anything:",
        ]
        lines.append(f"  {'baseline':<28} {self.config.params.baseline:+.3f}")
        for contrib in decision.top_factors:
            lines.append(f"  {contrib.factor:<28} {contrib.points:+.3f}   {contrib.detail or ''}")
        lines += [
            "",
            f"  {'TOTAL':<28} {decision.risk.risk_score:.3f}",
            f"  {'Confidence':<28} {decision.risk.risk_confidence:.3f}",
            f"  {'Action':<28} {decision.action.value}",
            f"  {'Policy':<28} {decision.matched_policy} ({decision.policy_version})",
        ]
        return "\n".join(lines)
