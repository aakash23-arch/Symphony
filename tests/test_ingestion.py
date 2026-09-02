"""Unit tests for L1 audio ingestion (C-01..C-14).

Covers WAV loading, normalisation, chunk generation, timestamps, buffering, VAD,
invalid/empty/unsupported audio, stream termination and WebSocket disconnect.

Several tests are guard tests: they assert that L1 does NOT classify, does NOT
emit detection scores, and does NOT fabricate audio or continuity.
"""

import asyncio
import json

import numpy as np
import pytest

from audio_fixtures import (
    FIXTURE_RATE,
    WAV_FIXTURE_DURATION_S,
    pcm_bytes,
    silence,
    tone,
    voiced,
)

from voiceshield.contracts.frame import FrameObject
from voiceshield.ingestion.buffering import FrameAssembler
from voiceshield.ingestion.channel import ChannelProfiler
from voiceshield.ingestion.errors import (
    AUDIO_PROTOCOL_VIOLATION,
    FIXTURE_MISSING,
    AudioFormatRejected,
    FrameRejected,
    SessionError,
    SourceUnavailable,
)
from voiceshield.ingestion.language import LanguageTagger
from voiceshield.ingestion.pipeline import L1IngestionPipeline
from voiceshield.ingestion.preprocessing import Normaliser
from voiceshield.ingestion.publisher import InMemoryFramePublisher
from voiceshield.ingestion.quality import QualityEstimator
from voiceshield.ingestion.session import SessionManager, SessionState
from voiceshield.ingestion.sources import (
    PCM_S16LE,
    FakeSource,
    MicrophoneSource,
    WavFileSource,
    WebSocketSource,
)
from voiceshield.ingestion.vad import VoiceActivityDetector

FRAME_MS = 250
FRAME_SAMPLES = FIXTURE_RATE * FRAME_MS // 1000


# ============================================================ WAV loading (C-02)


async def test_wav_source_reports_native_descriptors(wav_fixture):
    source = WavFileSource(wav_fixture, realtime=False)
    await source.open()
    try:
        assert source.source_type == "wav"
        assert source.native_sample_rate == FIXTURE_RATE
        assert source.channels == 1
        assert source.encoding == PCM_S16LE
    finally:
        await source.close()


async def test_wav_source_yields_all_samples_in_order(wav_fixture):
    source = WavFileSource(wav_fixture, realtime=False)
    await source.open()
    try:
        chunks = []
        while True:
            chunk = await source.read_chunk(FRAME_SAMPLES)
            if chunk is None:
                break
            chunks.append(chunk)
    finally:
        await source.close()

    total_bytes = sum(len(c) for c in chunks)
    expected_samples = int(WAV_FIXTURE_DURATION_S * FIXTURE_RATE)
    assert total_bytes // 2 == expected_samples

    # Ordering: reassembled bytes equal the file's payload exactly.
    import wave

    with wave.open(str(wav_fixture), "rb") as wav:
        original = wav.readframes(wav.getnframes())
    assert b"".join(chunks) == original


async def test_wav_source_exhaustion_returns_none(wav_fixture):
    source = WavFileSource(wav_fixture, realtime=False)
    await source.open()
    try:
        while await source.read_chunk(FRAME_SAMPLES) is not None:
            pass
        # Still None after exhaustion; it never wraps or loops.
        assert await source.read_chunk(FRAME_SAMPLES) is None
    finally:
        await source.close()


async def test_wav_source_missing_file_raises_fixture_missing(tmp_path):
    source = WavFileSource(tmp_path / "does_not_exist.wav")
    with pytest.raises(SourceUnavailable) as excinfo:
        await source.open()
    assert excinfo.value.code == FIXTURE_MISSING


async def test_wav_source_read_before_open_raises():
    source = WavFileSource("whatever.wav")
    with pytest.raises(SourceUnavailable):
        await source.read_chunk(160)


# ========================================================= Normalisation (C-07)


def test_normalise_produces_canonical_float32_mono():
    raw = pcm_bytes(tone(0.1, 440.0))
    pcm = Normaliser().normalise(raw, source_rate=FIXTURE_RATE, channels=1)

    assert pcm.dtype == np.float32
    assert pcm.ndim == 1
    assert pcm.size == int(0.1 * FIXTURE_RATE)
    assert float(np.max(np.abs(pcm))) <= 1.0


