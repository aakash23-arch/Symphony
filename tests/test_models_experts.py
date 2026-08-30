"""L3 expert behaviour: inference, abstention, malformed input, short audio.

NO ACCURACY ASSERTION APPEARS IN THIS FILE, deliberately. No evaluation set
exists in this workspace (readiness R1), and the demo fixtures are synthetic
tones with no authenticity ground truth. Any probability produced on them is
meaningless. These tests assert MECHANICS - that inference runs, that failures
abstain instead of crashing, that no path invents a score - never correctness of
the score itself. Latency is recorded, never asserted as a performance claim.
"""

import asyncio

import numpy as np
import pytest

from conftest import requires_weights
from voiceshield.contracts import ExpertStatus
from voiceshield.models import (
    MIN_SAMPLES_SPOOF,
    MIN_SAMPLES_XVECTOR,
    E1SpectralExpert,
    E2RawWaveformExpert,
    E3SSLExpert,
    E4SpeakerExpert,
    E5ProsodyExpert,
    E6ReplayExpert,
)
from voiceshield.models import errors as err
from voiceshield.signal_processing import FeatureBundle

RATE = 16000


def bundle(pcm=None, session_id="s", frame_id=0):
    """FeatureBundle carrying raw PCM, as an expert consuming waveform expects."""
    return FeatureBundle(
        session_id=session_id,
        frame_id=frame_id,
        raw_pcm=None if pcm is None else np.asarray(pcm, dtype=np.float32).tolist(),
    )


def noise(n, seed=20260828, amplitude=0.05):
    rng = np.random.default_rng(seed)
    return (rng.standard_normal(n) * amplitude).astype(np.float32)


# --- Category 2: model unavailable --------------------------------------------


def test_e1_reports_weights_not_acquired():
    """E1 abstains because no AASIST weights exist. A truthful state, not a bug."""
    expert = E1SpectralExpert()
    assert expert.is_available() is False
    result = asyncio.run(expert.score(bundle(noise(RATE))))
    assert result.status == ExpertStatus.MODEL_UNAVAILABLE
    assert result.p is None
    assert result.confidence is None


def test_e3_reports_probe_not_trained():
    """E3 abstains: the SSL backbone loads but no trained spoof probe exists."""
    expert = E3SSLExpert()
    assert expert.is_available() is False
    result = asyncio.run(expert.score(bundle(noise(RATE))))
    assert result.status == ExpertStatus.MODEL_UNAVAILABLE
    assert result.p is None


def test_e3_exposes_layer_selection():
    """C-22 layer selection is configurable, not hardcoded to the final layer."""
    assert E3SSLExpert().probe_layers == [4, 8, 12]
    assert E3SSLExpert(layers=[2, 6]).probe_layers == [2, 6]


def test_e5_and_e6_are_deferred_not_deleted():
    """C-25: the contract was not shortened by removing the deferred experts."""
    for expert in (E5ProsodyExpert(), E6ReplayExpert()):
        result = asyncio.run(expert.score(bundle(noise(RATE))))
        assert result.status == ExpertStatus.DEFERRED
        assert result.p is None


# --- Category 3: malformed input ----------------------------------------------


@pytest.mark.parametrize("expert_factory", [E2RawWaveformExpert, E4SpeakerExpert])
def test_experts_abstain_on_missing_raw_pcm(expert_factory):
    """A bundle with no raw_pcm abstains; it never raises and never scores."""
    result = asyncio.run(expert_factory().score(bundle(None)))
    assert result.status in (ExpertStatus.ABSTAIN, ExpertStatus.MODEL_UNAVAILABLE)
    assert result.p is None


@pytest.mark.parametrize("expert_factory", [E2RawWaveformExpert, E4SpeakerExpert])
def test_experts_abstain_on_none_bundle(expert_factory):
    """A None bundle produces an error status, not an exception."""
    result = asyncio.run(expert_factory().score(None))
    assert result.p is None
    assert result.status in (ExpertStatus.ERROR, ExpertStatus.ABSTAIN, ExpertStatus.MODEL_UNAVAILABLE)


