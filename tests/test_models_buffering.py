"""Rolling PCM buffer: the fix for 250 ms frames vs a 305 ms model floor."""

import numpy as np
import pytest

from voiceshield.models.buffering import RollingPCMBuffer

RATE = 16000


def chunk(n=4000, value=0.1):
    """One frame's worth of audio: 250 ms at 16 kHz."""
    return np.full(n, value, dtype=np.float32)


def make_buffer(**kwargs):
    defaults = dict(buffer_ms=2000, sample_rate=RATE, max_sessions=4, stride_ms=1000, min_samples=4880)
    defaults.update(kwargs)
    return RollingPCMBuffer(**defaults)


def test_single_frame_is_below_the_model_floor():
    """The problem this class exists to solve: one frame is not enough audio."""
    buffer = make_buffer()
    buffer.append("s", chunk())
    assert buffer.is_ready("s") is False


def test_buffer_becomes_ready_after_enough_frames():
    """Two 250 ms frames still fall short; a third crosses the 4880-sample floor."""
    buffer = make_buffer()
    buffer.append("s", chunk())
    assert buffer.is_ready("s") is False
    buffer.append("s", chunk())
    # 8000 samples > 4880
    assert buffer.is_ready("s") is True


def test_buffer_is_capped_at_capacity():
    """Old audio is evicted so memory stays bounded during a long call."""
    buffer = make_buffer(buffer_ms=1000)
    for _ in range(20):
        buffer.append("s", chunk())
    assert buffer.get("s").size == RATE  # 1000 ms


def test_unknown_session_returns_none():
    assert make_buffer().get("nope") is None
    assert make_buffer().is_ready("nope") is False
    assert make_buffer().should_emit("nope") is False


def test_stride_gates_emission():
    """Emission happens on a stride, not on every frame."""
    buffer = make_buffer()
    for _ in range(3):
        buffer.append("s", chunk())

    assert buffer.should_emit("s") is True
    buffer.mark_emitted("s")
    assert buffer.should_emit("s") is False

    # One more 250 ms frame is not yet the 1000 ms stride.
    buffer.append("s", chunk())
    assert buffer.should_emit("s") is False

    # Three more frames reach the stride.
    for _ in range(3):
        buffer.append("s", chunk())
    assert buffer.should_emit("s") is True


def test_release_frees_a_session():
    """Sessions must be released or the buffer leaks across a long-lived worker."""
    buffer = make_buffer()
    buffer.append("s", chunk())
    assert buffer.session_count == 1
    buffer.release("s")
    assert buffer.session_count == 0
    assert buffer.get("s") is None


def test_lru_cap_evicts_oldest_session():
    """An unbounded session map would leak; the cap evicts oldest-first."""
    buffer = make_buffer(max_sessions=3)
    for name in ("a", "b", "c", "d"):
        buffer.append(name, chunk())

    assert buffer.session_count == 3
    assert buffer.get("a") is None  # oldest evicted
    assert buffer.get("d") is not None


def test_sessions_are_isolated():
    """One session's audio never bleeds into another's window."""
    buffer = make_buffer()
    buffer.append("a", chunk(value=0.1))
    buffer.append("b", chunk(value=0.9))
    assert np.allclose(buffer.get("a"), 0.1)
    assert np.allclose(buffer.get("b"), 0.9)


def test_empty_append_is_a_noop():
    buffer = make_buffer()
    buffer.append("s", np.zeros(0, dtype=np.float32))
    assert buffer.get("s") is None


def test_buffer_preserves_sample_order():
    """The window must be chronological; a scrambled window is not the audio."""
    buffer = make_buffer()
    buffer.append("s", np.array([1.0, 2.0, 3.0], dtype=np.float32))
    buffer.append("s", np.array([4.0, 5.0], dtype=np.float32))
    assert np.allclose(buffer.get("s"), [1.0, 2.0, 3.0, 4.0, 5.0])