def test_normalise_downmixes_stereo_to_mono():
    left = tone(0.1, 440.0)
    right = tone(0.1, 440.0)
    interleaved = np.empty(left.size * 2, dtype=np.float64)
    interleaved[0::2] = left
    interleaved[1::2] = right

    pcm = Normaliser().normalise(pcm_bytes(interleaved), source_rate=FIXTURE_RATE, channels=2)
    assert pcm.size == left.size


def test_normalise_resamples_to_canonical_rate():
    raw = pcm_bytes(tone(0.5, 440.0, rate=44100))
    pcm = Normaliser().normalise(raw, source_rate=44100, channels=1)

    expected = int(round(0.5 * FIXTURE_RATE))
    assert abs(pcm.size - expected) <= 2


def test_normalise_golden_vector_preserves_tone_frequency():
    """Known input -> asserted output rate, shape and dominant frequency."""
    raw = pcm_bytes(tone(0.5, 1000.0, rate=48000))
    pcm = Normaliser().normalise(raw, source_rate=48000, channels=1)

    spectrum = np.abs(np.fft.rfft(pcm.astype(np.float64)))
    freqs = np.fft.rfftfreq(pcm.size, d=1.0 / FIXTURE_RATE)
    peak_hz = float(freqs[int(np.argmax(spectrum))])
    assert abs(peak_hz - 1000.0) < 20.0


def test_normalise_applies_no_spectral_enhancement():
    """C-07 hard rule: band-limited input must stay band-limited.

    Any denoise/enhancement stage would synthesise energy above the cutoff.
    """
    clean = voiced(0.5, f0=150.0)
    spectrum = np.fft.rfft(clean)
    freqs = np.fft.rfftfreq(clean.size, d=1.0 / FIXTURE_RATE)
    spectrum[freqs > 3000.0] = 0.0
    band_limited = np.fft.irfft(spectrum, n=clean.size)

    pcm = Normaliser().normalise(
        pcm_bytes(band_limited), source_rate=FIXTURE_RATE, channels=1
    )

    out_spectrum = np.abs(np.fft.rfft(pcm.astype(np.float64))) ** 2
    out_freqs = np.fft.rfftfreq(pcm.size, d=1.0 / FIXTURE_RATE)
    above = float(out_spectrum[out_freqs > 3400.0].sum())
    total = float(out_spectrum.sum())
    # Only quantisation noise should live above the cutoff.
    assert above / max(total, 1e-12) < 0.01


def test_normalise_does_not_amplify_silence():
    """Peak normalisation must not turn near-silence into noise."""
    quiet = silence(0.1) + 1e-6
    pcm = Normaliser().normalise(pcm_bytes(quiet), source_rate=FIXTURE_RATE, channels=1)
    assert float(np.max(np.abs(pcm))) < 0.01


def test_normalise_rejects_unsupported_encoding():
    with pytest.raises(FrameRejected):
        Normaliser().normalise(b"\x00\x01", source_rate=FIXTURE_RATE,
                               channels=1, encoding="mp3")


def test_normalise_rejects_unsupported_sample_rate():
    normaliser = Normaliser()
    with pytest.raises(FrameRejected):
        normaliser.normalise(pcm_bytes(tone(0.1)), source_rate=100, channels=1)
    assert normaliser.rejected_count == 1


# ======================================================= Chunk generation (C-06)


def test_frame_assembler_emits_exact_frame_sizes():
    assembler = FrameAssembler(sample_rate=FIXTURE_RATE, frame_ms=FRAME_MS)
    payload = pcm_bytes(tone(1.0))

    frames = assembler.push(payload)

    assert len(frames) == 4  # 1.0 s / 250 ms
    assert all(len(f.data) == FRAME_SAMPLES * 2 for f in frames)
    assert all(f.sample_count == FRAME_SAMPLES for f in frames)


def test_frame_assembler_honours_configurable_frame_size():
    for frame_ms, expected in [(20, 50), (100, 10), (500, 2)]:
        assembler = FrameAssembler(sample_rate=FIXTURE_RATE, frame_ms=frame_ms)
        frames = assembler.push(pcm_bytes(tone(1.0)))
        assert len(frames) == expected, f"frame_ms={frame_ms}"


