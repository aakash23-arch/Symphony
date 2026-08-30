"""Frame publishing (C-14).

Publishes FrameObjects to the short-lived raw-audio buffer. The publisher never
waits for a consumer: when the sink is full, frames are dropped OLDEST-FIRST and
backpressure is reported. Capture never blocks.

The frozen design targets a Redis stream (XADD vs:frames MAXLEN ~ N). This build
ships the in-memory queue sanctioned for all-in-one mode; a Redis implementation
is a drop-in behind the same protocol.
"""

import asyncio
from typing import List, Optional, Protocol, runtime_checkable

from voiceshield.config import settings
from voiceshield.contracts.frame import FrameObject
from voiceshield.obs.logging import get_logger

from .errors import INGEST_BACKPRESSURE

logger = get_logger("voiceshield.ingestion.publisher")


@runtime_checkable
class FramePublisher(Protocol):
    """Sink for assembled FrameObjects."""

    async def publish(self, frame: FrameObject) -> None:
        """Publish a frame. Must never block capture."""
        ...

    async def close(self) -> None:
        """Release any sink resources."""
        ...


class InMemoryFramePublisher:
    """Bounded in-memory frame sink (all-in-one fallback for C-14).

    PCM lives here and only here: it is never written to SQLite or to a durable
    file (§12.1).
    """

    def __init__(self, maxlen: Optional[int] = None):
        self.maxlen = maxlen if maxlen is not None else settings.redis_stream_maxlen
        self._queue: asyncio.Queue = asyncio.Queue()
        self.dropped_frames = 0
        self.published_count = 0

    async def publish(self, frame: FrameObject) -> None:
        while self._queue.qsize() >= self.maxlen:
            try:
                self._queue.get_nowait()
                self.dropped_frames += 1
            except asyncio.QueueEmpty:
                break
        if self.dropped_frames and self.dropped_frames % max(self.maxlen, 1) == 0:
            logger.warning(
                "Frame sink saturated; dropping oldest frames",
                extra={
                    "extra_fields": {
                        "code": INGEST_BACKPRESSURE,
                        "session_id": frame.session_id,
                        "dropped_frames": self.dropped_frames,
                    }
                },
            )
        self._queue.put_nowait(frame)
        self.published_count += 1

    async def get(self) -> FrameObject:
        return await self._queue.get()

    def drain(self) -> List[FrameObject]:
        """Remove and return every buffered frame, oldest first."""
        frames: List[FrameObject] = []
        while True:
            try:
                frames.append(self._queue.get_nowait())
            except asyncio.QueueEmpty:
                break
        return frames

    @property
    def pending(self) -> int:
        return self._queue.qsize()

    async def close(self) -> None:
        self.drain()
