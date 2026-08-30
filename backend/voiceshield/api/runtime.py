"""Process-local L1 runtime: session manager, pipeline and event fan-out.

Holds the single SessionManager and L1IngestionPipeline the API process uses, so
WebSocket handlers and REST routes address the same sessions.

This module owns no scoring state. Events carry ingestion telemetry only.
"""

import asyncio
from datetime import datetime, timezone
from typing import Callable, Dict, Optional, Set

from voiceshield.contracts.events import EventType, WebSocketEventEnvelope
from voiceshield.ingestion.pipeline import L1IngestionPipeline
from voiceshield.ingestion.publisher import InMemoryFramePublisher
from voiceshield.ingestion.session import SessionManager
from voiceshield.obs.logging import get_logger
from voiceshield.orchestration import AnalysisOrchestrator
from voiceshield.transactions import TransactionSimulator

logger = get_logger("voiceshield.api.runtime")


class EventBus:
    """Per-session fan-out of WebSocketEventEnvelopes with monotonic seq (§8.2)."""

    def __init__(self, sessions: SessionManager, max_queue: int = 512):
        self._sessions = sessions
        self._subscribers: Dict[str, Set[asyncio.Queue]] = {}
        self._max_queue = max_queue

    def subscribe(self, session_id: str) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=self._max_queue)
        self._subscribers.setdefault(session_id, set()).add(queue)
        return queue

    def unsubscribe(self, session_id: str, queue: asyncio.Queue) -> None:
        subs = self._subscribers.get(session_id)
        if not subs:
            return
        subs.discard(queue)
        if not subs:
            self._subscribers.pop(session_id, None)

    def build(self, session_id: str, event_type: EventType, data: dict) -> WebSocketEventEnvelope:
        try:
            seq = self._sessions.get(session_id).next_seq()
        except Exception:
            seq = 0
        return WebSocketEventEnvelope(
            seq=seq,
            session_id=session_id,
            event_type=event_type,
            timestamp=datetime.now(timezone.utc),
            data=data,
        )

    def publish_nowait(self, session_id: str, event_type: EventType, data: dict) -> None:
        """Fan out without ever blocking the ingestion path."""
        envelope = self.build(session_id, event_type, data)
        for queue in list(self._subscribers.get(session_id, ())):
            try:
                queue.put_nowait(envelope)
            except asyncio.QueueFull:
                # A slow client must not stall capture; it detects the gap via seq.
                pass


class L1Runtime:
    """Container for the process-local L1 objects."""

    def __init__(self) -> None:
        self.sessions = SessionManager()
        self.publisher = InMemoryFramePublisher()
        self.pipeline = L1IngestionPipeline(
            session_manager=self.sessions, publisher=self.publisher
        )
        self.events = EventBus(self.sessions)
        #: DEMO TRANSACTION ENVIRONMENT. Simulated only - no funds move and no
        #: external banking system is contacted.
        self.transactions = TransactionSimulator()
        #: L1 -> L2 -> L3 -> L4 -> L5 wiring. EventBus satisfies the EventSink
        #: protocol structurally, so orchestration never imports this module.
        self.orchestrator = AnalysisOrchestrator(
            events=self.events, transactions=self.transactions
        )
        #: Strong references to detached background tasks.
        #:
        #: asyncio only holds a WEAK reference to a task, so a fire-and-forget
        #: `create_task(...)` whose result nobody keeps can be garbage collected
        #: mid-run. That failure is silent and intermittent: the replay stops
        #: partway and the session simply never produces an assessment.
        self._background: Set[asyncio.Task] = set()

    def reset(self) -> None:
        """Drop all state. Used between tests; never on a live process.

        Cancels running analysis workers first: ``__init__`` would otherwise
        rebind ``orchestrator`` and orphan its tasks, which then keep scoring
        against a store nothing reads.
        """
        self.orchestrator.shutdown_sync()
        self.__init__()

    def spawn(self, coro) -> asyncio.Task:
        """Run a coroutine detached, keeping it alive until it finishes."""
        task = asyncio.create_task(coro)
        self._background.add(task)
        task.add_done_callback(self._background.discard)
        return task

    def make_frame_sink(self, session_id: str) -> Callable[[object], None]:
        """Build the on_frame callback every audio path must use.

        Shared deliberately. If one ingestion path published FRAME_PROCESSED and
        another did not, sessions fed by the second would silently lose the only
        source of live language and per-frame quality - a divergence that is
        invisible until someone asks why the Call panel is blank.

        Both calls are non-blocking by contract: this runs inside the ingestion
        loop, so anything slow here stalls capture.
        """

        def _on_frame(frame) -> None:
            self.events.publish_nowait(
                session_id, EventType.FRAME_PROCESSED, frame_telemetry(frame)
            )
            self.orchestrator.on_frame(frame)

        return _on_frame


_runtime: Optional[L1Runtime] = None


def get_runtime() -> L1Runtime:
    """Return the process-local L1 runtime, creating it on first use."""
    global _runtime
    if _runtime is None:
        _runtime = L1Runtime()
    return _runtime


def reset_runtime() -> L1Runtime:
    """Replace the runtime with a fresh one (test helper)."""
    global _runtime
    _runtime = L1Runtime()
    return _runtime


def frame_telemetry(frame) -> dict:
    """Frame telemetry for the events channel.

    An explicit whitelist, not a model dump: FrameObject carries PCM, and a
    field added to it must never start being broadcast by accident (P2).
    """
    return {
        "frame_id": frame.frame_id,
        "t_start": frame.t_start,
        "t_end": frame.t_end,
        "is_speech": frame.is_speech,
        "q_t": frame.q_t,
        "packet_loss": frame.packet_loss,
        "bandwidth": frame.bandwidth,
        "lang_t": frame.lang_t,
        "source_type": frame.source_type,
    }
