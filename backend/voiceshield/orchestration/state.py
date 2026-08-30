"""Per-session analysis state (C-38, privacy principle P2).

Holds what a live session has concluded so far, so the REST routes can read an
assessment without recomputing one.

Privacy
-------
This module is where "raw audio never leaves the ingestion boundary" becomes
structural rather than aspirational. ``SessionAnalysisState`` stores no
``FrameObject`` and therefore no PCM: a frame exists only inside
``frame_queue`` and in the local variable of the fast tick that consumes it.
``release()`` drains the queue. Nothing a route can reach holds audio.
"""

import asyncio
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Deque, Dict, List, Optional

from voiceshield.contracts import (
    ContextVector,
    EvidenceVector,
    PolicyAction,
    RiskBand,
    RiskDecision,
    TimelineEntry,
    VoiceBelief,
)
from voiceshield.fusion import StandardBeliefAccumulator

from .config import OrchestrationConfig
from .errors import AnalysisStateNotFound


@dataclass
class SessionAnalysisState:
    """Everything one session's analysis has produced.

    The belief accumulator is per session rather than the shared singleton:
    ``StandardBeliefAccumulator`` keys its internal state by session_id but
    never evicts, so a long-running process would leak one trajectory per call
    forever. Owning it here means it dies with the session.
    """

    session_id: str
    accumulator: StandardBeliefAccumulator
    frame_queue: "asyncio.Queue"
    config: OrchestrationConfig

    worker: Optional["asyncio.Task"] = None

    latest_belief_fast: Optional[VoiceBelief] = None
    latest_belief_slow: Optional[VoiceBelief] = None
    latest_evidence: Optional[EvidenceVector] = None
    latest_decision: Optional[RiskDecision] = None
    latest_context: Optional[ContextVector] = None

    decisions: Deque[RiskDecision] = field(default_factory=deque)
    timeline: Deque[TimelineEntry] = field(default_factory=deque)

    #: Last band/action published to the timeline, so entries are appended on
    #: transitions rather than on every slow tick.
    last_band: Optional[RiskBand] = None
    last_action: Optional[PolicyAction] = None

    #: Demo transaction this session is acting on, if any.
    transaction_id: Optional[str] = None

    #: Last action actually dispatched to that transaction, so a verdict that
    #: holds steady across ticks is applied once rather than every 1.5 s.
    last_applied_action: Optional[PolicyAction] = None

    frames_seen: int = 0
    frames_scored: int = 0
    frames_skipped_backpressure: int = 0
    frames_decimated: int = 0
    over_budget_streak: int = 0
    decimating: bool = False

    timeline_seq: int = 0
    timeline_truncated: bool = False

    session_start_t: Optional[float] = None
    last_slow_t: float = float("-inf")
    first_frame_at: Optional[datetime] = None
    last_frame_at: Optional[datetime] = None
    stopped: bool = False

    def record_frame(self, frame) -> None:
        """Count a frame's arrival. Retains no audio and no reference to it."""
        self.frames_seen += 1
        now = datetime.now(tz=frame.created_at.tzinfo) if frame.created_at.tzinfo else datetime.now()
        if self.first_frame_at is None:
            self.first_frame_at = now
            self.session_start_t = frame.t_start
        self.last_frame_at = now

    def next_timeline_seq(self) -> int:
        value = self.timeline_seq
        self.timeline_seq += 1
        return value

    def append_timeline(self, entry: TimelineEntry) -> None:
        """Append an entry, noting if the bounded buffer discarded an older one."""
        if len(self.timeline) == self.timeline.maxlen:
            self.timeline_truncated = True
        self.timeline.append(entry)

    @property
    def has_assessment(self) -> bool:
        """True once an action-grade decision exists for this session."""
        return self.latest_decision is not None

    def degradation_reasons(self) -> List[str]:
        """Machine-readable reasons this analysis is less than fully informed.

        Surfaced on /risk so a degraded run is visibly degraded. An empty list
        means every expert reported OK and no frame was dropped.
        """
        reasons: List[str] = []
        evidence = self.latest_evidence
        if evidence is not None:
            for expert_id, status in sorted(evidence.expert_statuses.items()):
                if status.value != "OK":
                    reasons.append(f"{status.value}:{expert_id}")
        if self.frames_skipped_backpressure:
            reasons.append(f"BACKPRESSURE_DROPS:{self.frames_skipped_backpressure}")
        if self.frames_decimated:
            reasons.append(f"DECIMATED_FRAMES:{self.frames_decimated}")
        if self.latest_decision is not None and self.latest_decision.fail_safe_engaged:
            reasons.append("FAIL_SAFE_ENGAGED")
        return reasons

    def drain_queue(self) -> None:
        """Discard any buffered frames, releasing their PCM immediately."""
        while True:
            try:
                self.frame_queue.get_nowait()
            except Exception:
                break


class SessionAnalysisStore:
    """Process-local map of session_id -> analysis state."""

    def __init__(self, config: Optional[OrchestrationConfig] = None):
        self._config = config or OrchestrationConfig()
        self._states: Dict[str, SessionAnalysisState] = {}

    @property
    def config(self) -> OrchestrationConfig:
        return self._config

    def get_or_create(self, session_id: str) -> SessionAnalysisState:
        state = self._states.get(session_id)
        if state is None:
            cfg = self._config
            state = SessionAnalysisState(
                session_id=session_id,
                accumulator=StandardBeliefAccumulator(),
                frame_queue=asyncio.Queue(maxsize=cfg.frame_queue_size),
                config=cfg,
                decisions=deque(maxlen=cfg.decision_history),
                timeline=deque(maxlen=cfg.timeline_history),
            )
            self._states[session_id] = state
        return state

    def get(self, session_id: str) -> SessionAnalysisState:
        """Return the state, or raise a typed 404 rather than a KeyError."""
        state = self._states.get(session_id)
        if state is None:
            raise AnalysisStateNotFound(session_id)
        return state

    def exists(self, session_id: str) -> bool:
        return session_id in self._states

    def session_ids(self) -> List[str]:
        """Snapshot of tracked session ids, safe to iterate while mutating."""
        return list(self._states)

    def release(self, session_id: str) -> None:
        """Drop buffered audio for a session while keeping its conclusions.

        Deliberately does not delete the state: /risk, /evidence and /timeline
        must still answer after a call ends. Only the PCM-bearing queue goes.
        """
        state = self._states.get(session_id)
        if state is not None:
            state.drain_queue()
            state.stopped = True

    def remove(self, session_id: str) -> None:
        state = self._states.pop(session_id, None)
        if state is not None:
            state.drain_queue()

    def clear(self) -> None:
        """Drop all state. Test and process-reset helper."""
        for state in self._states.values():
            state.drain_queue()
        self._states.clear()
