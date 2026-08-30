"""Ingestion pipeline interface and L1 implementation (C-04..C-14).

Wires the L1 chain: source chunks -> FrameAssembler -> Normaliser ->
{ChannelProfiler, QualityEstimator, VAD, TurnSegmenter, LanguageTagger} ->
FrameObjectAssembler -> FramePublisher.

This layer performs NO ML classification, produces NO detection score, and
hardcodes NO risk result. It measures signal properties and emits FrameObjects;
that is its entire output surface.
"""

import asyncio
from abc import ABC, abstractmethod
from typing import AsyncIterator, Callable, Optional

from voiceshield.config import settings
from voiceshield.contracts import FrameObject
from voiceshield.obs.logging import get_logger

from .buffering import FrameAssembler, RawFrame
from .channel import ChannelProfiler
from .errors import FrameRejected, SourceUnavailable
from .frame import FrameObjectAssembler
from .language import LanguageTagger
from .preprocessing import Normaliser
from .publisher import FramePublisher, InMemoryFramePublisher
from .quality import QualityEstimator
from .session import SessionManager, SessionState
from .sources import AudioSource
from .vad import VoiceActivityDetector
from .turns import TurnSegmenter

logger = get_logger("voiceshield.ingestion.pipeline")


class IngestionPipeline(ABC):
    """Abstract interface for L1 audio ingestion pipeline."""

    @abstractmethod
    async def process_raw_audio(
        self,
        session_id: str,
        audio_bytes: bytes,
        source_type: str,
    ) -> FrameObject:
        """Process incoming raw audio, apply VAD, quality, and assemble FrameObject."""
        raise NotImplementedError("IngestionPipeline.process_raw_audio is not implemented yet")

    @abstractmethod
    async def publish_frame(self, frame: FrameObject) -> None:
        """Publish FrameObject to Redis stream vs:frames."""
        raise NotImplementedError("IngestionPipeline.publish_frame is not implemented yet")


