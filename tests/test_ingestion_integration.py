"""Deterministic end-to-end integration test for L1 audio ingestion.

Streams a small synthetic fixture WAV through the replay simulator and the full
L1 pipeline into the frame publisher, then asserts the emitted FrameObject
sequence field by field.

The replay runs at speed=0 (as fast as possible), which makes the run instant
and its output identical on every machine. Playback speed affects PACING ONLY:
timestamps derive from cumulative sample counts, so they are unchanged by it --
that invariant is asserted here directly.
"""

import numpy as np
import pytest

from audio_fixtures import (
    FIXTURE_RATE,
    WAV_FIXTURE_DURATION_S,
    WAV_FIXTURE_SEGMENTS,
    standard_fixture_samples,
    write_wav,
)

from voiceshield.contracts.frame import FrameObject
from voiceshield.demo.replay import ReplaySimulator, ReplayState
from voiceshield.ingestion.publisher import InMemoryFramePublisher
from voiceshield.ingestion.session import SessionManager, SessionState

FRAME_MS = 250
FRAME_SAMPLES = FIXTURE_RATE * FRAME_MS // 1000
EXPECTED_FRAMES = int(WAV_FIXTURE_DURATION_S * 1000 / FRAME_MS)  # 8


@pytest.fixture
def fixture_wav(tmp_path):
    """The standard 2.0 s silence/voiced/silence/voiced fixture."""
    return write_wav(tmp_path / "integration.wav", standard_fixture_samples())


def _make_simulator(path, speed=0.0):
    sessions = SessionManager()
    publisher = InMemoryFramePublisher()
    simulator = ReplaySimulator(
        path,
        session_manager=sessions,
        publisher=publisher,
        speed=speed,
        frame_ms=FRAME_MS,
    )
    return simulator, publisher


async def test_replay_streams_fixture_end_to_end(fixture_wav):
    """One deterministic pass of a fixture file through the whole L1 layer."""
    simulator, publisher = _make_simulator(fixture_wav)

    frames = await simulator.collect()

    # -- frame count ----------------------------------------------------------
    assert len(frames) == EXPECTED_FRAMES
    assert publisher.published_count == EXPECTED_FRAMES

    # -- contract -------------------------------------------------------------
    assert all(isinstance(f, FrameObject) for f in frames)

    # -- identifiers ----------------------------------------------------------
    assert [f.frame_id for f in frames] == list(range(EXPECTED_FRAMES))
    assert len({f.session_id for f in frames}) == 1
    assert frames[0].session_id == simulator.session_id

    # -- timestamps -----------------------------------------------------------
    assert frames[0].t_start == 0.0
    for previous, current in zip(frames, frames[1:]):
        assert current.t_start > previous.t_start
        assert current.t_start == pytest.approx(previous.t_end, abs=1e-9)
    assert frames[-1].t_end == pytest.approx(WAV_FIXTURE_DURATION_S, abs=1e-6)

    # -- canonical PCM --------------------------------------------------------
    for frame in frames:
        assert frame.sample_rate == FIXTURE_RATE
        assert len(frame.pcm) == FRAME_SAMPLES
        assert max(abs(x) for x in frame.pcm) <= 1.0

    # -- VAD tracks the known segment layout ----------------------------------
    for frame in frames:
        midpoint = (frame.t_start + frame.t_end) / 2.0
        expected = next(
            speech for start, end, speech in WAV_FIXTURE_SEGMENTS
            if start <= midpoint < end
        )
        assert frame.is_speech is expected, (
            f"frame {frame.frame_id} at t={midpoint:.3f}s: "
            f"expected is_speech={expected}, got {frame.is_speech}"
        )

    # -- honest defaults ------------------------------------------------------
    for frame in frames:
        assert frame.source_type == "wav"
        assert frame.lang_t == "UNKNOWN"       # C-12: no language is guessed
        assert frame.switch_flag is False
        assert frame.codec_vec is None         # C-08: UNKNOWN for file sources
        assert frame.q_t is None or 0.0 <= frame.q_t <= 1.0

    # -- terminal state -------------------------------------------------------
    assert simulator.state is ReplayState.STOPPED
    assert simulator.session_state is SessionState.STOPPED
    assert simulator.error is None


