"""Tests verifying that abstract interfaces raise NotImplementedError rather than faking outputs."""

import pytest
import numpy as np

from voiceshield.ingestion.sources import AudioSource
from voiceshield.ingestion.pipeline import IngestionPipeline
from voiceshield.signal_processing.dsp import SignalProcessor
from voiceshield.signal_processing.features import FeatureExtractor
from voiceshield.models.base import Expert
from voiceshield.models.registry import ExpertRegistry
from voiceshield.evidence.assembler import EvidenceVectorAssembler
from voiceshield.speaker.enrollment import EnrollmentStore
from voiceshield.fusion.calibrator import Calibrator
from voiceshield.fusion.weighting import QualityConditionedWeighting
from voiceshield.fusion.belief import BeliefAccumulator
from voiceshield.context.context_engine import ContextEngine
from voiceshield.risk.risk_engine import RiskEngine
from voiceshield.decision.tiers import TransactionSensitivity
from voiceshield.decision.policy import PolicyEngine
from voiceshield.decision.state import RiskStateMachine
from voiceshield.decision.actions import ActionEmitter
from voiceshield.assurance.explanation import ExplanationService
from voiceshield.assurance.evidence import EvidenceRecorder
from voiceshield.assurance.privacy import PrivacyController
from voiceshield.assurance.events import EventPublisher
from voiceshield.storage.repository import StorageRepository
from voiceshield.demo.simulator import ScenarioEngine


def test_audio_source_interface():
    class TestSource(AudioSource):
        async def open(self): return await super().open()
        async def read_chunk(self, n): return await super().read_chunk(n)
        async def close(self): return await super().close()
        def stream_chunks(self, n): return super().stream_chunks(n)

    source = TestSource()
    with pytest.raises(NotImplementedError):
        source.stream_chunks(160)


def test_calibrator_interface():
    class TestCalibrator(Calibrator):
        def calibrate(self, eid, score): return super().calibrate(eid, score)
        def is_fitted(self): return super().is_fitted()

    calibrator = TestCalibrator()
    with pytest.raises(NotImplementedError):
        calibrator.calibrate("E1", 0.5)


def test_policy_engine_interface():
    class TestPolicy(PolicyEngine):
        def evaluate_policy(self, risk, tier): return super().evaluate_policy(risk, tier)

    policy = TestPolicy()
    with pytest.raises(NotImplementedError):
        policy.evaluate_policy(None, None)


# The registry's score_all is now implemented. The invariant the original
# NotImplementedError test protected - THE REGISTRY MUST NEVER FABRICATE OUTPUT -
# is preserved below in a stronger form: it now runs, and still refuses to invent
# a probability.


def test_registry_score_all_on_empty_registry_returns_all_unavailable():
    """An empty registry returns six abstentions, never a default probability."""
    import asyncio

    from voiceshield.models.registry import ALL_EXPERT_IDS
    from voiceshield.signal_processing import FeatureBundle

    registry = ExpertRegistry()
    bundle = FeatureBundle(session_id="s", frame_id=0)
    results = asyncio.run(registry.score_all(bundle))

    assert [r.expert_id for r in results] == ALL_EXPERT_IDS
    assert all(r.p is None for r in results)
    assert all(r.confidence is None for r in results)


def test_registry_score_all_rejects_none_bundle():
    """A None bundle raises rather than being quietly tolerated."""
    import asyncio

    registry = ExpertRegistry()
    with pytest.raises(ValueError):
        asyncio.run(registry.score_all(None))


def test_expert_base_score_raises():
    """The Expert ABC still guards its own unimplemented contract."""
    import asyncio

    from voiceshield.models.base import Expert

    class BareExpert(Expert):
        def __init__(self):
            super().__init__(expert_id="EX")

        @property
        def required_features(self):
            return super().required_features

        async def score(self, bundle):
            return await super().score(bundle)

        def is_available(self):
            return super().is_available()

    expert = BareExpert()
    with pytest.raises(NotImplementedError):
        asyncio.run(expert.score(None))
    with pytest.raises(NotImplementedError):
        expert.is_available()
