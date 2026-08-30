"""Frame assembly and jitter buffering (C-06).

Accumulates source chunks into fixed-duration frames carrying a monotonic
frame_id and exact t_start/t_end. Does not resample, normalise, or classify.

Timestamps are derived from cumulative SAMPLE COUNTS, never from wall clock, so
they stay monotonic and exactly contiguous regardless of playback speed or
scheduling jitter.
"""

from collections import deque
from dataclasses import dataclass
from typing import Deque, Iterator, List, Optional

from voiceshield.config import settings

from .errors import INGEST_BACKPRESSURE


@dataclass
class RawFrame:
    """A timestamped, fixed-size block of raw source bytes (pre-normalisation)."""

    frame_id: int
    data: bytes
    sample_rate: int
    channels: int
    encoding: str
    t_start: float
    t_end: float
    #: Fraction [0,1] of this frame's expected duration that never arrived.
    packet_loss: float = 0.0
    #: True when the frame is short because the stream ended mid-frame.
    partial: bool = False
    #: Samples per channel actually carried by this frame.
    sample_count: int = 0


class FrameAssembler:
    """Accumulate chunks into fixed-duration frames with monotonic ids and timestamps.

    Underruns are reported through ``packet_loss`` on the emitted frame; audio is
    never zero-padded silently and continuity is never fabricated.
    """

    def __init__(
        self,
        sample_rate: int,
        channels: int = 1,
        encoding: str = "pcm_s16le",
        frame_ms: Optional[int] = None,
        bytes_per_sample: int = 2,
        max_buffered_frames: int = 64,
    ):
        if sample_rate <= 0:
            raise ValueError("sample_rate must be positive")

        self.sample_rate = sample_rate
        self.channels = max(channels, 1)
        self.encoding = encoding
        self.frame_ms = frame_ms if frame_ms is not None else settings.audio_hop_ms
        self.bytes_per_sample = bytes_per_sample
        self.max_buffered_frames = max_buffered_frames

        #: Samples (per channel) in one emitted frame.
        self.frame_samples = int(round(self.sample_rate * self.frame_ms / 1000.0))
        if self.frame_samples <= 0:
            raise ValueError("frame_ms too small for the given sample rate")
        self.frame_bytes = self.frame_samples * self.channels * self.bytes_per_sample
        self.frame_duration_s = self.frame_samples / self.sample_rate

        self._buffer = bytearray()
        self._next_frame_id = 0
        #: Samples consumed so far, the sole basis for timestamps.
        self._samples_emitted = 0
        #: Samples known to be missing (declared gaps), for packet_loss accounting.
        self._pending_gap_samples = 0

        self._jitter: Deque[RawFrame] = deque(maxlen=max_buffered_frames)
        self.dropped_frames = 0
        self.underrun_frames = 0

    # -- ingest ---------------------------------------------------------------

    def push(self, data: bytes) -> List[RawFrame]:
        """Add a source chunk; return every complete frame it made available."""
        if data:
            self._buffer.extend(data)
        return self._drain()

    def declare_gap(self, missing_bytes: int) -> None:
        """Record a known mid-stream gap (C-04) without inventing audio for it."""
        if missing_bytes <= 0:
            return
        per_sample = self.channels * self.bytes_per_sample
        self._pending_gap_samples += missing_bytes // per_sample

    def _drain(self) -> List[RawFrame]:
        frames: List[RawFrame] = []
        while len(self._buffer) >= self.frame_bytes:
            payload = bytes(self._buffer[: self.frame_bytes])
            del self._buffer[: self.frame_bytes]
            frames.append(self._make_frame(payload, self.frame_samples))
        return frames

    def flush(self) -> List[RawFrame]:
        """Emit any trailing partial frame at stream end, marked as partial.

        The residue is emitted at its true length with packet_loss reflecting the
        missing portion. It is not zero-padded up to a full frame.
        """
        if not self._buffer:
            return []
        payload = bytes(self._buffer)
        self._buffer.clear()
        per_sample = self.channels * self.bytes_per_sample
        samples = len(payload) // per_sample
        if samples == 0:
            return []
        frame = self._make_frame(payload, samples, partial=True)
        return [frame]

    def _make_frame(self, payload: bytes, samples: int, partial: bool = False) -> RawFrame:
        t_start = self._samples_emitted / self.sample_rate
        t_end = (self._samples_emitted + samples) / self.sample_rate

        # A frame carrying fewer samples than nominal, or following a declared
        # gap, is an underrun: report it, do not conceal it.
        gap = min(self._pending_gap_samples, self.frame_samples)
        self._pending_gap_samples -= gap
        shortfall = max(self.frame_samples - samples, 0) if partial else 0
        lost_samples = gap + shortfall
        packet_loss = min(lost_samples / self.frame_samples, 1.0) if self.frame_samples else 0.0
        if packet_loss > 0:
            self.underrun_frames += 1

        frame = RawFrame(
            frame_id=self._next_frame_id,
            data=payload,
            sample_rate=self.sample_rate,
            channels=self.channels,
            encoding=self.encoding,
            t_start=t_start,
            t_end=t_end,
            packet_loss=packet_loss,
            partial=partial,
            sample_count=samples,
        )
        self._next_frame_id += 1
        self._samples_emitted += samples
        return frame

    # -- jitter buffer --------------------------------------------------------

    def buffer_frame(self, frame: RawFrame) -> Optional[str]:
        """Queue a frame in the bounded jitter buffer.

        On overflow the OLDEST frame is dropped so that capture never blocks
        (C-14). Returns INGEST_BACKPRESSURE when a drop occurred.
        """
        overflowed = len(self._jitter) >= self.max_buffered_frames
        if overflowed:
            self._jitter.popleft()
            self.dropped_frames += 1
        self._jitter.append(frame)
        return INGEST_BACKPRESSURE if overflowed else None

    def pop_buffered(self) -> Optional[RawFrame]:
        """Remove and return the oldest buffered frame, if any."""
        if not self._jitter:
            return None
        return self._jitter.popleft()

    def drain_buffered(self) -> Iterator[RawFrame]:
        while self._jitter:
            yield self._jitter.popleft()

    @property
    def buffered_count(self) -> int:
        return len(self._jitter)

    @property
    def next_frame_id(self) -> int:
        return self._next_frame_id
