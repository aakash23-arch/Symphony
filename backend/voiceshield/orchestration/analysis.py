"""Analysis orchestration: the L1 -> L2 -> L3 -> L4 -> L5 wiring.

This is the only module permitted to compose every layer. Each layer package is
forbidden from importing its peers (the DAG in
``tests/test_architecture_boundaries.py``), which is what keeps them
independently testable; the cost of that isolation is that something above them
has to do the joining, and this is it.

The sync/async seam
-------------------
``L1IngestionPipeline`` calls ``on_frame(frame)`` synchronously, between
``read_chunk`` awaits. ``ExpertRegistry.score_all`` is async and E3/E4 take
seconds, while frames arrive every 250 ms. Scoring inline would stall capture,
so ``on_frame`` does nothing but enqueue, and a per-session worker task does the
work. A full queue drops the frame and counts it: dropping audio is survivable,
stalling the microphone is not, and a silent drop would be worse than either.

Two clocks (§8.3)
-----------------
FAST, per frame: features -> experts -> evidence -> belief. No risk decision.
SLOW, ~1.5 s: belief + context -> risk decision -> timeline -> optional L5 action.

The fast clock deliberately emits no decision. A single 250 ms window is not
action-grade evidence, and ``Decision.clock`` is documented SLOW-only.

Degraded models
---------------
With no weights vendored every expert returns MODEL_UNAVAILABLE, and the
correct output is UNCERTAIN / STEP_UP. Four downstream components already
guarantee that; this module's job is to not undo it. In particular the slow
tick refuses to run before any frame has been scored, because
``RiskAssessment.risk_score`` is a non-optional float and a "nothing yet"
assessment would have to carry 0.0 - which a dashboard paints green.
"""

import asyncio
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Protocol

import numpy as np

from voiceshield.context import StandardContextEngine
from voiceshield.contracts import (
    ClockType,
    ContextVector,
    EventType,
    ExpertStatus,
    FrameObject,
    PolicyAction,
    TimelineEventKind,
    TimelineSeverity,
    VoiceBelief,
)
from voiceshield.evidence import StandardEvidenceAssembler
from voiceshield.models.registry import ExpertRegistry, expert_registry
from voiceshield.obs.logging import get_logger
from voiceshield.risk import StandardRiskEngine
from voiceshield.signal_processing.features import StandardFeatureExtractor
from voiceshield.transactions import TransactionSimulator

from .config import OrchestrationConfig
from .state import SessionAnalysisState, SessionAnalysisStore
from .timeline import TimelineRecorder

logger = get_logger("voiceshield.orchestration.analysis")

#: Sentinel pushed to end a worker loop.
_SENTINEL = object()

#: Experts whose absence means the anti-spoofing capability itself is gone.
#: E5/E6 are DEFERRED by design, so their absence is expected, not an outage.
CORE_SPOOF_EXPERTS = ("E1", "E2", "E3")

#: Actions that should reach a linked demo transaction.
_ACTIONABLE = {PolicyAction.HOLD, PolicyAction.ESCALATE}


class EventSink(Protocol):
    """What the orchestrator needs from an event bus.

    A Protocol rather than an import of ``api.runtime.EventBus``: the
    orchestration package must not depend on transport, or the dependency
    direction inverts. ``EventBus`` satisfies this structurally.
    """

    def publish_nowait(self, session_id: str, event_type: EventType, data: dict) -> None:
        ...


class _NullEventSink:
    """Discards events. Used when the orchestrator runs outside the API."""

    def publish_nowait(self, session_id: str, event_type: EventType, data: dict) -> None:
        return None


