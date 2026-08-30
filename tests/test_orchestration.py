"""Tests for the analysis orchestrator (L1 -> L2 -> L3 -> L4 -> L5 wiring).

The load-bearing test in this file is
``TestDegradedModels::test_no_weights_yields_uncertain_never_low``. With no
model weights vendored - the default CI state - every expert reports
MODEL_UNAVAILABLE, and the only honest output is UNCERTAIN with a step-up. A
regression that turned that into a confident LOW would be invisible to every
other test in the suite and catastrophic in the product.
"""

import asyncio
from datetime import datetime, timezone

import numpy as np
import pytest

from voiceshield.contracts import (
    AuditEventType,
    ClockType,
    DecisionBand,
    EventType,
    FrameObject,
    PolicyAction,
    RiskBand,
    TimelineEventKind,
    TransactionState,
)
from voiceshield.orchestration import (
    AnalysisOrchestrator,
    OrchestrationConfig,
    RiskNotYetAvailable,
    SessionAnalysisStore,
)
from voiceshield.transactions import TransactionSimulator

RATE = 16000
HOP_S = 0.25
FRAME_SAMPLES = int(RATE * HOP_S)


class RecordingSink:
    """Captures published events instead of fanning them out."""

    def __init__(self):
        self.events = []

    def publish_nowait(self, session_id, event_type, data):
        self.events.append((session_id, event_type, data))

    def kinds(self):
        return [event_type for _, event_type, _ in self.events]


