"""Orchestration cadence and coupling configuration.

Every tunable the analysis orchestrator honours lives here. Nothing in
:mod:`voiceshield.orchestration.analysis` hard-codes a cadence, a queue depth or
a coupling decision, because those are the knobs an operator needs to see
without reading the worker loop.
"""

import dataclasses


@dataclasses.dataclass(frozen=True)
class OrchestrationConfig:
    """Configuration for the per-session analysis worker."""

    #: Frames buffered between L1 and the scoring worker. Eight frames at the
    #: 250 ms hop is ~2 s of audio: enough to ride out one slow expert call
    #: without letting the backlog grow into a stale-analysis problem.
    frame_queue_size: int = 8

    #: Slow (action-grade) clock interval. Spec §8.3 calls for a 1-3 s rolling
    #: window; 1.5 s sits inside that and keeps the demo visibly responsive.
    slow_interval_s: float = 1.5

    #: Budget for one fast tick. Exceeding it repeatedly means inference cannot
    #: keep up with capture, and the worker starts decimating rather than
    #: letting the queue overflow silently.
    fast_tick_budget_ms: float = 400.0

    #: Consecutive over-budget fast ticks before decimation engages.
    decimation_trigger: int = 3

    #: Score every k-th frame while decimating.
    decimation_factor: int = 3

    #: Bounded history depths. Both are per session and both are reported as
    #: truncated once they wrap, so a reader never mistakes a clipped history
    #: for a complete one.
    decision_history: int = 64
    timeline_history: int = 256

    #: Apply a HOLD/ESCALATE verdict to a linked demo transaction.
    #:
    #: True for the demo, where the point is showing the verdict is
    #: consequential. Kept as a flag so the coupling is a visible choice rather
    #: than a hidden side effect: with it off, the orchestrator is a pure
    #: assessor and an operator must apply the action explicitly.
    auto_apply_risk_actions: bool = True

    #: Seconds to wait for in-flight scoring when a session stops.
    #:
    #: Sized against real inference, not intuition: with E2 and E4 weights
    #: vendored, one fast tick costs a few hundred milliseconds on CPU, so a
    #: full queue can legitimately need well over five seconds to clear. The
    #: old 5 s budget cancelled the worker mid-queue and silently discarded
    #: frames that had already been captured.
    #:
    #: A drain that still times out leaves the last frames unscored, which is
    #: correct - it never synthesises a final score to fill the gap.
    drain_timeout_s: float = 30.0
