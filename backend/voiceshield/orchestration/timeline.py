"""Timeline construction (§34).

Turns analysis state changes into the analyst-facing narrative of a call.

The whole design decision here is *when not to append*. A slow tick fires every
1.5 s; appending on each one would produce forty rows saying "still MEDIUM" for
a one-minute call, which buries the two rows that mattered. The recorder
therefore appends only when the band or the action actually changes.
"""

from datetime import datetime, timezone
from typing import List, Optional

from voiceshield.contracts import (
    EvidenceReference,
    PolicyAction,
    RiskBand,
    RiskDecision,
    TimelineEntry,
    TimelineEventKind,
    TimelineSeverity,
)

from .state import SessionAnalysisState

#: How prominently each band renders once it appears on the timeline.
_BAND_SEVERITY = {
    RiskBand.LOW: TimelineSeverity.INFO,
    RiskBand.MEDIUM: TimelineSeverity.NOTICE,
    RiskBand.HIGH: TimelineSeverity.WARNING,
    RiskBand.CRITICAL: TimelineSeverity.CRITICAL,
    RiskBand.UNCERTAIN: TimelineSeverity.WARNING,
}

#: Actions that represent the system objecting to something.
_OBJECTING_ACTIONS = {
    PolicyAction.STEP_UP,
    PolicyAction.HOLD,
    PolicyAction.ESCALATE,
    PolicyAction.ACTIVE_LIVENESS,
}


class TimelineRecorder:
    """Appends timeline entries to a session's bounded history."""

    def append(
        self,
        state: SessionAnalysisState,
        kind: TimelineEventKind,
        label: str,
        *,
        severity: TimelineSeverity = TimelineSeverity.INFO,
        detail: Optional[str] = None,
        t_offset_s: Optional[float] = None,
        risk_band: Optional[RiskBand] = None,
        action: Optional[PolicyAction] = None,
        reason_codes: Optional[List[str]] = None,
        evidence_refs: Optional[List[EvidenceReference]] = None,
        transaction_id: Optional[str] = None,
    ) -> TimelineEntry:
        """Append one entry and return it."""
        entry = TimelineEntry(
            seq=state.next_timeline_seq(),
            session_id=state.session_id,
            kind=kind,
            severity=severity,
            label=label,
            detail=detail,
            t_offset_s=t_offset_s,
            risk_band=risk_band,
            action=action,
            reason_codes=list(reason_codes or []),
            evidence_refs=list(evidence_refs or []),
            transaction_id=transaction_id,
            timestamp=datetime.now(timezone.utc),
        )
        state.append_timeline(entry)
        return entry

    def record_decision(
        self,
        state: SessionAnalysisState,
        decision: RiskDecision,
        t_offset_s: Optional[float] = None,
    ) -> List[TimelineEntry]:
        """Append entries for a decision, but only where something changed.

        Returns the entries appended, which may be empty - that is the normal
        case for a steady call, and an empty return is not a failure.
        """
        appended: List[TimelineEntry] = []
        band = decision.risk.risk_band
        action = decision.action

        if band != state.last_band:
            appended.append(
                self.append(
                    state,
                    TimelineEventKind.BAND_CHANGED,
                    label=self._band_label(state.last_band, band),
                    severity=_BAND_SEVERITY.get(band, TimelineSeverity.NOTICE),
                    detail=(
                        f"{decision.risk.score_label} {decision.risk.risk_score:.2f}, "
                        f"confidence {decision.risk.risk_confidence:.2f} "
                        f"(policy {decision.matched_policy})"
                    ),
                    t_offset_s=t_offset_s,
                    risk_band=band,
                    action=action,
                    reason_codes=list(decision.reason_codes),
                    evidence_refs=list(decision.evidence_refs[:4]),
                )
            )
            state.last_band = band

        if action != state.last_action:
            appended.append(
                self.append(
                    state,
                    TimelineEventKind.ACTION_CHANGED,
                    label=self._action_label(action),
                    severity=(
                        TimelineSeverity.CRITICAL
                        if action == PolicyAction.ESCALATE
                        else TimelineSeverity.WARNING
                        if action in _OBJECTING_ACTIONS
                        else TimelineSeverity.INFO
                    ),
                    detail=self._verification_detail(decision),
                    t_offset_s=t_offset_s,
                    risk_band=band,
                    action=action,
                    reason_codes=list(decision.reason_codes),
                )
            )
            state.last_action = action

        return appended

    @staticmethod
    def _band_label(previous: Optional[RiskBand], current: RiskBand) -> str:
        if current == RiskBand.UNCERTAIN:
            # Not a level on the LOW..CRITICAL scale - it means the system
            # declined to assert one, and the label must not imply otherwise.
            return "Evidence insufficient to assert a risk band"
        if previous is None:
            return f"Risk assessed as {current.value}"
        return f"Risk moved {previous.value} to {current.value}"

    @staticmethod
    def _action_label(action: PolicyAction) -> str:
        return {
            PolicyAction.ALLOW: "Call allowed to proceed",
            PolicyAction.WARN: "Warning raised to the operator",
            PolicyAction.ACTIVE_LIVENESS: "Liveness challenge requested",
            PolicyAction.STEP_UP: "Step-up verification required",
            PolicyAction.HOLD: "Transaction held pending verification",
            PolicyAction.ESCALATE: "Escalated to the fraud desk",
        }.get(action, f"Action {action.value}")

    @staticmethod
    def _verification_detail(decision: RiskDecision) -> Optional[str]:
        if not decision.recommended_verifications:
            return None
        return "; ".join(decision.recommended_verifications[:2])