def make_frame(session_id="s1", frame_id=0, *, q_t=0.9, voiced=True) -> FrameObject:
    """A frame carrying deterministic synthetic audio."""
    t = np.arange(FRAME_SAMPLES) / RATE
    pcm = 0.3 * np.sin(2 * np.pi * 220.0 * t) if voiced else np.zeros(FRAME_SAMPLES)
    return FrameObject(
        session_id=session_id,
        frame_id=frame_id,
        pcm=pcm.astype(float).tolist(),
        sample_rate=RATE,
        t_start=frame_id * HOP_S,
        t_end=(frame_id + 1) * HOP_S,
        q_t=q_t,
        is_speech=voiced,
        lang_t="en",
        source_type="wav",
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def sink():
    return RecordingSink()


@pytest.fixture
def orchestrator(sink):
    """An orchestrator with a fast slow-clock, so tests do not need long audio."""
    config = OrchestrationConfig(slow_interval_s=0.5)
    return AnalysisOrchestrator(
        store=SessionAnalysisStore(config), events=sink, config=config
    )


async def feed(orchestrator, session_id, count, *, q_t=0.9):
    """Push ``count`` frames through the orchestrator and let them be scored.

    Yields to the event loop between frames. Real ingestion awaits a read
    between frames, so pushing a whole call in one synchronous burst would
    overflow the queue and exercise backpressure instead of the scoring path -
    which is what the dedicated backpressure tests are for.
    """
    await orchestrator.start(session_id)
    for frame_id in range(count):
        orchestrator.on_frame(make_frame(session_id, frame_id, q_t=q_t))
        await asyncio.sleep(0)
    await orchestrator.drain(session_id)
    return orchestrator.store.get(session_id)


# =============================================================================
# The degraded-model principle
# =============================================================================


class TestDegradedModels:
    async def test_no_weights_yields_uncertain_never_low(self, orchestrator):
        """With no experts available the answer must be UNCERTAIN, not LOW.

        This is the single most important assertion in the file. Every expert
        reports MODEL_UNAVAILABLE in CI, and the failure mode being guarded
        against is an orchestrator that fills the gap with a confident zero.
        """
        state = await feed(orchestrator, "s1", 4)

        assert state.latest_decision is not None
        decision = state.latest_decision
        assert decision.risk.risk_band == RiskBand.UNCERTAIN
        assert decision.risk.risk_band not in (RiskBand.LOW, RiskBand.MEDIUM)
        assert decision.action != PolicyAction.ALLOW
        assert decision.fail_safe_engaged

    async def test_the_unavailability_is_named_in_the_reason_codes(self, orchestrator):
        state = await feed(orchestrator, "s1", 4)
        codes = state.latest_decision.reason_codes
        assert any("MODEL_UNAVAILABLE" in code or "INSUFFICIENT" in code for code in codes)

    async def test_a_belief_with_no_experts_carries_no_probability(self, orchestrator):
        """P_spoof must stay None rather than defaulting to 0.0."""
        state = await feed(orchestrator, "s1", 2)
        belief = state.latest_belief_fast
        assert belief is not None
        assert belief.band == DecisionBand.UNCERTAIN
        assert belief.P_spoof is None

    async def test_degradation_is_reported_rather_than_hidden(self, orchestrator):
        state = await feed(orchestrator, "s1", 4)
        reasons = state.degradation_reasons()
        assert reasons
        assert any("MODEL_UNAVAILABLE" in reason for reason in reasons)

    async def test_expert_statuses_are_recorded_for_every_expert(self, orchestrator):
        """Abstaining experts must appear, or the gap becomes invisible."""
        state = await feed(orchestrator, "s1", 2)
        assert set(state.latest_evidence.expert_statuses) == {"E1", "E2", "E3", "E4", "E5", "E6"}


# =============================================================================
# The no-assessment guard
# =============================================================================


class TestNoAssessmentGuard:
    async def test_the_slow_clock_does_not_run_before_any_frame_is_scored(self, orchestrator):
        """An unscored session has no assessment, not a zero-valued one."""
        await orchestrator.start("s1")
        state = orchestrator.store.get("s1")
        assert state.latest_decision is None
        assert not state.has_assessment

    async def test_a_started_session_with_no_audio_produces_nothing(self, orchestrator):
        await orchestrator.start("s1")
        await orchestrator.drain("s1")
        assert orchestrator.store.get("s1").latest_decision is None

    def test_the_typed_error_is_retriable(self):
        """The client should poll; absence of a verdict is not a verdict."""
        exc = RiskNotYetAvailable("s1", frames_seen=3, frames_scored=0)
        assert exc.status_code == 409
        assert exc.retriable is True
        assert "3" in exc.message


# =============================================================================
# The two clocks
# =============================================================================


class TestClocks:
    async def test_the_fast_clock_stamps_fast(self, orchestrator):
        """A per-frame belief is provisional and must say so."""
        state = await feed(orchestrator, "s1", 1)
        assert state.latest_belief_fast.clock == ClockType.FAST

    async def test_the_fast_clock_emits_no_decision(self, orchestrator):
        """One 250 ms window is not action-grade evidence."""
        await orchestrator.start("s1")
        orchestrator.on_frame(make_frame("s1", 0))
        await orchestrator.drain("s1")
        state = orchestrator.store.get("s1")
        assert state.frames_scored == 1
        assert state.latest_decision is None

    async def test_the_slow_clock_stamps_slow(self, orchestrator):
        state = await feed(orchestrator, "s1", 4)
        assert state.latest_belief_slow.clock == ClockType.SLOW

    async def test_the_slow_clock_fires_on_its_interval(self, orchestrator):
        """At 0.5 s spacing and a 0.25 s hop, four frames give two windows."""
        state = await feed(orchestrator, "s1", 8)
        assert len(state.decisions) >= 2

    async def test_the_shared_accumulator_is_not_mutated(self, orchestrator):
        """Re-stamping the clock must not write back into fusion state."""
        state = await feed(orchestrator, "s1", 2)
        internal = state.accumulator.get_current_belief("s1")
        assert internal.clock == ClockType.SLOW


# =============================================================================
# Backpressure
# =============================================================================


class TestBackpressure:
    async def test_a_full_queue_drops_rather_than_blocks(self, sink):
        """Dropping audio is survivable; stalling capture is not."""
        config = OrchestrationConfig(frame_queue_size=2, slow_interval_s=0.5)
        orch = AnalysisOrchestrator(
            store=SessionAnalysisStore(config), events=sink, config=config
        )
        # No worker started, so nothing drains the queue.
        for frame_id in range(10):
            orch.on_frame(make_frame("s1", frame_id))
        state = orch.store.get("s1")
        assert state.frames_seen == 10
        assert state.frames_skipped_backpressure > 0

    async def test_on_frame_never_raises(self, orchestrator):
        """It runs inside the ingestion loop; an exception would kill capture."""
        for frame_id in range(30):
            orchestrator.on_frame(make_frame("s1", frame_id))

    async def test_drops_are_surfaced_as_a_degradation_reason(self, sink):
        config = OrchestrationConfig(frame_queue_size=1, slow_interval_s=0.5)
        orch = AnalysisOrchestrator(
            store=SessionAnalysisStore(config), events=sink, config=config
        )
        for frame_id in range(6):
            orch.on_frame(make_frame("s1", frame_id))
        assert any("BACKPRESSURE" in r for r in orch.store.get("s1").degradation_reasons())


# =============================================================================
# Privacy: no PCM is retained
# =============================================================================


class TestPrivacy:
    async def test_analysis_state_retains_no_audio(self, orchestrator):
        """P2: raw audio must not survive past the ingestion boundary."""
        state = await feed(orchestrator, "s1", 4)
        for attribute in vars(state).values():
            assert not isinstance(attribute, FrameObject)

    async def test_the_evidence_vector_has_no_pcm_field(self, orchestrator):
        state = await feed(orchestrator, "s1", 2)
        assert "pcm" not in state.latest_evidence.model_dump()

    async def test_the_queue_is_drained_on_release(self, orchestrator):
        await orchestrator.start("s1")
        for frame_id in range(4):
            orchestrator.on_frame(make_frame("s1", frame_id))
        await orchestrator.drain("s1")
        assert orchestrator.store.get("s1").frame_queue.empty()

    async def test_no_published_event_carries_audio(self, orchestrator, sink):
        await feed(orchestrator, "s1", 4)
        for _, _, data in sink.events:
            assert "pcm" not in data
            assert "samples" not in data


# =============================================================================
# Events
# =============================================================================


class TestEvents:
    async def test_belief_updates_are_published(self, orchestrator, sink):
        await feed(orchestrator, "s1", 2)
        assert EventType.BELIEF_UPDATED in sink.kinds()

    async def test_risk_updates_are_published_on_the_slow_clock(self, orchestrator, sink):
        await feed(orchestrator, "s1", 4)
        assert EventType.RISK_UPDATED in sink.kinds()
        assert EventType.DECISION_EMITTED in sink.kinds()

    async def test_the_risk_event_carries_the_calibration_labelling(self, orchestrator, sink):
        """A consumer must not be able to read the score as a probability."""
        await feed(orchestrator, "s1", 4)
        payloads = [d for _, kind, d in sink.events if kind == EventType.RISK_UPDATED]
        assert payloads
        assert payloads[-1]["score_semantics"] == "UNCALIBRATED_RISK_SCORE"


# =============================================================================
# Timeline
# =============================================================================


class TestTimeline:
    async def test_analysis_start_is_recorded(self, orchestrator):
        await orchestrator.start("s1")
        kinds = [e.kind for e in orchestrator.store.get("s1").timeline]
        assert TimelineEventKind.ANALYSIS_STARTED in kinds

    async def test_entries_are_appended_on_transitions_not_per_tick(self, orchestrator):
        """A steady call must not generate one row per slow tick."""
        state = await feed(orchestrator, "s1", 20)
        band_entries = [e for e in state.timeline if e.kind == TimelineEventKind.BAND_CHANGED]
        assert len(state.decisions) > len(band_entries)
        assert len(band_entries) == 1

    async def test_sequence_numbers_are_monotonic(self, orchestrator):
        state = await feed(orchestrator, "s1", 8)
        seqs = [e.seq for e in state.timeline]
        assert seqs == sorted(seqs)
        assert len(set(seqs)) == len(seqs)

    async def test_an_uncertain_band_is_not_labelled_as_a_level(self, orchestrator):
        """UNCERTAIN means 'we declined to say', not a rung on the scale."""
        state = await feed(orchestrator, "s1", 4)
        entry = next(e for e in state.timeline if e.kind == TimelineEventKind.BAND_CHANGED)
        assert "insufficient" in entry.label.lower()

    async def test_context_ingestion_is_recorded(self, orchestrator):
        await orchestrator.start("s1")
        orchestrator.ingest_context("s1", {"claimed_identity": "alice"})
        kinds = [e.kind for e in orchestrator.store.get("s1").timeline]
        assert TimelineEventKind.CONTEXT_INGESTED in kinds


# =============================================================================
# Context
# =============================================================================


class TestContext:
    async def test_ingested_context_is_used_by_the_next_assessment(self, orchestrator):
        await orchestrator.start("s1")
        orchestrator.ingest_context("s1", {"claimed_identity": "alice", "amount": 250000})
        for frame_id in range(4):
            orchestrator.on_frame(make_frame("s1", frame_id))
        await orchestrator.drain("s1")
        state = orchestrator.store.get("s1")
        assert state.latest_context.identity.claimed_identity == "alice"
        assert state.latest_decision is not None

    async def test_absent_context_degrades_rather_than_defaults_benignly(self, orchestrator):
        """An empty context must lower confidence, not read as 'all clear'."""
        state = await feed(orchestrator, "s1", 4)
        assert state.latest_context is not None
        assert state.latest_decision.risk.context_degraded


# =============================================================================
# Auto-applied risk actions
# =============================================================================


class TestAutoAction:
    def _orchestrator(self, sink, simulator, **overrides):
        config = OrchestrationConfig(slow_interval_s=0.5, **overrides)
        return AnalysisOrchestrator(
            store=SessionAnalysisStore(config),
            events=sink,
            transactions=simulator,
            config=config,
        )

    async def test_a_model_outage_holds_a_tier_four_transaction(self, sink):
        """The fail-safe reaching the transaction, end to end.

        With no context supplied the tier defaults to TIER_4 (privileged
        authorisation), where P-MODEL-UNAVAILABLE mandates HOLD rather than a
        step-up. Knocking out the detector must not buy an attacker a clean
        channel to a privileged action.
        """
        simulator = TransactionSimulator()
        orch = self._orchestrator(sink, simulator)
        txn = simulator.create_transaction(
            caller_identity="alice", amount="1000", beneficiary="b", session_id="s1"
        )
        orch.link_transaction("s1", txn.transaction_id)
        state = await feed(orch, "s1", 4)

        assert state.latest_decision.matched_policy == "P-MODEL-UNAVAILABLE"
        assert state.latest_decision.action == PolicyAction.HOLD
        assert simulator.get_transaction(txn.transaction_id).state == TransactionState.HELD

    async def test_a_low_tier_request_is_not_held_during_an_outage(self, sink):
        """Proportionality survives the outage: a balance enquiry still passes.

        Same missing models, but a declared tier-0 request. The action is a
        warning, which is not an objection to the transaction, so the state
        machine must not move.
        """
        simulator = TransactionSimulator()
        orch = self._orchestrator(sink, simulator)
        txn = simulator.create_transaction(
            caller_identity="alice", amount="50", beneficiary="self", session_id="s1"
        )
        orch.link_transaction("s1", txn.transaction_id)
        await orch.start("s1")
        orch.ingest_context("s1", {"transaction_type": "BALANCE_ENQUIRY"})
        for frame_id in range(4):
            orch.on_frame(make_frame("s1", frame_id))
            await asyncio.sleep(0)
        await orch.drain("s1")

        assert orch.store.get("s1").latest_decision.action == PolicyAction.WARN
        assert simulator.get_transaction(txn.transaction_id).state == TransactionState.PENDING

    async def test_linking_a_transaction_is_recorded(self, sink):
        simulator = TransactionSimulator()
        orch = self._orchestrator(sink, simulator)
        txn = simulator.create_transaction(caller_identity="a", amount="1", beneficiary="b")
        orch.link_transaction("s1", txn.transaction_id)
        kinds = [e.kind for e in orch.store.get("s1").timeline]
        assert TimelineEventKind.TRANSACTION_LINKED in kinds

    async def test_the_coupling_can_be_disabled(self, sink):
        simulator = TransactionSimulator()
        orch = self._orchestrator(sink, simulator, auto_apply_risk_actions=False)
        assert orch.config.auto_apply_risk_actions is False

    async def test_a_hold_is_applied_once_not_per_tick(self, sink):
        """Debounce: a verdict holding steady must not re-fire every 1.5 s."""
        simulator = TransactionSimulator()
        orch = self._orchestrator(sink, simulator)
        txn = simulator.create_transaction(
            caller_identity="alice", amount="1000", beneficiary="b", session_id="s1"
        )
        orch.link_transaction("s1", txn.transaction_id)
        state = orch.store.get("s1")

        # Drive the action path directly: with no weights the real verdict is
        # STEP_UP, so a synthetic HOLD is the only way to exercise debouncing.
        class _Decision:
            action = PolicyAction.HOLD
            matched_policy = "P-TEST"
            reason_codes = ["TEST"]

            class risk:
                risk_band = RiskBand.CRITICAL

        await orch._maybe_apply_action(state, _Decision(), 1.0)
        await orch._maybe_apply_action(state, _Decision(), 2.0)

        # One dispatch produces exactly one RISK_ACTION_REQUESTED. Counting by
        # risk_action alone would double-count, since the resulting HOLD_PLACED
        # carries the same field.
        trail = simulator.get_audit_trail(txn.transaction_id)
        requested = [e for e in trail if e.event_type == AuditEventType.RISK_ACTION_REQUESTED]
        assert len(requested) == 1
        assert simulator.get_transaction(txn.transaction_id).state == TransactionState.HELD


# =============================================================================
# Lifecycle and isolation
# =============================================================================


class TestLifecycle:
    async def test_sessions_do_not_share_state(self, orchestrator):
        await feed(orchestrator, "s1", 4)
        await feed(orchestrator, "s2", 2)
        assert orchestrator.store.get("s1").frames_scored != orchestrator.store.get("s2").frames_scored

    async def test_conclusions_survive_the_session_ending(self, orchestrator):
        """/risk must still answer after a call ends; only audio is released."""
        state = await feed(orchestrator, "s1", 4)
        decision = state.latest_decision
        orchestrator.store.release("s1")
        assert orchestrator.store.get("s1").latest_decision is decision

    async def test_stop_cancels_the_worker(self, orchestrator):
        await orchestrator.start("s1")
        await orchestrator.stop("s1")
        assert orchestrator.store.get("s1").worker.done()

    async def test_shutdown_clears_every_session(self, orchestrator):
        await orchestrator.start("s1")
        await orchestrator.start("s2")
        await orchestrator.shutdown()
        assert orchestrator.store.session_ids() == []

    async def test_draining_an_unknown_session_is_a_no_op(self, orchestrator):
        await orchestrator.drain("never-existed")

    async def test_a_worker_crash_is_recorded_not_swallowed(self, orchestrator, monkeypatch):
        async def boom(*_a, **_k):
            raise RuntimeError("simulated expert failure")

        monkeypatch.setattr(orchestrator.registry, "score_all", boom)
        await orchestrator.start("s1")
        orchestrator.on_frame(make_frame("s1", 0))
        await orchestrator.drain("s1")

        state = orchestrator.store.get("s1")
        assert state.latest_decision is None
        assert any(e.kind == TimelineEventKind.ANALYSIS_DEGRADED for e in state.timeline)