@pytest.mark.parametrize("bad", [np.nan, np.inf, -np.inf])
def test_experts_reject_non_finite_audio(bad):
    """NaN/Inf must not reach a forward pass and become a nan 'probability'."""
    pcm = noise(RATE)
    pcm[100] = bad
    result = asyncio.run(E2RawWaveformExpert().score(bundle(pcm)))
    assert result.p is None
    assert result.status in (ExpertStatus.ABSTAIN, ExpertStatus.MODEL_UNAVAILABLE)


def test_empty_pcm_abstains():
    """Zero-length audio abstains rather than crashing."""
    result = asyncio.run(E2RawWaveformExpert().score(bundle(np.zeros(0, dtype=np.float32))))
    assert result.p is None


# --- Category 4: short audio ---------------------------------------------------


@requires_weights
def test_e2_abstains_below_measured_sample_floor():
    """Below the MEASURED 400-sample floor the model raises; we must abstain first."""
    result = asyncio.run(E2RawWaveformExpert().score(bundle(noise(MIN_SAMPLES_SPOOF - 1))))
    assert result.status == ExpertStatus.ABSTAIN
    assert result.p is None


@requires_weights
def test_e4_abstains_below_measured_sample_floor():
    """A 250 ms frame (4000 samples) is below WavLM-SV's 4880-sample floor.

    This is the exact condition the rolling buffer exists to handle: the expert
    must abstain with INSUFFICIENT_AUDIO, never let the RuntimeError escape.
    """
    expert = E4SpeakerExpert()
    result = asyncio.run(expert.score(bundle(noise(4000), session_id="short")))
    assert result.status == ExpertStatus.ABSTAIN
    assert result.p is None


@requires_weights
def test_wavlm_raises_below_floor_which_is_why_we_guard():
    """Proves the floor is real: the raw adapter genuinely raises below it."""
    from voiceshield.models.adapters import WavLMXVectorAdapter

    adapter = WavLMXVectorAdapter()
    assert adapter.load()
    with pytest.raises((ValueError, RuntimeError)):
        adapter.embed(noise(MIN_SAMPLES_XVECTOR - 1), RATE)


# --- Category 1: successful inference ------------------------------------------


@requires_weights
def test_e2_real_inference_succeeds():
    """E2 runs genuine model inference and returns a probability in range."""
    expert = E2RawWaveformExpert()
    assert expert.warmup() is True
    assert expert.is_available() is True

    result = asyncio.run(expert.score(bundle(noise(RATE * 2))))
    assert result.status == ExpertStatus.OK
    assert result.p is not None and 0.0 <= result.p <= 1.0
    assert result.confidence is not None and 0.0 <= result.confidence <= 1.0
    assert result.latency_ms > 0.0
    # Provenance survives the down-conversion via the version signature.
    assert expert.version_signature.startswith("E2:")


@requires_weights
def test_e2_is_deterministic():
    """Identical audio yields a bit-identical score (deterministic eval mode)."""
    expert = E2RawWaveformExpert()
    assert expert.warmup()
    pcm = noise(RATE)
    first = asyncio.run(expert.score(bundle(pcm)))
    second = asyncio.run(expert.score(bundle(pcm)))
    assert first.p == second.p


@requires_weights
def test_e4_embeddings_are_deterministic():
    """The same audio produces a bit-identical embedding across calls."""
    from voiceshield.models.adapters import WavLMXVectorAdapter

    adapter = WavLMXVectorAdapter()
    assert adapter.load()
    pcm = noise(RATE * 2)
    assert np.array_equal(adapter.embed(pcm, RATE), adapter.embed(pcm, RATE))