def test_frame_assembler_accumulates_across_partial_chunks():
    """Chunks smaller than a frame accumulate; no frame is emitted early."""
    assembler = FrameAssembler(sample_rate=FIXTURE_RATE, frame_ms=FRAME_MS)
    payload = pcm_bytes(tone(0.25))
    quarter = len(payload) // 4

    emitted = []
    for i in range(4):
        emitted.extend(assembler.push(payload[i * quarter : (i + 1) * quarter]))

    assert len(emitted) == 1
    assert emitted[0].sample_count == FRAME_SAMPLES


def test_frame_assembler_leaves_residue_unemitted_until_flush():
    assembler = FrameAssembler(sample_rate=FIXTURE_RATE, frame_ms=FRAME_MS)
    frames = assembler.push(pcm_bytes(tone(0.3)))  # 1 full frame + 50 ms residue
    assert len(frames) == 1

    flushed = assembler.flush()
    assert len(flushed) == 1
    assert flushed[0].partial is True
    assert flushed[0].sample_count == int(0.05 * FIXTURE_RATE)


# ============================================================ Timestamps (C-06)


def test_frame_ids_are_strictly_monotonic():
    assembler = FrameAssembler(sample_rate=FIXTURE_RATE, frame_ms=FRAME_MS)
    frames = assembler.push(pcm_bytes(tone(2.0)))

    ids = [f.frame_id for f in frames]
    assert ids == list(range(len(frames)))
    assert all(b > a for a, b in zip(ids, ids[1:]))


def test_timestamps_are_monotonic_and_contiguous():
    assembler = FrameAssembler(sample_rate=FIXTURE_RATE, frame_ms=FRAME_MS)
    frames = assembler.push(pcm_bytes(tone(2.0)))

    assert frames[0].t_start == 0.0
    for previous, current in zip(frames, frames[1:]):
        assert current.t_start > previous.t_start
        assert current.t_start == pytest.approx(previous.t_end, abs=1e-9)
    for frame in frames:
        assert frame.t_end > frame.t_start


def test_timestamps_derive_from_sample_counts_not_wall_clock():
    """Frame duration must equal the nominal frame duration exactly."""
    assembler = FrameAssembler(sample_rate=FIXTURE_RATE, frame_ms=FRAME_MS)
    frames = assembler.push(pcm_bytes(tone(1.0)))
    for frame in frames:
        assert frame.t_end - frame.t_start == pytest.approx(FRAME_MS / 1000.0, abs=1e-9)


def test_timestamps_survive_ragged_chunk_arrival():
    """Irregular chunk sizes must not perturb the timeline."""
    assembler = FrameAssembler(sample_rate=FIXTURE_RATE, frame_ms=FRAME_MS)
    payload = pcm_bytes(tone(1.0))

    frames = []
    offset = 0
    for size in [101, 4096, 7, 20000, 512, 99999]:
        frames.extend(assembler.push(payload[offset : offset + size]))
        offset += size
    frames.extend(assembler.push(payload[offset:]))

    assert [f.frame_id for f in frames] == list(range(len(frames)))
    for previous, current in zip(frames, frames[1:]):
        assert current.t_start == pytest.approx(previous.t_end, abs=1e-9)


# ============================================================= Buffering (C-06)


def test_underrun_frame_is_flagged_with_packet_loss():
    assembler = FrameAssembler(sample_rate=FIXTURE_RATE, frame_ms=FRAME_MS)
    assembler.push(pcm_bytes(tone(0.125)))  # half a frame
    flushed = assembler.flush()

    assert len(flushed) == 1
    assert flushed[0].packet_loss == pytest.approx(0.5, abs=0.01)
    assert assembler.underrun_frames == 1


def test_declared_gap_raises_packet_loss_without_padding():
    assembler = FrameAssembler(sample_rate=FIXTURE_RATE, frame_ms=FRAME_MS)
    # Declare that a quarter-frame of audio never arrived.
    assembler.declare_gap(int(FRAME_SAMPLES * 0.25) * 2)
    frames = assembler.push(pcm_bytes(tone(0.25)))

    assert len(frames) == 1
    assert frames[0].packet_loss == pytest.approx(0.25, abs=0.01)
    # The frame still carries only real audio: no zero padding was inserted.
    assert frames[0].sample_count == FRAME_SAMPLES