class AnalysisOrchestrator:
    """Drives per-session analysis from FrameObjects to RiskDecisions."""

    def __init__(
        self,
        *,
        store: Optional[SessionAnalysisStore] = None,
        events: Optional[EventSink] = None,
        registry: Optional[ExpertRegistry] = None,
        extractor: Optional[StandardFeatureExtractor] = None,
        assembler: Optional[StandardEvidenceAssembler] = None,
        risk_engine: Optional[StandardRiskEngine] = None,
        context_engine: Optional[StandardContextEngine] = None,
        transactions: Optional[TransactionSimulator] = None,
        config: Optional[OrchestrationConfig] = None,
    ):
        self.config = config or OrchestrationConfig()
        self.store = store or SessionAnalysisStore(self.config)
        self.events: EventSink = events or _NullEventSink()
        self.registry = registry or expert_registry
        self.extractor = extractor or StandardFeatureExtractor()
        self.assembler = assembler or StandardEvidenceAssembler()
        self.risk = risk_engine or StandardRiskEngine()
        self.context_engine = context_engine or StandardContextEngine()
        self.transactions = transactions
        self.timeline = TimelineRecorder()

    # --- ingestion seam ------------------------------------------------------

    def on_frame(self, frame: FrameObject) -> None:
        """Enqueue a frame for scoring. Sync, non-blocking, never raises.

        Passed directly as ``L1IngestionPipeline.run(on_frame=...)``. Anything
        slow here would stall audio capture, so this method must stay trivial.
        """
        try:
            state = self.store.get_or_create(frame.session_id)
            state.record_frame(frame)
            state.frame_queue.put_nowait(frame)
        except asyncio.QueueFull:
            # Dropping audio is survivable; stalling capture is not. The count
            # reaches /risk and /timeline so the gap is visible.
            state.frames_skipped_backpressure += 1
            logger.warning(
                "analysis backpressure; frame dropped",
                extra={"extra_fields": {
                    "session_id": frame.session_id,
                    "frame_id": frame.frame_id,
                    "dropped_total": state.frames_skipped_backpressure,
                }},
            )
        except Exception as exc:  # noqa: BLE001 - must never break ingestion
            logger.error(
                "on_frame failed; ingestion continues",
                extra={"extra_fields": {"session_id": frame.session_id, "error": repr(exc)}},
            )

    # --- lifecycle -----------------------------------------------------------

    async def start(self, session_id: str) -> SessionAnalysisState:
        """Spawn the scoring worker for a session."""
        state = self.store.get_or_create(session_id)
        if state.worker is None or state.worker.done():
            state.stopped = False
            state.worker = asyncio.create_task(self._worker(session_id))
            self.timeline.append(
                state,
                TimelineEventKind.ANALYSIS_STARTED,
                label="Voice analysis started",
                detail="Experts are scoring audio; no assessment has been produced yet.",
            )
        return state

    async def drain(self, session_id: str, timeout: Optional[float] = None) -> None:
        """Wait for in-flight scoring to finish, then stop the worker.

        A drain that times out leaves the last frames unscored. That is correct:
        no final score is ever synthesised to fill the gap (§22).
        """
        if not self.store.exists(session_id):
            return
        state = self.store.get(session_id)
        if state.worker is None or state.worker.done():
            self.store.release(session_id)
            return
        # A full queue means the worker still has buffered frames to score, so
        # it is exactly the case where cancelling would throw away real work.
        # Wait for space instead; the timeout below is the only thing allowed to
        # end the worker early.
        try:
            await asyncio.wait_for(
                state.frame_queue.put(_SENTINEL), timeout or self.config.drain_timeout_s
            )
        except asyncio.TimeoutError:
            logger.warning(
                "could not signal end of stream before the drain timeout",
                extra={"extra_fields": {"session_id": session_id}},
            )
        try:
            await asyncio.wait_for(
                asyncio.shield(state.worker), timeout or self.config.drain_timeout_s
            )
        except (asyncio.TimeoutError, asyncio.CancelledError):
            if not state.worker.done():
                state.worker.cancel()
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "analysis worker ended in error",
                extra={"extra_fields": {"session_id": session_id, "error": repr(exc)}},
            )
        finally:
            self.store.release(session_id)

    async def stop(self, session_id: str) -> None:
        """Cancel the worker immediately and release buffered audio."""
        if not self.store.exists(session_id):
            return
        state = self.store.get(session_id)
        if state.worker is not None and not state.worker.done():
            state.worker.cancel()
            try:
                await state.worker
            except (asyncio.CancelledError, Exception):  # noqa: B014
                pass
        self.store.release(session_id)

    async def shutdown(self) -> None:
        """Stop every worker. Called on runtime reset."""
        for session_id in self.store.session_ids():
            await self.stop(session_id)
        self.store.clear()

    def shutdown_sync(self) -> None:
        """Cancel every worker from synchronous code.

        ``L1Runtime.reset`` is called from sync test setup, where there is no
        loop to await on. Cancelling the task is enough: the worker holds no
        resource that needs async teardown, and the store is cleared outright.
        """
        for session_id in self.store.session_ids():
            state = self.store.get(session_id)
            if state.worker is not None and not state.worker.done():
                state.worker.cancel()
        self.store.clear()

    # --- context and linkage -------------------------------------------------

    def ingest_context(self, session_id: str, raw_context: Dict[str, Any]) -> ContextVector:
        """Parse and store call context; the next slow tick will use it."""
        state = self.store.get_or_create(session_id)
        context = self.context_engine.ingest_context(session_id, raw_context or {})
        state.latest_context = context
        self.timeline.append(
            state,
            TimelineEventKind.CONTEXT_INGESTED,
            label="Call context received",
            detail=f"{int(self._completeness(context) * 100)}% of context fields supplied",
        )
        return context

    def link_transaction(self, session_id: str, transaction_id: str) -> None:
        """Associate a demo transaction with this session."""
        state = self.store.get_or_create(session_id)
        state.transaction_id = transaction_id
        self.timeline.append(
            state,
            TimelineEventKind.TRANSACTION_LINKED,
            label="Demo transaction linked to this call",
            transaction_id=transaction_id,
        )

    def record_transaction_event(
        self,
        session_id: str,
        transaction_id: str,
        kind: TimelineEventKind,
        label: str,
        detail: Optional[str] = None,
    ) -> None:
        """Record an operator-initiated transaction change on the call timeline.

        The orchestrator's own auto-hold already appends such an entry. Without
        this, a transaction held by hand would leave no trace in the call's
        narrative, so the audit record would show the automatic holds and
        silently omit the manual ones. It also gives every connected client the
        push it needs, since the REST mutation itself emits no event.

        Never creates analysis state: a transaction acted on outside any session
        has nowhere to write, and inventing a session for it would be worse than
        recording nothing.
        """
        if not self.store.exists(session_id):
            return
        state = self.store.get(session_id)
        entry = self.timeline.append(
            state,
            kind,
            label=label,
            severity=TimelineSeverity.WARNING,
            detail=detail,
            transaction_id=transaction_id,
        )
        self.events.publish_nowait(
            session_id, EventType.TIMELINE_EVENT, entry.model_dump(mode="json")
        )

    @staticmethod
    def _completeness(context: ContextVector) -> float:
        prov = context.provenance
        if not prov:
            return 0.0
        known = sum(1 for p in prov.values() if p.value != "UNAVAILABLE")
        return known / len(prov)

    # --- worker --------------------------------------------------------------

    async def _worker(self, session_id: str) -> None:
        """Drain the frame queue, running the fast and slow clocks."""
        state = self.store.get(session_id)
        try:
            last_processed_frame = None
            while True:
                frame = await state.frame_queue.get()
                if frame is _SENTINEL:
                    break
                last_processed_frame = frame
                if self._should_decimate(state):
                    state.frames_decimated += 1
                    continue
                await self._fast_tick(state, frame)
                if self._slow_due(state, frame):
                    await self._slow_tick(state, frame)

            if state.latest_decision is None and state.latest_belief_fast is not None and last_processed_frame is not None:
                await self._slow_tick(state, last_processed_frame)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 - a worker crash must not be silent
            logger.error(
                "analysis worker failed",
                extra={"extra_fields": {"session_id": session_id, "error": repr(exc)}},
            )
            self.timeline.append(
                state,
                TimelineEventKind.ANALYSIS_DEGRADED,
                label="Voice analysis stopped unexpectedly",
                severity=TimelineSeverity.WARNING,
                detail=f"{type(exc).__name__}; no further assessments will be produced",
            )

    def _should_decimate(self, state: SessionAnalysisState) -> bool:
        """Skip scoring this frame when inference cannot keep up with capture."""
        if not state.decimating:
            return False
        return (state.frames_seen % self.config.decimation_factor) != 0

    def _slow_due(self, state: SessionAnalysisState, frame: FrameObject) -> bool:
        """True when a full slow interval of audio has accumulated.

        The first window is measured from the session's first frame, not from
        an unset marker. Seeding ``last_slow_t`` to -inf would make the very
        first frame look infinitely overdue and fire an action-grade decision
        off a single 250 ms window - the exact thing the two-clock split exists
        to prevent.
        """
        if state.latest_belief_fast is None:
            # Never assess before anything has been scored.
            return False
        if state.last_slow_t == float("-inf"):
            state.last_slow_t = state.session_start_t or frame.t_start
        return (frame.t_end - state.last_slow_t) >= self.config.slow_interval_s

    # --- fast clock ----------------------------------------------------------

    async def _fast_tick(self, state: SessionAnalysisState, frame: FrameObject) -> None:
        """Score one frame: features -> experts -> evidence -> belief."""
        started = time.perf_counter()

        pcm = np.asarray(frame.pcm, dtype=np.float64)
        bundle = self.extractor.extract_bundle(
            pcm,
            sample_rate=frame.sample_rate,
            session_id=frame.session_id,
            frame_id=frame.frame_id,
            include_raw=True,
        )

        # score_all never raises for a valid bundle; a failing expert comes back
        # as a non-OK ExpertResult, which the assembler turns into a None
        # probability rather than a score.
        results = await self.registry.score_all(bundle)
        evidence = self.assembler.assemble(frame, results)
        belief = state.accumulator.update(state.session_id, evidence)

        # The accumulator stamps SLOW unconditionally; a per-frame belief is
        # provisional, so re-stamp rather than let the contract lie.
        belief = belief.model_copy(update={"clock": ClockType.FAST})

        state.latest_evidence = evidence
        state.latest_belief_fast = belief
        state.frames_scored += 1

        self._track_budget(state, (time.perf_counter() - started) * 1000.0)
        self._emit_belief(state, belief, frame)

    def _track_budget(self, state: SessionAnalysisState, elapsed_ms: float) -> None:
        """Engage decimation when fast ticks repeatedly overrun their budget."""
        if elapsed_ms > self.config.fast_tick_budget_ms:
            state.over_budget_streak += 1
            if (
                not state.decimating
                and state.over_budget_streak >= self.config.decimation_trigger
            ):
                state.decimating = True
                logger.warning(
                    "inference cannot keep up with capture; decimating",
                    extra={"extra_fields": {
                        "session_id": state.session_id,
                        "elapsed_ms": round(elapsed_ms, 1),
                        "factor": self.config.decimation_factor,
                    }},
                )
                self.timeline.append(
                    state,
                    TimelineEventKind.ANALYSIS_DEGRADED,
                    label="Analysis running behind live audio",
                    severity=TimelineSeverity.WARNING,
                    detail=(
                        f"Scoring one frame in {self.config.decimation_factor}; "
                        "assessments remain action-grade but cover less audio."
                    ),
                )
        else:
            state.over_budget_streak = 0

    def _emit_belief(
        self, state: SessionAnalysisState, belief: VoiceBelief, frame: FrameObject
    ) -> None:
        self.events.publish_nowait(
            state.session_id,
            EventType.BELIEF_UPDATED,
            {
                "frame_id": frame.frame_id,
                "t_end": frame.t_end,
                "P_spoof": belief.P_spoof,
                "confidence": belief.confidence,
                "band": belief.band.value,
                "clock": belief.clock.value,
                "q_call": belief.q_call,
                "uncertainty_reason": belief.uncertainty_reason,
            },
        )

    # --- slow clock ----------------------------------------------------------

    async def _slow_tick(self, state: SessionAnalysisState, frame: FrameObject) -> None:
        """Produce one action-grade assessment."""
        state.last_slow_t = frame.t_end

        belief = state.latest_belief_fast
        if belief is None:
            return
        belief = belief.model_copy(update={"clock": ClockType.SLOW})
        state.latest_belief_slow = belief

        context = state.latest_context
        if context is None:
            # An empty ingest yields a vector whose every field is UNAVAILABLE,
            # which drives the risk engine to low confidence. Fabricating
            # benign-looking defaults would manufacture confidence instead.
            context = self.context_engine.ingest_context(state.session_id, {})
            state.latest_context = context

        # assess() converts any internal failure into a fail-safe UNCERTAIN
        # decision, so it does not raise. Do not wrap it in a handler that
        # turns that into something confident.
        decision = self.risk.assess(state.session_id, belief, context)

        state.latest_decision = decision
        state.decisions.append(decision)

        t_offset = self._t_offset(state, frame)
        entries = self.timeline.record_decision(state, decision, t_offset_s=t_offset)

        self._emit_risk(state, decision)
        for entry in entries:
            self.events.publish_nowait(
                state.session_id,
                EventType.TIMELINE_EVENT,
                entry.model_dump(mode="json"),
            )

        await self._maybe_apply_action(state, decision, t_offset)

    @staticmethod
    def _t_offset(state: SessionAnalysisState, frame: FrameObject) -> float:
        base = state.session_start_t if state.session_start_t is not None else 0.0
        return max(0.0, frame.t_end - base)

    def _emit_risk(self, state: SessionAnalysisState, decision) -> None:
        self.events.publish_nowait(
            state.session_id,
            EventType.RISK_UPDATED,
            {
                "risk_score": decision.risk.risk_score,
                "risk_band": decision.risk.risk_band.value,
                "risk_confidence": decision.risk.risk_confidence,
                "score_semantics": decision.risk.score_semantics.value,
                "score_label": decision.risk.score_label,
                "action": decision.action.value,
                "matched_policy": decision.matched_policy,
                "reason_codes": list(decision.reason_codes),
                "fail_safe_engaged": decision.fail_safe_engaged,
                "policy_version": decision.policy_version,
                "timestamp": decision.timestamp.isoformat(),
            },
        )
        self.events.publish_nowait(
            state.session_id,
            EventType.DECISION_EMITTED,
            {
                "action": decision.action.value,
                "matched_policy": decision.matched_policy,
                "transaction_tier": int(decision.transaction_tier),
                "recommended_verifications": list(decision.recommended_verifications),
                "timestamp": decision.timestamp.isoformat(),
            },
        )

    async def _maybe_apply_action(
        self, state: SessionAnalysisState, decision, t_offset: Optional[float]
    ) -> None:
        """Apply a HOLD/ESCALATE verdict to the linked demo transaction.

        Debounced on the action itself: the timeline recorder has already
        updated ``last_action``, so this fires once per transition rather than
        on every slow tick that reaches the same conclusion.
        """
        if not self.config.auto_apply_risk_actions:
            return
        if self.transactions is None or state.transaction_id is None:
            return
        if decision.action not in _ACTIONABLE:
            return
        if state.last_applied_action == decision.action:
            return

        try:
            transaction = self.transactions.request_risk_action(
                state.transaction_id,
                decision.action,
                reason=decision.matched_policy,
                reason_codes=list(decision.reason_codes),
                session_id=state.session_id,
            )
        except Exception as exc:  # noqa: BLE001 - a simulator refusal is not an analysis failure
            logger.warning(
                "risk action could not be applied to the demo transaction",
                extra={"extra_fields": {
                    "session_id": state.session_id,
                    "transaction_id": state.transaction_id,
                    "error": repr(exc),
                }},
            )
            return

        state.last_applied_action = decision.action
        self.timeline.append(
            state,
            TimelineEventKind.TRANSACTION_HELD,
            label=f"Demo transaction {transaction.state.value.lower()}",
            severity=TimelineSeverity.CRITICAL,
            detail=f"{decision.action.value} applied by policy {decision.matched_policy}",
            t_offset_s=t_offset,
            risk_band=decision.risk.risk_band,
            action=decision.action,
            transaction_id=state.transaction_id,
        )

    # --- read helpers used by the API ---------------------------------------

    @staticmethod
    def analysis_degraded(state: SessionAnalysisState) -> bool:
        """True when this session's analysis is less than fully informed."""
        return bool(state.degradation_reasons())

    @staticmethod
    def core_experts_available(state: SessionAnalysisState) -> bool:
        """True when at least one core anti-spoofing expert produced a score."""
        evidence = state.latest_evidence
        if evidence is None:
            return False
        return any(
            evidence.expert_statuses.get(eid) == ExpertStatus.OK
            for eid in CORE_SPOOF_EXPERTS
        )

    @staticmethod
    def now() -> datetime:
        return datetime.now(timezone.utc)