@requires_weights
def test_e4_embedding_dimension_is_512():
    """WavLMForXVector emits 512-d, NOT the 192-d of the ECAPA it substitutes."""
    from voiceshield.models.adapters import WavLMXVectorAdapter

    adapter = WavLMXVectorAdapter()
    assert adapter.load()
    assert adapter.embedding_dim == 512
    assert adapter.embed(noise(RATE * 2), RATE).shape == (512,)


# --- E4 abstention ladder (C-23) ------------------------------------------------


@requires_weights
def test_e4_abstains_without_enrollment():
    """C-23/§22: an unenrolled speaker ABSTAINS - not a low score, not a high one."""
    from voiceshield.speaker.store import JsonEnrollmentStore

    store = JsonEnrollmentStore(path="/nonexistent/enroll.json", autoload=False)
    expert = E4SpeakerExpert(enrollment=store)
    assert expert.warmup()

    # Feed enough audio that the ONLY remaining reason to abstain is enrollment.
    result = None
    for i in range(12):
        result = asyncio.run(expert.score(bundle(noise(4000, seed=i), session_id="unenrolled", frame_id=i)))
    assert result.status == ExpertStatus.ABSTAIN
    assert result.p is None


@requires_weights
def test_e4_abstains_on_enrollment_dimension_mismatch(tmp_path):
    """A 192-d ECAPA reference vs a 512-d WavLM embedding is incomparable."""
    from voiceshield.speaker.store import JsonEnrollmentStore

    store = JsonEnrollmentStore(path=str(tmp_path / "enroll.json"), autoload=False)
    store.enroll_speaker("mismatch", np.ones(192, dtype=np.float32), persist=False)

    expert = E4SpeakerExpert(enrollment=store)
    assert expert.warmup()

    result = None
    for i in range(12):
        result = asyncio.run(expert.score(bundle(noise(4000, seed=i), session_id="mismatch", frame_id=i)))
    assert result.status == ExpertStatus.ABSTAIN
    assert result.p is None


@requires_weights
def test_e4_scores_when_enrolled_and_buffered(tmp_path):
    """With a matching-dimension reference and enough audio, E4 produces a score."""
    from voiceshield.models.adapters import WavLMXVectorAdapter
    from voiceshield.speaker.store import JsonEnrollmentStore

    adapter = WavLMXVectorAdapter()
    assert adapter.load()
    reference = adapter.embed(noise(RATE * 2, seed=1), RATE)

    store = JsonEnrollmentStore(path=str(tmp_path / "enroll.json"), autoload=False)
    store.enroll_speaker("sess", reference, persist=False)

    expert = E4SpeakerExpert(adapter=adapter, enrollment=store)
    statuses = []
    for i in range(12):
        result = asyncio.run(expert.score(bundle(noise(4000, seed=i), session_id="sess", frame_id=i)))
        statuses.append(result.status)
        if result.status == ExpertStatus.OK:
            assert 0.0 <= result.p <= 1.0
            # Raw cosine is preserved for explanation despite the polarity flip.
            assert result.logits and -1.0 <= result.logits[0] <= 1.0

    assert ExpertStatus.OK in statuses, "E4 never emitted once buffered and enrolled"
    assert ExpertStatus.ABSTAIN in statuses, "E4 should abstain while the buffer fills"


@requires_weights
def test_e4_polarity_is_probability_inauthentic(tmp_path):
    """p must be LOW when the speaker matches, so it means P(inauthentic).

    If this ever inverts, E4's contribution would be read backwards by L4.
    """
    from voiceshield.models.adapters import WavLMXVectorAdapter
    from voiceshield.speaker.store import JsonEnrollmentStore

    adapter = WavLMXVectorAdapter()
    assert adapter.load()
    audio = noise(RATE * 2, seed=7)
    reference = adapter.embed(audio, RATE)

    result = adapter.verify(audio, RATE, reference)
    assert result.status == ExpertStatus.OK
    # Same audio against its own embedding: cosine ~1, so p must be near 0.
    assert result.extra["cosine"] > 0.99
    assert result.p < 0.05
