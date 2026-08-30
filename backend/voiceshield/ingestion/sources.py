"""Audio source interfaces and implementations (C-01, C-02, C-03, C-04).

Every source implements one protocol so that adding SIP/RTP later means adding
one class and rewriting nothing in L2-L5 (§1.3). Sources yield raw bytes and
descriptors only: they do not decode, resample, buffer, or detect speech.
"""

import asyncio
import time
import wave
from abc import ABC, abstractmethod
from pathlib import Path
from typing import AsyncIterator, Optional

import numpy as np

from .errors import (
    FIXTURE_MISSING,
    NO_CAPTURE_DEVICE,
    SOURCE_UNAVAILABLE,
    SourceUnavailable,
)

# Supported PCM encodings for raw byte payloads.
PCM_S16LE = "pcm_s16le"
PCM_F32LE = "pcm_f32le"
SUPPORTED_ENCODINGS = (PCM_S16LE, PCM_F32LE)

BYTES_PER_SAMPLE = {PCM_S16LE: 2, PCM_F32LE: 4}


class AudioSource(ABC):
    """Abstract interface for audio ingestion sources (WAV, Mic, WebSocket, SIP/RTP).

    Static descriptors (C-01) describe the native stream; they are set by concrete
    implementations once ``open()`` has succeeded.
    """

    #: Opaque origin tag that survives into FrameObject.source_type (§6.1).
    source_type: str = "unknown"
    #: Native sample rate of the underlying stream, in Hz.
    native_sample_rate: int = 0
    #: Native channel count of the underlying stream.
    channels: int = 0
    #: Byte encoding of chunks returned by read_chunk().
    encoding: str = PCM_S16LE

    @abstractmethod
    async def open(self) -> None:
        """Open audio source and initialize acquisition."""
        raise NotImplementedError("AudioSource.open must be implemented by concrete sources")

    @abstractmethod
    async def read_chunk(self, chunk_size_samples: int) -> bytes:
        """Read a raw PCM chunk from the audio stream.

        Returns ``None`` when the stream is exhausted.
        """
        raise NotImplementedError("AudioSource.read_chunk must be implemented by concrete sources")

    @abstractmethod
    async def close(self) -> None:
        """Gracefully close and release hardware/network resources."""
        raise NotImplementedError("AudioSource.close must be implemented by concrete sources")

    @abstractmethod
    def stream_chunks(self, chunk_size_samples: int) -> AsyncIterator[bytes]:
        """Stream chunks asynchronously."""
        raise NotImplementedError("AudioSource.stream_chunks must be implemented by concrete sources")

    def bytes_per_sample(self) -> int:
        """Bytes occupied by one sample of one channel in this source's encoding."""
        return BYTES_PER_SAMPLE.get(self.encoding, 2)


class _StreamingSourceMixin:
    """Default ``stream_chunks`` for concrete sources: drain until exhaustion."""

    async def stream_chunks(self, chunk_size_samples: int) -> AsyncIterator[bytes]:
        while True:
            chunk = await self.read_chunk(chunk_size_samples)
            if chunk is None:
                return
            yield chunk


class FakeSource(_StreamingSourceMixin, AudioSource):
    """Deterministic in-memory source used to prove the contract without hardware (C-01).

    Yields a caller-supplied byte buffer in fixed-size chunks.
    """

    source_type = "fake"

    def __init__(
        self,
        payload: bytes,
        sample_rate: int = 16000,
        channels: int = 1,
        encoding: str = PCM_S16LE,
        fail_on_open: bool = False,
    ):
        self._payload = payload
        self.native_sample_rate = sample_rate
        self.channels = channels
        self.encoding = encoding
        self._fail_on_open = fail_on_open
        self._offset = 0
        self._opened = False
        self.closed = False

    @classmethod
    def sine(
        cls,
        duration_s: float,
        freq_hz: float = 440.0,
        sample_rate: int = 16000,
        amplitude: float = 0.5,
    ) -> "FakeSource":
        """Build a source yielding a known sine sequence (C-01 test vehicle)."""
        n = int(round(duration_s * sample_rate))
        t = np.arange(n, dtype=np.float64) / sample_rate
        samples = (amplitude * np.sin(2 * np.pi * freq_hz * t)).astype(np.float32)
        payload = (np.clip(samples, -1.0, 1.0) * 32767.0).astype("<i2").tobytes()
        return cls(payload, sample_rate=sample_rate)

    async def open(self) -> None:
        if self._fail_on_open:
            raise SourceUnavailable(SOURCE_UNAVAILABLE, "FakeSource configured to fail")
        self._opened = True

    async def read_chunk(self, chunk_size_samples: int) -> Optional[bytes]:
        if not self._opened:
            raise SourceUnavailable(SOURCE_UNAVAILABLE, "FakeSource.read_chunk before open()")
        if self._offset >= len(self._payload):
            return None
        nbytes = chunk_size_samples * self.channels * self.bytes_per_sample()
        chunk = self._payload[self._offset : self._offset + nbytes]
        self._offset += len(chunk)
        return chunk

    async def close(self) -> None:
        self.closed = True
        self._opened = False


