"""Real-time replay simulator (demo/development source per reference §4.1).

Replays an audio file as if it were arriving live: chunks are paced in wall-clock
time so downstream code sees a stream, not a batch job.

Guarantees:
  * Timestamps are monotonically increasing and exactly contiguous, because they
    are derived from cumulative sample counts inside the FrameAssembler, never
    from the wall clock. Playback speed therefore cannot perturb them.
  * Playback speed is configurable; speed <= 0 means "as fast as possible",
    which is what makes replay-driven tests deterministic.
  * start / stop / error states are explicit and observable.

The simulator classifies nothing and scores nothing: it is a transport.
"""

import asyncio
from enum import Enum
from pathlib import Path
from typing import Callable, List, Optional

from voiceshield.contracts import FrameObject
from voiceshield.ingestion.errors import SourceUnavailable
from voiceshield.ingestion.pipeline import L1IngestionPipeline
from voiceshield.ingestion.publisher import FramePublisher
from voiceshield.ingestion.session import SessionManager, SessionState
from voiceshield.ingestion.sources import WavFileSource
from voiceshield.obs.logging import get_logger

logger = get_logger("voiceshield.demo.replay")


class ReplayState(str, Enum):
    """Observable simulator states (start/stop/error)."""

    IDLE = "IDLE"
    RUNNING = "RUNNING"
    STOPPING = "STOPPING"
    STOPPED = "STOPPED"
    ERROR = "ERROR"


class ReplaySimulator:
    """Replay a WAV file through the L1 pipeline as a live stream."""

    def __init__(
        self,
        path,
        pipeline: Optional[L1IngestionPipeline] = None,
        session_manager: Optional[SessionManager] = None,
        publisher: Optional[FramePublisher] = None,
        speed: float = 1.0,
        frame_ms: Optional[int] = None,
        session_id: Optional[str] = None,
        scenario_id: Optional[str] = None,
    ):
        self.path = Path(path)
        self.speed = speed
        self.frame_ms = frame_ms
        self.scenario_id = scenario_id

        if pipeline is not None:
            self.pipeline = pipeline
        else:
            self.pipeline = L1IngestionPipeline(
                session_manager=session_manager,
                publisher=publisher,
                frame_ms=frame_ms,
            )
        self.sessions = self.pipeline.sessions

        self._state = ReplayState.IDLE
        self._error: Optional[str] = None
        self._stop_event = asyncio.Event()
        self._task: Optional[asyncio.Task] = None
        self._source: Optional[WavFileSource] = None

        if session_id is not None and self.sessions.exists(session_id):
            self.session_id = session_id
        else:
            self.session_id = self.sessions.create(
                source_type="wav", scenario_id=scenario_id, session_id=session_id
            ).session_id

        self.frames_published = 0

    # -- observable state -----------------------------------------------------

    @property
    def state(self) -> ReplayState:
        return self._state

    @property
    def error(self) -> Optional[str]:
        """Reason code retained after a failure, or None."""
        return self._error

    @property
    def is_running(self) -> bool:
        return self._state is ReplayState.RUNNING

    @property
    def session_state(self) -> SessionState:
        return self.sessions.get(self.session_id).state

    # -- control --------------------------------------------------------------

    async def run(self, on_frame: Optional[Callable[[FrameObject], None]] = None) -> int:
        """Replay to completion in the caller's task. Returns frames published."""
        if self._state is ReplayState.RUNNING:
            return self.frames_published

        self._stop_event = asyncio.Event()
        self._error = None
        self._state = ReplayState.RUNNING
        self._source = WavFileSource(
            self.path, speed=self.speed, realtime=self.speed > 0
        )

        try:
            self.frames_published = await self.pipeline.run(
                self.session_id,
                self._source,
                chunk_ms=self.frame_ms,
                on_frame=on_frame,
                stop_event=self._stop_event,
            )
        except SourceUnavailable as exc:
            self._state = ReplayState.ERROR
            self._error = exc.code
            logger.error(
                "Replay failed to open source",
                extra={"extra_fields": {"code": exc.code, "session_id": self.session_id}},
            )
            raise
        except Exception as exc:
            self._state = ReplayState.ERROR
            self._error = "REPLAY_FAILED"
            logger.error(
                "Replay failed",
                extra={"extra_fields": {"session_id": self.session_id, "error": str(exc)}},
            )
            raise

        self._state = ReplayState.STOPPED
        return self.frames_published

    async def start(self, on_frame: Optional[Callable[[FrameObject], None]] = None) -> None:
        """Start replay in a background task. Idempotent while already running."""
        if self._task is not None and not self._task.done():
            return
        self._task = asyncio.create_task(self._guarded_run(on_frame))
        # Let the task reach its first await so state is observable on return.
        await asyncio.sleep(0)

    async def _guarded_run(self, on_frame: Optional[Callable[[FrameObject], None]]) -> int:
        try:
            return await self.run(on_frame)
        except Exception:
            # State and error are already recorded by run(); a background replay
            # must not raise into the event loop.
            return self.frames_published

    async def stop(self) -> None:
        """Request a clean stop and wait for the replay task to drain. Idempotent."""
        if self._state is ReplayState.RUNNING:
            self._state = ReplayState.STOPPING
        self._stop_event.set()

        if self._task is not None:
            try:
                await self._task
            except Exception:
                pass
            self._task = None

        if self._source is not None:
            await self._source.close()

        if self._state is not ReplayState.ERROR:
            self._state = ReplayState.STOPPED

        record = self.sessions.get(self.session_id)
        if not record.is_terminal:
            self.sessions.stop(self.session_id)

    async def collect(self) -> List[FrameObject]:
        """Replay to completion and return every frame, in order.

        Used by deterministic tests: pair with speed<=0 for instant replay.
        """
        frames: List[FrameObject] = []
        await self.run(on_frame=frames.append)
        return frames