def test_partial_frame_is_not_zero_padded():
    assembler = FrameAssembler(sample_rate=FIXTURE_RATE, frame_ms=FRAME_MS)
    assembler.push(pcm_bytes(tone(0.1)))
    flushed = assembler.flush()

    expected_samples = int(0.1 * FIXTURE_RATE)
    assert flushed[0].sample_count == expected_samples
    assert len(flushed[0].data) == expected_samples * 2


def test_jitter_buffer_drops_oldest_on_overflow():
    assembler = FrameAssembler(sample_rate=FIXTURE_RATE, frame_ms=FRAME_MS,
                               max_buffered_frames=3)
    frames = assembler.push(pcm_bytes(tone(1.25)))  # 5 frames
    assert len(frames) == 5

    for frame in frames:
        assembler.buffer_frame(frame)

    buffered = list(assembler.drain_buffered())
    assert assembler.dropped_frames == 2
    # The OLDEST were dropped: the newest 3 survive, still in order.
    assert [f.frame_id for f in buffered] == [2, 3, 4]


def test_publisher_drops_oldest_and_never_blocks():
    publisher = InMemoryFramePublisher(maxlen=3)

    async def _run():
        for i in range(5):
            await publisher.publish(_make_frame(frame_id=i))
        return publisher.drain()

    frames = asyncio.run(_run())
    assert [f.frame_id for f in frames] == [2, 3, 4]
    assert publisher.dropped_frames == 2


def _make_frame(frame_id: int = 0, session_id: str = "s") -> FrameObject:
    from datetime import datetime, timezone

    return FrameObject(
        session_id=session_id,
        frame_id=frame_id,
        pcm=[0.0, 0.1],
        sample_rate=FIXTURE_RATE,
        t_start=float(frame_id) * 0.25,
        t_end=float(frame_id) * 0.25 + 0.25,
        created_at=datetime.now(timezone.utc),
    )


# =================================================================== VAD (C-10)


def test_vad_detects_speechlike_signal():
    detector = VoiceActivityDetector()
    result = detector.detect(voiced(0.5, f0=140.0).astype(np.float32), FIXTURE_RATE)
    assert result.is_speech is True


def test_vad_rejects_digital_silence():
    detector = VoiceActivityDetector()
    result = detector.detect(silence(0.5).astype(np.float32), FIXTURE_RATE)
    assert result.is_speech is False