async def test_replay_is_deterministic_across_runs(fixture_wav):
    """Two in-process replays of the same fixture produce identical frames."""

    async def _run():
        simulator, _ = _make_simulator(fixture_wav)
        return await simulator.collect()

    first = await _run()
    second = await _run()

    assert len(first) == len(second)
    for a, b in zip(first, second):
        assert a.frame_id == b.frame_id
        assert a.t_start == b.t_start and a.t_end == b.t_end
        assert a.pcm == b.pcm                      # byte-identical audio
        assert a.is_speech == b.is_speech
        assert a.q_t == b.q_t
        assert a.bandwidth == b.bandwidth


async def test_playback_speed_does_not_alter_timestamps(fixture_wav):
    """Requirement: speed changes pacing only, never the emitted timeline."""
    fast, _ = _make_simulator(fixture_wav, speed=0.0)
    paced, _ = _make_simulator(fixture_wav, speed=50.0)

    fast_frames = await fast.collect()
    paced_frames = await paced.collect()

    assert len(fast_frames) == len(paced_frames)
    assert [f.t_start for f in fast_frames] == [f.t_start for f in paced_frames]
    assert [f.t_end for f in fast_frames] == [f.t_end for f in paced_frames]
    assert [f.frame_id for f in fast_frames] == [f.frame_id for f in paced_frames]


async def test_replay_exposes_start_and_stop_states(fixture_wav):
    """Requirement: the simulator exposes start / stop / error states."""
    simulator, _ = _make_simulator(fixture_wav)

    assert simulator.state is ReplayState.IDLE
    assert simulator.is_running is False

    await simulator.collect()

    assert simulator.state is ReplayState.STOPPED
    assert simulator.is_running is False


async def test_replay_stop_is_idempotent(fixture_wav):
    simulator, _ = _make_simulator(fixture_wav)
    await simulator.collect()

    await simulator.stop()
    await simulator.stop()

    assert simulator.state is ReplayState.STOPPED
    assert simulator.session_state is SessionState.STOPPED


async def test_replay_reports_error_state_for_missing_file(tmp_path):
    """Requirement: error state is observable, and no frames are invented."""
    from voiceshield.ingestion.errors import SourceUnavailable

    simulator, publisher = _make_simulator(tmp_path / "missing.wav")

    with pytest.raises(SourceUnavailable):
        await simulator.collect()

    assert simulator.state is ReplayState.ERROR
    assert simulator.error == "FIXTURE_MISSING"
    assert publisher.published_count == 0
    assert simulator.session_state is SessionState.FAILED


async def test_replay_publishes_no_score_fields(fixture_wav):
    """L1 emits FrameObjects only: no detection score, no risk verdict."""
    simulator, _ = _make_simulator(fixture_wav)
    frames = await simulator.collect()

    forbidden = {"p_spoof", "risk", "score", "confidence", "band",
                 "prediction", "verdict", "is_deepfake", "label"}
    for frame in frames:
        assert forbidden.isdisjoint({k.lower() for k in frame.model_dump()})


async def test_replay_total_audio_is_preserved(fixture_wav):
    """Every sample of the fixture reaches exactly one frame; none are invented."""
    simulator, _ = _make_simulator(fixture_wav)
    frames = await simulator.collect()

    total_samples = sum(len(f.pcm) for f in frames)
    assert total_samples == int(WAV_FIXTURE_DURATION_S * FIXTURE_RATE)


async def test_replay_quality_is_measured_per_frame(fixture_wav):
    """q_t is computed from the signal, and differs between silence and speech."""
    simulator, _ = _make_simulator(fixture_wav)
    frames = await simulator.collect()

    speech_q = [f.q_t for f in frames if f.is_speech and f.q_t is not None]
    silent_q = [f.q_t for f in frames if not f.is_speech and f.q_t is not None]

    assert speech_q, "expected at least one speech frame with a quality score"
    # Quality is an audio measure, not a verdict: it simply has to vary with the
    # signal rather than being a constant stamped onto every frame.
    assert len(set(round(q, 6) for q in speech_q + silent_q)) > 1
    assert all(0.0 <= q <= 1.0 for q in speech_q + silent_q)