class WavFileSource(_StreamingSourceMixin, AudioSource):
    """Read a WAV fixture and yield chunks paced in wall-clock time (C-02).

    Does not loop, seek, transcode non-WAV formats, or normalise. Pacing makes the
    demo a stream rather than a batch job; ``speed`` scales that pacing and never
    affects the audio itself or the timestamps derived downstream from sample counts.
    """

    source_type = "wav"

    def __init__(self, path, speed: float = 1.0, realtime: bool = True):
        self.path = Path(path)
        self.speed = speed
        self.realtime = realtime
        self._wav: Optional[wave.Wave_read] = None
        self._sample_width = 2
        self._started_at: Optional[float] = None
        self._samples_read = 0

    async def open(self) -> None:
        if not self.path.exists() or not self.path.is_file():
            raise SourceUnavailable(FIXTURE_MISSING, f"WAV fixture not found: {self.path}")
        try:
            wav = wave.open(str(self.path), "rb")
        except (wave.Error, EOFError, OSError) as exc:
            raise SourceUnavailable(
                FIXTURE_MISSING, f"Unreadable WAV fixture {self.path}: {exc}"
            ) from exc

        sample_width = wav.getsampwidth()
        if sample_width != 2:
            wav.close()
            raise SourceUnavailable(
                SOURCE_UNAVAILABLE,
                f"Unsupported WAV sample width {sample_width * 8}-bit; expected 16-bit PCM",
            )

        self._wav = wav
        self._sample_width = sample_width
        self.native_sample_rate = wav.getframerate()
        self.channels = wav.getnchannels()
        self.encoding = PCM_S16LE
        self._started_at = time.monotonic()
        self._samples_read = 0

    async def read_chunk(self, chunk_size_samples: int) -> Optional[bytes]:
        if self._wav is None:
            raise SourceUnavailable(SOURCE_UNAVAILABLE, "WavFileSource.read_chunk before open()")

        data = self._wav.readframes(chunk_size_samples)
        if not data:
            return None

        self._samples_read += len(data) // (self._sample_width * max(self.channels, 1))
        await self._pace()
        return data

    async def _pace(self) -> None:
        """Sleep so chunks arrive at (scaled) real time. speed<=0 means as fast as possible."""
        if not self.realtime or self.speed <= 0 or self._started_at is None:
            return
        target_elapsed = (self._samples_read / self.native_sample_rate) / self.speed
        drift = target_elapsed - (time.monotonic() - self._started_at)
        if drift > 0:
            await asyncio.sleep(drift)

    async def close(self) -> None:
        if self._wav is not None:
            self._wav.close()
            self._wav = None