def test_vad_rejects_low_level_noise():
    rng = np.random.default_rng(7)
    quiet_noise = (0.0005 * rng.standard_normal(FIXTURE_RATE // 2)).astype(np.float32)
    detector = VoiceActivityDetector()
    # Prime the noise floor on the same noise, then judge it.
    detector.detect(quiet_noise, FIXTURE_RATE)
    result = detector.detect(quiet_noise, FIXTURE_RATE)
    assert result.is_speech is False


def test_vad_fails_open_on_detector_error():
    """C-10: a detector failure must fail open to is_speech=True, not crash."""
    detector = VoiceActivityDetector()
    result = detector.detect("not-an-array", FIXTURE_RATE)  # type: ignore[arg-type]

    assert result.is_speech is True
    assert result.failed_open is True
    assert detector.failure_count == 1


def test_vad_empty_input_is_not_speech():
    detector = VoiceActivityDetector()
    result = detector.detect(np.zeros(0, dtype=np.float32), FIXTURE_RATE)
    assert result.is_speech is False


# =============================================================== Invalid audio


async def test_corrupt_wav_raises_source_unavailable(corrupt_wav_fixture):
    source = WavFileSource(corrupt_wav_fixture)
    with pytest.raises(SourceUnavailable):
        await source.open()


async def test_corrupt_wav_emits_no_frames(corrupt_wav_fixture):
    sessions = SessionManager()
    publisher = InMemoryFramePublisher()
    pipeline = L1IngestionPipeline(session_manager=sessions, publisher=publisher)
    record = sessions.create(source_type="wav")

    with pytest.raises(SourceUnavailable):
        await pipeline.run(record.session_id, WavFileSource(corrupt_wav_fixture))

    assert publisher.published_count == 0
    assert sessions.get(record.session_id).state is SessionState.FAILED


async def test_failed_session_carries_reason_and_no_score(corrupt_wav_fixture):
    """C-01: the UI shows the failure; it never shows a score."""
    sessions = SessionManager()
    pipeline = L1IngestionPipeline(session_manager=sessions)
    record = sessions.create(source_type="wav")

    with pytest.raises(SourceUnavailable):
        await pipeline.run(record.session_id, WavFileSource(corrupt_wav_fixture))

    failed = sessions.get(record.session_id)
    assert failed.state is SessionState.FAILED
    assert failed.reason is not None
    assert failed.frames_published == 0


# ================================================================= Empty audio


async def test_empty_wav_emits_zero_frames(empty_wav_fixture):
    sessions = SessionManager()
    publisher = InMemoryFramePublisher()
    pipeline = L1IngestionPipeline(session_manager=sessions, publisher=publisher)
    record = sessions.create(source_type="wav")

    published = await pipeline.run(
        record.session_id, WavFileSource(empty_wav_fixture, realtime=False)
    )

    assert published == 0
    assert publisher.published_count == 0
    # No frame is fabricated to stand in for absent audio.
    assert publisher.drain() == []
    assert sessions.get(record.session_id).state is SessionState.STOPPED


def test_empty_buffer_flush_emits_nothing():
    assembler = FrameAssembler(sample_rate=FIXTURE_RATE, frame_ms=FRAME_MS)
    assert assembler.push(b"") == []
    assert assembler.flush() == []
    assert assembler.next_frame_id == 0


async def test_silent_wav_emits_frames_but_no_speech(silent_wav_fixture):
    sessions = SessionManager()
    publisher = InMemoryFramePublisher()
    pipeline = L1IngestionPipeline(session_manager=sessions, publisher=publisher)
    record = sessions.create(source_type="wav")

    await pipeline.run(record.session_id, WavFileSource(silent_wav_fixture, realtime=False))

    frames = publisher.drain()
    assert len(frames) > 0
    assert all(f.is_speech is False for f in frames)


# =========================================================== Unsupported format


async def test_eight_bit_wav_is_rejected(eight_bit_wav_fixture):
    source = WavFileSource(eight_bit_wav_fixture)
    with pytest.raises(SourceUnavailable):
        await source.open()


def test_websocket_header_rejects_unsupported_encoding():
    with pytest.raises(AudioFormatRejected):
        WebSocketSource.validate_header(
            {"type": "audio.header", "sample_rate": 16000, "channels": 1, "encoding": "mp3"}
        )


def test_websocket_header_rejects_out_of_range_sample_rate():
    with pytest.raises(AudioFormatRejected):
        WebSocketSource.validate_header(
            {"type": "audio.header", "sample_rate": 3, "channels": 1, "encoding": PCM_S16LE}
        )


def test_websocket_header_rejects_wrong_message_type():
    with pytest.raises(AudioFormatRejected):
        WebSocketSource.validate_header({"type": "audio.data", "sample_rate": 16000})


def test_websocket_header_accepts_valid_declaration():
    rate, channels, encoding = WebSocketSource.validate_header(
        {"type": "audio.header", "sample_rate": 48000, "channels": 2, "encoding": PCM_S16LE}
    )
    assert (rate, channels, encoding) == (48000, 2, PCM_S16LE)


async def test_unsupported_frame_is_dropped_and_session_continues():
    """C-07: FRAME_REJECTED drops one frame; the session keeps running."""
    sessions = SessionManager()
    pipeline = L1IngestionPipeline(session_manager=sessions)
    record = sessions.create(source_type="wav")
    sessions.start(record.session_id)

    from voiceshield.ingestion.buffering import RawFrame

    bad = RawFrame(
        frame_id=0,
        data=b"\x00" * 64,
        sample_rate=100,  # unsupported rate -> rejected by the Normaliser
        channels=1,
        encoding=PCM_S16LE,
        t_start=0.0,
        t_end=0.25,
        sample_count=32,
    )
    assert pipeline.build_frame(record.session_id, 0, bad, "wav") is None
    assert pipeline.rejected_frames == 1
    assert sessions.get(record.session_id).state is SessionState.RUNNING


# =========================================================== Stream termination


async def test_stream_terminates_on_source_exhaustion(wav_fixture):
    sessions = SessionManager()
    publisher = InMemoryFramePublisher()
    pipeline = L1IngestionPipeline(session_manager=sessions, publisher=publisher)
    record = sessions.create(source_type="wav")

    published = await pipeline.run(
        record.session_id, WavFileSource(wav_fixture, realtime=False)
    )

    assert published > 0
    assert sessions.get(record.session_id).state is SessionState.STOPPED
    # Nothing more arrives after termination.
    before = publisher.published_count
    assert before == published
    assert publisher.pending == published


async def test_stop_event_terminates_stream_early(wav_fixture):
    sessions = SessionManager()
    publisher = InMemoryFramePublisher()
    pipeline = L1IngestionPipeline(session_manager=sessions, publisher=publisher)
    record = sessions.create(source_type="wav")

    stop_event = asyncio.Event()
    stop_event.set()  # stop before the first read

    published = await pipeline.run(
        record.session_id,
        WavFileSource(wav_fixture, realtime=False),
        stop_event=stop_event,
    )

    assert published == 0
    assert sessions.get(record.session_id).state is SessionState.STOPPED


async def test_source_is_closed_after_termination(wav_fixture):
    sessions = SessionManager()
    pipeline = L1IngestionPipeline(session_manager=sessions)
    record = sessions.create(source_type="fake")
    source = FakeSource(pcm_bytes(tone(0.5)))

    await pipeline.run(record.session_id, source)

    assert source.closed is True


def test_session_lifecycle_rejects_illegal_transitions():
    sessions = SessionManager()
    record = sessions.create(source_type="wav")
    sessions.start(record.session_id)
    sessions.stop(record.session_id)

    # A terminal session cannot be restarted.
    with pytest.raises(SessionError):
        sessions.transition(record.session_id, SessionState.RUNNING)


def test_duplicate_start_is_rejected():
    sessions = SessionManager()
    record = sessions.create(source_type="wav")
    sessions.start(record.session_id)

    with pytest.raises(SessionError) as excinfo:
        sessions.start(record.session_id)
    assert excinfo.value.status_code == 409


def test_unknown_session_lookup_is_404():
    sessions = SessionManager()
    with pytest.raises(SessionError) as excinfo:
        sessions.get("no-such-session")
    assert excinfo.value.status_code == 404


def test_interrupted_sessions_are_not_resumed():
    """§17.3: non-terminal sessions become INTERRUPTED and no score is rebuilt."""
    sessions = SessionManager()
    record = sessions.create(source_type="wav")
    sessions.start(record.session_id)

    interrupted = sessions.mark_interrupted()

    assert len(interrupted) == 1
    assert sessions.get(record.session_id).state is SessionState.INTERRUPTED
    assert sessions.get(record.session_id).is_terminal is True


# ========================================================== WebSocket lifecycle
# (The /ws/audio live streaming ingestion route was removed during architecture hardening)



def test_events_websocket_emits_session_envelope(client):
    from voiceshield.api.runtime import reset_runtime

    runtime = reset_runtime()
    session_id = runtime.sessions.create(source_type="wav").session_id

    with client.websocket_connect(f"/v1/sessions/{session_id}/events") as ws:
        envelope = ws.receive_json()

    assert envelope["session_id"] == session_id
    assert envelope["event_type"] == "session.started"
    assert envelope["seq"] >= 1


def test_events_websocket_unknown_session_is_closed(client):
    from voiceshield.api.runtime import reset_runtime

    reset_runtime()
    with client.websocket_connect("/v1/sessions/nope/events") as ws:
        message = ws.receive_json()
    assert message["code"] == "SESSION_NOT_FOUND"


# ============================================== Quality / channel / language

def test_quality_is_lowered_by_added_noise():
    """C-09 monotonicity: added noise must lower q_t."""
    rng = np.random.default_rng(11)
    clean = voiced(0.5, f0=140.0)
    noisy = clean + 0.3 * rng.standard_normal(clean.size)

    estimator = QualityEstimator()
    q_clean = estimator.estimate(clean.astype(np.float32), FIXTURE_RATE, bandwidth=3400.0).q_t
    q_noisy = estimator.estimate(noisy.astype(np.float32), FIXTURE_RATE, bandwidth=3400.0).q_t

    assert q_clean is not None and q_noisy is not None
    assert q_noisy < q_clean


def test_quality_is_lowered_by_clipping():
    clean = voiced(0.5, f0=140.0)
    clipped = np.clip(clean * 8.0, -1.0, 1.0)

    estimator = QualityEstimator()
    q_clean = estimator.estimate(clean.astype(np.float32), FIXTURE_RATE, bandwidth=3400.0).q_t
    q_clipped = estimator.estimate(clipped.astype(np.float32), FIXTURE_RATE,
                                   bandwidth=3400.0).q_t

    assert q_clean is not None and q_clipped is not None
    assert q_clipped < q_clean


def test_quality_is_bounded_and_unknown_on_failure():
    estimator = QualityEstimator()
    report = estimator.estimate(voiced(0.3).astype(np.float32), FIXTURE_RATE, bandwidth=3400.0)
    assert 0.0 <= report.q_t <= 1.0

    # An estimator failure yields None, never a flattering default.
    broken = estimator.estimate("not-an-array", FIXTURE_RATE)  # type: ignore[arg-type]
    assert broken.q_t is None
    assert estimator.error_count == 1


def test_quality_of_empty_frame_is_unknown():
    report = QualityEstimator().estimate(np.zeros(0, dtype=np.float32), FIXTURE_RATE)
    assert report.q_t is None


def test_clean_tonal_audio_is_not_scored_as_clipped():
    """A clean sine sits near its peak every cycle; that is not clipping."""
    estimator = QualityEstimator()
    clean = estimator.estimate(tone(0.25, 440.0).astype(np.float32), FIXTURE_RATE,
                               bandwidth=3400.0)
    assert clean.clipping_ratio == 0.0
    assert clean.clipping_score == 1.0


def test_clipped_audio_is_detected_after_peak_normalisation():
    """C-07 peak-normalises every frame, so clipping must be judged relatively."""
    clipped_source = np.clip(voiced(0.25, f0=130.0) * 8.0, -1.0, 1.0)
    normalised = Normaliser().normalise(
        pcm_bytes(clipped_source), source_rate=FIXTURE_RATE, channels=1
    )

    report = QualityEstimator().estimate(normalised, FIXTURE_RATE, bandwidth=3400.0)
    assert report.clipping_ratio > 0.1
    assert report.clipping_score < 0.5


def test_snr_distinguishes_clean_from_noisy_stationary_signal():
    """A steady clean tone must not be mistaken for a noisy one."""
    rng = np.random.default_rng(5)
    estimator = QualityEstimator()

    clean = tone(0.25, 440.0).astype(np.float32)
    noisy = (tone(0.25, 440.0) + 0.3 * rng.standard_normal(clean.size)).astype(np.float32)

    snr_clean = estimator.estimate_snr_db(clean, FIXTURE_RATE)
    snr_noisy = estimator.estimate_snr_db(noisy, FIXTURE_RATE)

    assert snr_clean is not None and snr_noisy is not None
    assert snr_clean > snr_noisy + 10.0


def test_quality_never_collapses_to_exactly_zero():
    """q_t = 0 would assert a certainty the estimator does not have."""
    estimator = QualityEstimator()
    report = estimator.estimate(silence(0.25).astype(np.float32), FIXTURE_RATE,
                                bandwidth=None)
    assert report.q_t is not None
    assert 0.0 < report.q_t < 0.5


def test_channel_profiler_reports_unknown_codec_for_file_sources():
    """C-08: UNKNOWN is the expected value for file input, not an error."""
    profile = ChannelProfiler().profile(
        voiced(0.3).astype(np.float32), FIXTURE_RATE, source_type="wav"
    )
    assert profile.codec_vec is None
    assert profile.bandwidth is not None


def test_channel_profiler_estimates_bandwidth_of_band_limited_signal():
    clean = voiced(0.5, f0=150.0)
    spectrum = np.fft.rfft(clean)
    freqs = np.fft.rfftfreq(clean.size, d=1.0 / FIXTURE_RATE)
    spectrum[freqs > 2000.0] = 0.0
    band_limited = np.fft.irfft(spectrum, n=clean.size).astype(np.float32)

    bandwidth = ChannelProfiler().estimate_bandwidth(band_limited, FIXTURE_RATE)
    assert bandwidth is not None
    assert bandwidth <= 2200.0


def test_language_tagger_reports_unknown():
    """C-12: UNKNOWN is the honest state; no language is guessed."""
    result = LanguageTagger().tag(voiced(0.3).astype(np.float32), FIXTURE_RATE)
    assert result.lang_t == "UNKNOWN"
    assert result.switch_flag is False


# ============================================ FrameObject contract guards (C-13)


async def test_assembled_frame_matches_frozen_contract(wav_fixture):
    """§6.1: exactly the frozen field set -- no score field may appear."""
    sessions = SessionManager()
    publisher = InMemoryFramePublisher()
    pipeline = L1IngestionPipeline(session_manager=sessions, publisher=publisher)
    record = sessions.create(source_type="wav")

    await pipeline.run(record.session_id, WavFileSource(wav_fixture, realtime=False))
    frame = publisher.drain()[0]

    assert set(frame.model_dump().keys()) == {
        "session_id", "frame_id", "pcm", "sample_rate", "t_start", "t_end",
        "codec_vec", "bandwidth", "packet_loss", "q_t", "is_speech",
        "speaker_turn", "overlap_flag", "lang_t", "switch_flag",
        "source_type", "created_at",
    }


async def test_frames_carry_no_detection_score(wav_fixture):
    """L1 must not produce any ML/detection/risk field."""
    sessions = SessionManager()
    publisher = InMemoryFramePublisher()
    pipeline = L1IngestionPipeline(session_manager=sessions, publisher=publisher)
    record = sessions.create(source_type="wav")

    await pipeline.run(record.session_id, WavFileSource(wav_fixture, realtime=False))

    forbidden = {"p_spoof", "risk", "score", "confidence", "band", "prediction",
                 "is_deepfake", "label"}
    for frame in publisher.drain():
        assert forbidden.isdisjoint({k.lower() for k in frame.model_dump()})


async def test_source_type_is_opaque_and_preserved(wav_fixture):
    sessions = SessionManager()
    publisher = InMemoryFramePublisher()
    pipeline = L1IngestionPipeline(session_manager=sessions, publisher=publisher)
    record = sessions.create(source_type="wav")

    await pipeline.run(record.session_id, WavFileSource(wav_fixture, realtime=False))
    assert all(f.source_type == "wav" for f in publisher.drain())


async def test_fake_source_conforms_to_protocol():
    """C-01: protocol conformance without audio hardware."""
    source = FakeSource.sine(0.5, freq_hz=440.0)
    await source.open()
    try:
        assert source.native_sample_rate == FIXTURE_RATE
        assert source.channels == 1
        chunks = [c async for c in source.stream_chunks(FRAME_SAMPLES)]
    finally:
        await source.close()

    assert sum(len(c) for c in chunks) // 2 == int(0.5 * FIXTURE_RATE)
    assert source.closed is True


async def test_fake_source_open_failure_is_typed():
    source = FakeSource(b"", fail_on_open=True)
    with pytest.raises(SourceUnavailable):
        await source.open()


# ==================================================== Microphone error path (C-03)


async def test_microphone_missing_device_raises_typed_error(monkeypatch):
    """C-03: no device must raise NO_CAPTURE_DEVICE, never crash the process."""
    import sys
    import types

    stub = types.ModuleType("sounddevice")

    def _raise(*args, **kwargs):
        raise OSError("no default input device")

    stub.RawInputStream = _raise  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "sounddevice", stub)

    source = MicrophoneSource()
    with pytest.raises(SourceUnavailable) as excinfo:
        await source.open()
    assert excinfo.value.code == "NO_CAPTURE_DEVICE"


async def test_microphone_missing_library_raises_typed_error(monkeypatch):
    import builtins

    real_import = builtins.__import__

    def _fake_import(name, *args, **kwargs):
        if name == "sounddevice":
            raise ImportError("sounddevice is not installed")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _fake_import)

    source = MicrophoneSource()
    with pytest.raises(SourceUnavailable) as excinfo:
        await source.open()
    assert excinfo.value.code == "NO_CAPTURE_DEVICE"
