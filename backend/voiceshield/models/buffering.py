"""Rolling PCM buffer for experts needing more audio than one frame (C-23).

WHY THIS EXISTS
    ``settings.audio_hop_ms`` is 250 ms, so a FrameObject carries 4000 samples.
    WavLMForXVector needs at least 4880 samples (0.305 s) - MEASURED, it raises
    below that. E4 therefore cannot score a single frame and must accumulate
    audio across frames.

STRIDE
    A 2 s window advanced by 250 ms is 87.5% the same audio as the previous one.
    Re-embedding every frame would spend roughly 1.4 CPU-seconds per wall-second
    producing eight near-identical scores. So E4 re-scores on a stride and
    abstains in between, with a reason code that distinguishes "warming up"
    (INSUFFICIENT_AUDIO) from "deliberately holding" (E4_STRIDE_SKIP).

Whether L4 carries the last E4 value forward between emissions is L4's decision.
L3's job is to say honestly that it has nothing new.
"""

from __future__ import annotations

import threading
from collections import OrderedDict, deque
from typing import Deque, Dict, Optional

import numpy as np

from voiceshield.config import settings
from voiceshield.obs.logging import get_logger

logger = get_logger("voiceshield.models.buffering")


class RollingPCMBuffer:
    """Per-session rolling PCM window with an LRU cap on sessions.

    Thread-safe: buffers are written from the registry's inference threads.
    """

    def __init__(
        self,
        buffer_ms: Optional[int] = None,
        sample_rate: Optional[int] = None,
        max_sessions: Optional[int] = None,
        stride_ms: Optional[int] = None,
        min_samples: Optional[int] = None,
    ):
        self.sample_rate = sample_rate or settings.audio_sample_rate
        self.buffer_ms = buffer_ms if buffer_ms is not None else settings.e4_buffer_ms
        self.stride_ms = stride_ms if stride_ms is not None else settings.e4_stride_ms
        self.min_samples = min_samples if min_samples is not None else settings.e4_min_samples
        self.max_sessions = max_sessions or settings.e4_max_sessions

        self.capacity = max(1, int(self.buffer_ms * self.sample_rate / 1000))
        self._stride_samples = max(0, int(self.stride_ms * self.sample_rate / 1000))

        self._buffers: "OrderedDict[str, Deque[float]]" = OrderedDict()
        # Samples consumed at the last emission, per session.
        self._last_emit: Dict[str, int] = {}
        self._total_seen: Dict[str, int] = {}
        self._lock = threading.Lock()

    def append(self, session_id: str, pcm: np.ndarray) -> None:
        """Add a frame's audio, evicting the oldest samples beyond capacity."""
        arr = np.asarray(pcm, dtype=np.float32).ravel()
        if arr.size == 0:
            return

        with self._lock:
            buf = self._buffers.get(session_id)
            if buf is None:
                if len(self._buffers) >= self.max_sessions:
                    evicted, _ = self._buffers.popitem(last=False)
                    self._last_emit.pop(evicted, None)
                    self._total_seen.pop(evicted, None)
                    logger.warning(
                        "evicted oldest session PCM buffer at capacity",
                        extra={"extra_fields": {"evicted_session": evicted, "cap": self.max_sessions}},
                    )
                buf = deque(maxlen=self.capacity)
                self._buffers[session_id] = buf
                self._total_seen[session_id] = 0

            buf.extend(arr.tolist())
            self._buffers.move_to_end(session_id)
            self._total_seen[session_id] = self._total_seen.get(session_id, 0) + int(arr.size)

    def get(self, session_id: str) -> Optional[np.ndarray]:
        """Current window as a contiguous array, or None if the session is unknown."""
        with self._lock:
            buf = self._buffers.get(session_id)
            if buf is None:
                return None
            return np.fromiter(buf, dtype=np.float32, count=len(buf))

    def is_ready(self, session_id: str) -> bool:
        """True once enough audio has accumulated to embed at all."""
        with self._lock:
            buf = self._buffers.get(session_id)
            return buf is not None and len(buf) >= self.min_samples

    def should_emit(self, session_id: str) -> bool:
        """True when the stride has elapsed since the last emission."""
        with self._lock:
            if session_id not in self._buffers:
                return False
            if len(self._buffers[session_id]) < self.min_samples:
                return False
            seen = self._total_seen.get(session_id, 0)
            last = self._last_emit.get(session_id)
            if last is None:
                return True
            return (seen - last) >= self._stride_samples

    def mark_emitted(self, session_id: str) -> None:
        """Record that a score was produced, restarting the stride."""
        with self._lock:
            self._last_emit[session_id] = self._total_seen.get(session_id, 0)

    def release(self, session_id: str) -> None:
        """Drop a session's buffer. Must be called at session end or this leaks."""
        with self._lock:
            self._buffers.pop(session_id, None)
            self._last_emit.pop(session_id, None)
            self._total_seen.pop(session_id, None)

    def clear(self) -> None:
        with self._lock:
            self._buffers.clear()
            self._last_emit.clear()
            self._total_seen.clear()

    @property
    def session_count(self) -> int:
        with self._lock:
            return len(self._buffers)
