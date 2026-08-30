"""E4 relative behaviour on REAL speech (C-23 test method).

WHAT THIS IS NOT
    Not an accuracy test. Not an EER. Not a speaker-discrimination claim.
    No evaluation set exists in this workspace (readiness R1).

WHAT IT IS
    A relative separation check: embeddings of the same real speaker must cluster
    much more tightly than a speech-vs-non-speech pair. If that ordering ever
    inverts, the encoder is not doing its job and E4's similarity is worthless.

KNOWN LIMITATION, STATED PLAINLY
    The available corpus (LibriSpeech dummy/demo) contains exactly ONE speaker
    (id 1272), so a true different-speaker pair is NOT available. C-23 asks for
    "same-speaker pair scores higher than different-speaker pair"; we can only
    honestly assert the weaker, still-meaningful version below. Measured values
    at implementation time: same-speaker pairwise cosine 0.9721-0.9901,
    speech-vs-noise 0.4734, speech-vs-tone 0.5760.
"""

import io
import itertools

import numpy as np
import pytest

from conftest import requires_speech_samples, requires_weights

RATE = 16000
pytestmark = [requires_weights, requires_speech_samples]


def load_real_speech(limit=6):
    """Load real LibriSpeech utterances from the cached parquet."""
    from huggingface_hub import hf_hub_download
    import pyarrow.parquet as pq
    import soundfile as sf

    path = hf_hub_download(
        "hf-internal-testing/librispeech_asr_demo",
        "clean/validation-00000-of-00001.parquet",
        repo_type="dataset",
    )
    rows = pq.read_table(path).to_pylist()[:limit]
    clips = []
    for row in rows:
        audio = row["audio"]
        raw = audio["bytes"] if isinstance(audio, dict) else audio
        samples, sr = sf.read(io.BytesIO(raw), dtype="float32")
        assert sr == RATE
        clips.append(samples)
    return clips


@pytest.fixture(scope="module")
def adapter():
    from voiceshield.models.adapters import WavLMXVectorAdapter

    instance = WavLMXVectorAdapter()
    assert instance.load(), "E4 adapter failed to load"
    return instance


def test_same_speaker_clusters_tighter_than_non_speech(adapter):
    """Same-speaker cohesion must clearly exceed speech-vs-non-speech similarity."""
    clips = load_real_speech()
    embeddings = [adapter.embed(clip, RATE) for clip in clips]

    same_speaker = [
        adapter.similarity(a, b) for a, b in itertools.combinations(embeddings, 2)
    ]

    rng = np.random.default_rng(20260828)
    noise = (rng.standard_normal(RATE * 4) * 0.05).astype(np.float32)
    t = np.arange(RATE * 4) / RATE
    tone = (np.sin(2 * np.pi * 180 * t) * 0.8).astype(np.float32)

    non_speech = [adapter.similarity(e, adapter.embed(noise, RATE)) for e in embeddings]
    non_speech += [adapter.similarity(e, adapter.embed(tone, RATE)) for e in embeddings]

    # The separation is large (measured ~0.98 vs ~0.47-0.58), so a strict
    # min > max assertion is safe and far more meaningful than a mean comparison.
    assert min(same_speaker) > max(non_speech), (
        f"same-speaker min {min(same_speaker):.4f} did not exceed "
        f"non-speech max {max(non_speech):.4f}"
    )


def test_same_speaker_similarity_is_high(adapter):
    """Real utterances from one speaker embed close together."""
    clips = load_real_speech(limit=4)
    embeddings = [adapter.embed(clip, RATE) for clip in clips]
    sims = [adapter.similarity(a, b) for a, b in itertools.combinations(embeddings, 2)]
    assert min(sims) > 0.85, f"same-speaker similarity unexpectedly low: {min(sims):.4f}"


def test_verify_polarity_on_real_speech(adapter):
    """A matching real speaker yields LOW p, confirming p means P(inauthentic)."""
    clips = load_real_speech(limit=2)
    reference = adapter.embed(clips[0], RATE)
    result = adapter.verify(clips[1], RATE, reference)

    from voiceshield.contracts import ExpertStatus

    assert result.status == ExpertStatus.OK
    assert result.extra["cosine"] > 0.85
    # High cosine (same speaker) must map to a LOW probability of inauthenticity.
    assert result.p < 0.15