class L1IngestionPipeline(IngestionPipeline):
    """Concrete L1 pipeline binding one AudioSource to one session."""

    def __init__(
        self,
        session_manager: Optional[SessionManager] = None,
        publisher: Optional[FramePublisher] = None,
        frame_ms: Optional[int] = None,
        target_sample_rate: Optional[int] = None,
        normalise_amplitude: bool = True,
    ):
        self.sessions = session_manager or SessionManager()
        self.publisher = publisher or InMemoryFramePublisher()
        self.frame_ms = frame_ms if frame_ms is not None else settings.audio_hop_ms
        self.target_sample_rate = target_sample_rate or settings.audio_sample_rate

        self.normaliser = Normaliser(
            target_sample_rate=self.target_sample_rate,
            normalise_amplitude=normalise_amplitude,
        )
        self.channel_profiler = ChannelProfiler()
        self.quality_estimator = QualityEstimator()
        self.vad = VoiceActivityDetector()
        self.turn_segmenter = TurnSegmenter()
        self.language_tagger = LanguageTagger()
        self.frame_assembler_out = FrameObjectAssembler()

        self.rejected_frames = 0

    # -- per-frame path -------------------------------------------------------

    def build_frame(
        self,
        session_id: str,
        frame_id: int,
        raw: RawFrame,
        source_type: str,
        native_sample_rate: Optional[int] = None,
    ) -> Optional[FrameObject]:
        """Run one raw frame through C-07..C-13. Returns None if it was dropped."""
        try:
            pcm = self.normaliser.normalise(
                raw.data,
                source_rate=raw.sample_rate,
                channels=raw.channels,
                encoding=raw.encoding,
            )
        except FrameRejected as exc:
            self.rejected_frames += 1
            logger.warning(
                "Frame rejected during normalisation; session continues",
                extra={
                    "extra_fields": {
                        "code": exc.code,
                        "session_id": session_id,
                        "frame_id": frame_id,
                        "error": exc.message,
                    }
                },
            )
            return None

        packet_loss = raw.packet_loss if raw.packet_loss > 0 else (
            0.0 if source_type == "wav" else None
        )

        channel = self.channel_profiler.profile(
            pcm,
            sample_rate=self.target_sample_rate,
            source_type=source_type,
            native_sample_rate=native_sample_rate or raw.sample_rate,
            packet_loss=packet_loss,
        )
        quality = self.quality_estimator.estimate(
            pcm, sample_rate=self.target_sample_rate, bandwidth=channel.bandwidth
        )
        vad = self.vad.detect(pcm, sample_rate=self.target_sample_rate)
        turns = self.turn_segmenter.segment(
            pcm,
            sample_rate=self.target_sample_rate,
            is_speech=vad.is_speech,
            frame_duration_s=max(raw.t_end - raw.t_start, 0.0),
        )
        language = self.language_tagger.tag(pcm, sample_rate=self.target_sample_rate)

        return self.frame_assembler_out.assemble(
            session_id=session_id,
            frame_id=frame_id,
            pcm=pcm,
            sample_rate=self.target_sample_rate,
            t_start=raw.t_start,
            t_end=raw.t_end,
            channel=channel,
            quality=quality,
            vad=vad,
            turns=turns,
            language=language,
            source_type=source_type,
        )

    async def process_raw_audio(
        self,
        session_id: str,
        audio_bytes: bytes,
        source_type: str,
    ) -> Optional[FrameObject]:
        """Single-shot path: treat the buffer as one frame and assemble it."""
        sample_rate = self.target_sample_rate
        assembler = FrameAssembler(
            sample_rate=sample_rate,
            channels=1,
            frame_ms=self.frame_ms,
        )
        frames = assembler.push(audio_bytes) or assembler.flush()
        if not frames:
            return None
        raw = frames[0]
        return self.build_frame(session_id, raw.frame_id, raw, source_type)

    async def publish_frame(self, frame: FrameObject) -> None:
        await self.publisher.publish(frame)

    # -- streaming path -------------------------------------------------------

    async def run(
        self,
        session_id: str,
        source: AudioSource,
        chunk_ms: Optional[int] = None,
        on_frame: Optional[Callable[[FrameObject], None]] = None,
        stop_event: Optional[asyncio.Event] = None,
    ) -> int:
        """Drive a source to exhaustion, publishing every assembled frame.

        Returns the number of frames published. On source failure the session is
        marked FAILED and no final score is synthesised.
        """
        record = self.sessions.get(session_id)

        try:
            await source.open()
        except SourceUnavailable as exc:
            self.sessions.fail(session_id, exc.code)
            logger.error(
                "Audio source unavailable; session FAILED",
                extra={"extra_fields": {"code": exc.code, "session_id": session_id}},
            )
            raise

        if record.source is None:
            self.sessions.bind_source(session_id, source)
        if record.state is SessionState.CREATED:
            self.sessions.start(session_id)

        assembler = FrameAssembler(
            sample_rate=source.native_sample_rate,
            channels=source.channels,
            encoding=source.encoding,
            frame_ms=chunk_ms if chunk_ms is not None else self.frame_ms,
            bytes_per_sample=source.bytes_per_sample(),
        )
        # Read in sub-frame chunks so pacing stays smooth.
        read_samples = max(assembler.frame_samples // 4, 1)

        published = 0
        try:
            while True:
                if stop_event is not None and stop_event.is_set():
                    break
                chunk = await source.read_chunk(read_samples)
                if chunk is None:
                    break
                for raw in assembler.push(chunk):
                    published += await self._emit(session_id, raw, source, on_frame)

            for raw in assembler.flush():
                published += await self._emit(session_id, raw, source, on_frame)

        except SourceUnavailable as exc:
            self.sessions.fail(session_id, exc.code)
            raise
        except Exception as exc:
            self.sessions.fail(session_id, "SOURCE_UNAVAILABLE")
            logger.error(
                "Ingestion loop failed; session FAILED",
                extra={"extra_fields": {"session_id": session_id, "error": str(exc)}},
            )
            raise
        finally:
            await source.close()

        if not self.sessions.get(session_id).is_terminal:
            self.sessions.stop(session_id)
        return published

    async def _emit(
        self,
        session_id: str,
        raw: RawFrame,
        source: AudioSource,
        on_frame: Optional[Callable[[FrameObject], None]],
    ) -> int:
        record = self.sessions.get(session_id)
        frame = self.build_frame(
            session_id,
            record.next_frame_id(),
            raw,
            source_type=source.source_type,
            native_sample_rate=source.native_sample_rate,
        )
        if frame is None:
            record.frames_dropped += 1
            return 0
        await self.publish_frame(frame)
        record.frames_published += 1
        if on_frame is not None:
            on_frame(frame)
        return 1

    async def stream(
        self,
        session_id: str,
        source: AudioSource,
        chunk_ms: Optional[int] = None,
    ) -> AsyncIterator[FrameObject]:
        """Async-iterate assembled frames instead of only publishing them."""
        queue: asyncio.Queue = asyncio.Queue()
        sentinel = object()

        async def _drive() -> None:
            try:
                await self.run(
                    session_id,
                    source,
                    chunk_ms=chunk_ms,
                    on_frame=queue.put_nowait,
                )
            finally:
                queue.put_nowait(sentinel)

        task = asyncio.create_task(_drive())
        try:
            while True:
                item = await queue.get()
                if item is sentinel:
                    break
                yield item
            await task
        finally:
            if not task.done():
                task.cancel()
