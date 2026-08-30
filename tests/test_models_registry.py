"""Registry dispatch: timeouts, error isolation, availability, independence.

Covers required categories 5 (init failure) and 6 (timeout / inference error).
"""

import asyncio
import logging

import numpy as np
import pytest

from voiceshield.contracts import ExpertResult, ExpertStatus
from voiceshield.models import (
    ALL_EXPERT_IDS,
    E1SpectralExpert,
    E5ProsodyExpert,
    E6ReplayExpert,
    Expert,
    ExpertRegistry,
)
from voiceshield.signal_processing import FeatureBundle


def bundle(session_id="s", frame_id=0):
    return FeatureBundle(session_id=session_id, frame_id=frame_id, raw_pcm=[0.1, 0.2, 0.3])


class ExplodingExpert(Expert):
    """Raises on every call. Must not break the run (C-19)."""

    def __init__(self, expert_id="E2"):
        super().__init__(expert_id=expert_id)

    @property
    def required_features(self):
        return ["raw_pcm"]

    def is_available(self):
        return True

    async def score(self, bundle):
        raise RuntimeError("deliberate expert explosion")


class SleepingExpert(Expert):
    """Exceeds any sane time budget."""

    def __init__(self, expert_id="E3", delay=5.0):
        super().__init__(expert_id=expert_id)
        self._delay = delay

    @property
    def required_features(self):
        return ["raw_pcm"]

    def is_available(self):
        return True

    async def score(self, bundle):
        await asyncio.sleep(self._delay)
        return ExpertResult(expert_id=self.expert_id, status=ExpertStatus.OK, p=0.5)


class MutatingExpert(Expert):
    """Attempts to mutate the shared bundle, to prove isolation is checked."""

    def __init__(self, expert_id="E4"):
        super().__init__(expert_id=expert_id)

    @property
    def required_features(self):
        return ["raw_pcm"]

    def is_available(self):
        return True

    async def score(self, bundle):
        return ExpertResult(expert_id=self.expert_id, status=ExpertStatus.OK, p=0.25)


# --- Category 6: timeout / error ------------------------------------------------


def test_exploding_expert_does_not_break_the_run():
    """One expert raising must not kill the pipeline or the other five."""
    registry = ExpertRegistry()
    registry.register(ExplodingExpert("E2"))
    registry.register(E1SpectralExpert())
    registry.register(E5ProsodyExpert())

    results = asyncio.run(registry.score_all(bundle()))

    assert len(results) == len(ALL_EXPERT_IDS)
    by_id = {r.expert_id: r for r in results}
    assert by_id["E2"].status == ExpertStatus.ERROR
    assert by_id["E2"].p is None
    # The others still produced their honest statuses.
    assert by_id["E1"].status == ExpertStatus.MODEL_UNAVAILABLE
    assert by_id["E5"].status == ExpertStatus.DEFERRED


def test_slow_expert_times_out_without_a_score(monkeypatch):
    """A slow expert yields TIMEOUT with p=None, not a stalled pipeline."""
    from voiceshield.config import settings

    monkeypatch.setattr(settings, "expert_timeout_ms", 50)

    registry = ExpertRegistry()
    registry.register(SleepingExpert("E3", delay=3.0))

    results = asyncio.run(registry.score_all(bundle()))
    by_id = {r.expert_id: r for r in results}
    assert by_id["E3"].status == ExpertStatus.TIMEOUT
    assert by_id["E3"].p is None


def test_timeout_does_not_prevent_other_experts(monkeypatch):
    """A timing-out expert must not suppress its peers' results."""
    from voiceshield.config import settings

    monkeypatch.setattr(settings, "expert_timeout_ms", 50)

    registry = ExpertRegistry()
    registry.register(SleepingExpert("E3", delay=3.0))
    registry.register(E5ProsodyExpert())
    registry.register(E6ReplayExpert())

    by_id = {r.expert_id: r for r in asyncio.run(registry.score_all(bundle()))}
    assert by_id["E3"].status == ExpertStatus.TIMEOUT
    assert by_id["E5"].status == ExpertStatus.DEFERRED
    assert by_id["E6"].status == ExpertStatus.DEFERRED


# --- Completeness and abstention -------------------------------------------------


def test_score_all_always_returns_six_results_in_contract_order():
    """Downstream indexing is total regardless of what is registered."""
    registry = ExpertRegistry()
    registry.register(E1SpectralExpert())
    results = asyncio.run(registry.score_all(bundle()))
    assert [r.expert_id for r in results] == ALL_EXPERT_IDS


def test_no_registered_expert_ever_yields_a_default_probability():
    """§22: no code path invents a number. Every abstention carries p=None."""
    registry = ExpertRegistry()
    registry.register(ExplodingExpert("E2"))
    registry.register(E1SpectralExpert())

    for result in asyncio.run(registry.score_all(bundle())):
        if result.status != ExpertStatus.OK:
            assert result.p is None, f"{result.expert_id} fabricated a score while {result.status}"
            assert result.confidence is None


# --- Category 5: availability reporting / init failure ----------------------------


def test_availability_report_covers_all_six_experts():
    registry = ExpertRegistry()
    report = registry.get_availability_report()
    assert set(report) == set(ALL_EXPERT_IDS)
    assert report["E1"]["status"] == ExpertStatus.MODEL_UNAVAILABLE.value
    assert report["E5"]["status"] == ExpertStatus.DEFERRED.value


def test_startup_log_names_unavailable_experts(caplog):
    """C-27: startup must state plainly which experts are down."""
    registry = ExpertRegistry()
    registry.register(E1SpectralExpert())

    with caplog.at_level(logging.INFO):
        registry.log_availability_report()

    text = caplog.text
    assert "E1" in text
    assert "unavailable" in text.lower() or "MODEL_UNAVAILABLE" in text


def test_registry_with_empty_models_dir_degrades_gracefully(empty_models_dir):
    """With no weights at all, everything abstains and nothing raises."""
    from voiceshield.models.bootstrap import register_experts
    from voiceshield.models.loader import ManifestModelLoader

    loader = ManifestModelLoader(
        models_dir=str(empty_models_dir), manifest_path=str(empty_models_dir / "manifest.json")
    )
    assert loader.load_manifest() is None

    registry = ExpertRegistry()
    register_experts(registry=registry, warmup=False)
    results = asyncio.run(registry.score_all(bundle()))

    assert len(results) == len(ALL_EXPERT_IDS)
    assert all(r.p is None for r in results)


# --- Evidence independence (§6.1) -------------------------------------------------


def test_experts_do_not_receive_other_expert_output():
    """No expert's score() signature accepts an ExpertResult or EvidenceVector."""
    import inspect

    from voiceshield.models import bootstrap

    for expert in bootstrap.build_experts():
        params = inspect.signature(expert.score).parameters
        assert list(params) == ["bundle"], f"{expert.expert_id} takes more than a bundle"


def test_score_all_does_not_mutate_the_shared_bundle():
    """Every expert sees the same unmodified bundle (evidence independence)."""
    registry = ExpertRegistry()
    registry.register(MutatingExpert("E4"))
    registry.register(E1SpectralExpert())

    payload = bundle()
    before = payload.model_dump_json()
    asyncio.run(registry.score_all(payload))
    assert payload.model_dump_json() == before