class MicrophoneSource(_StreamingSourceMixin, AudioSource):
    """Capture from the host microphone (C-03).

    Not on the critical demo path: WAV fixtures are the reliable route. A missing
    device or denied permission raises SourceUnavailable(NO_CAPTURE_DEVICE) and
    must never crash the API process.
    """

    source_type = "mic"

    def __init__(self, device: Optional[int] = None, sample_rate: int = 16000, channels: int = 1):
        self.device = device
        self.native_sample_rate = sample_rate
        self.channels = channels
        self.encoding = PCM_S16LE
        self._stream = None

    async def open(self) -> None:
        try:
            import sounddevice as sd
        except Exception as exc:  # ImportError, or a backend/PortAudio load failure
            raise SourceUnavailable(
                NO_CAPTURE_DEVICE, f"Microphone capture unavailable: {exc}"
            ) from exc

        try:
            stream = sd.RawInputStream(
                samplerate=self.native_sample_rate,
                channels=self.channels,
                dtype="int16",
                device=self.device,
            )
            stream.start()
        except Exception as exc:  # no device, permission denied, device busy
            raise SourceUnavailable(
                NO_CAPTURE_DEVICE, f"Could not open capture device: {exc}"
            ) from exc

        self._stream = stream

    async def read_chunk(self, chunk_size_samples: int) -> Optional[bytes]:
        if self._stream is None:
            raise SourceUnavailable(NO_CAPTURE_DEVICE, "MicrophoneSource.read_chunk before open()")
        loop = asyncio.get_running_loop()
        data, _overflowed = await loop.run_in_executor(
            None, self._stream.read, chunk_size_samples
        )
        return bytes(data)

    async def close(self) -> None:
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            finally:
                self._stream = None


class WebSocketSource(_StreamingSourceMixin, AudioSource):
    """Accept PCM chunks pushed by the browser over WS /v1/sessions/{id}/audio (C-04).

    The transport layer (api.ws_audio) validates the declared header and calls
    ``push()``; this class owns no socket, which keeps it transport-agnostic.
    Mid-stream gaps are reported via ``gap_bytes`` so the assembler can set
    packet_loss -- audio is never interpolated or invented.
    """

    source_type = "ws"

    def __init__(self, sample_rate: int = 16000, channels: int = 1, encoding: str = PCM_S16LE,
                 max_queue: int = 256):
        self.native_sample_rate = sample_rate
        self.channels = channels
        self.encoding = encoding
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue)
        self._closed = False
        self._buffer = bytearray()
        self.dropped_chunks = 0

    @staticmethod
    def validate_header(header: dict) -> "tuple[int, int, str]":
        """Validate a client-declared audio header; never trust it blindly (C-04)."""
        from .errors import AudioFormatRejected

        if not isinstance(header, dict) or header.get("type") != "audio.header":
            raise AudioFormatRejected("First message must be an audio.header frame")

        sample_rate = header.get("sample_rate")
        channels = header.get("channels", 1)
        encoding = header.get("encoding", PCM_S16LE)

        if not isinstance(sample_rate, int) or not (8000 <= sample_rate <= 192000):
            raise AudioFormatRejected(f"Declared sample_rate out of range: {sample_rate!r}")
        if not isinstance(channels, int) or not (1 <= channels <= 2):
            raise AudioFormatRejected(f"Declared channels unsupported: {channels!r}")
        if encoding not in SUPPORTED_ENCODINGS:
            raise AudioFormatRejected(f"Declared encoding unsupported: {encoding!r}")
        return sample_rate, channels, encoding

    async def open(self) -> None:
        self._closed = False

    def push(self, data: bytes) -> bool:
        """Enqueue a chunk from the transport. Returns False if it was dropped."""
        try:
            self._queue.put_nowait(data)
            return True
        except asyncio.QueueFull:
            self.dropped_chunks += 1
            return False

    def signal_end(self) -> None:
        """Mark the stream finished; pending chunks still drain."""
        self._closed = True
        try:
            self._queue.put_nowait(None)
        except asyncio.QueueFull:
            pass

    async def read_chunk(self, chunk_size_samples: int) -> Optional[bytes]:
        nbytes = chunk_size_samples * self.channels * self.bytes_per_sample()
        while len(self._buffer) < nbytes:
            if self._closed and self._queue.empty():
                break
            item = await self._queue.get()
            if item is None:
                break
            self._buffer.extend(item)

        if not self._buffer:
            return None
        take = min(nbytes, len(self._buffer))
        chunk = bytes(self._buffer[:take])
        del self._buffer[:take]
        return chunk

    async def close(self) -> None:
        self.signal_end()
        self._buffer.clear()
