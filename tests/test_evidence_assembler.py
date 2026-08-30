"""EvidenceVector assembly and the physical proof of privacy principle P2.

Category 7: output schema validation.
"""

import asyncio
from datetime import datetime, timezone

import numpy as np
import pytest

from voiceshield.contracts import EvidenceVector, ExpertResult, ExpertStatus, FrameObject
from voiceshield.evidence import EXPERT_TO_FIELD, StandardEvidenceAssembler
from voiceshield.models import ALL_EXPERT_IDS, ExpertRegistry
from voiceshield.models.bootstrap import register_experts
from voiceshield.signal_processing import FeatureBundle

PCM = [0.101, 0.202, -0.303, 0.404]


def frame(session_id="s1", frame_id=3, pcm=None):
    return FrameObject(
        session_id=session_id,
        frame_id=frame_id,
        pcm=pcm if pcm is not None else list(PCM),
        sample_rate=16000,
        t_start=0.0,
        t_end=0.25,
        q_t=0.83,
        lang_t="UNKNOWN",
        created_at=datetime.now(timezone.utc),
    )


def all_abstaining():
    return [
        ExpertResult(expert_id=eid, status=ExpertStatus.MODEL_UNAVAILABLE, p=None)
        for eid in ALL_EXPERT_IDS
    ]


# --- Privacy: the physical proof of P2 -------------------------------------------


def test_evidence_vector_has_no_pcm_field():
    """The contract itself cannot carry audio. This is P2 made structural."""
    assert "pcm" not in EvidenceVector.model_fields
    assert "raw_pcm" not in EvidenceVector.model_fields
    assert "audio" not in EvidenceVector.model_fields


def test_serialised_evidence_contains_no_audio_samples():
    """No PCM value survives into the serialised message (C-26, P2)."""
    results = all_abstaining()
    evidence = StandardEvidenceAssembler().assemble(frame(), results)
    payload = evidence.model_dump_json()

    assert "pcm" not in payload
    for sample in PCM:
        assert str(sample) not in payload, f"PCM value {sample} leaked into evidence"


def test_evidence_from_a_full_pipeline_run_carries_no_audio():
    """End-to-end: raw PCM goes in, no audio comes out."""
    registry = ExpertRegistry()
    register_experts(registry=registry, warmup=False)

    pcm = (np.random.default_rng(0).standard_normal(4000) * 0.05).astype(np.float32)
    bundle = FeatureBundle(session_id="s1", frame_id=3, raw_pcm=pcm.tolist())
    results = asyncio.run(registry.score_all(bundle))

    evidence = StandardEvidenceAssembler().assemble(frame(pcm=pcm.tolist()), results)
    payload = evidence.model_dump_json()

    assert "pcm" not in payload
    # Spot-check actual sample values rather than only the field name.
    for value in pcm[:20]:
        assert str(float(value)) not in payload


# --- Schema and abstention semantics ---------------------------------------------


def test_all_abstaining_still_publishes_a_complete_vector():
    """C-26: if every expert abstains we still publish, with all probabilities None.

    L4 reads that as UNCERTAIN, which is the correct answer. An absent vector
    would be indistinguishable from a safe one.
    """
    evidence = StandardEvidenceAssembler().assemble(frame(), all_abstaining())

    for field in EXPERT_TO_FIELD.values():
        assert getattr(evidence, field) is None
    assert set(evidence.expert_statuses) == set(ALL_EXPERT_IDS)


def test_expert_results_map_onto_the_correct_contract_fields():
    results = [
        ExpertResult(expert_id="E2", status=ExpertStatus.OK, p=0.75, confidence=0.5, latency_ms=12.0),
        ExpertResult(expert_id="E4", status=ExpertStatus.OK, p=0.10, confidence=0.9, latency_ms=30.0),
    ]
    evidence = StandardEvidenceAssembler().assemble(frame(), results)

    assert evidence.p_raw == 0.75
    assert evidence.p_spk == 0.10
    assert evidence.p_spec is None
    assert evidence.inference_latency_ms["E2"] == 12.0


def test_a_non_ok_expert_cannot_contribute_a_probability():
    """§22: only an OK expert's score reaches the vector, even if one is attached."""
    sneaky = ExpertResult(expert_id="E1", status=ExpertStatus.TIMEOUT, p=0.99)
    evidence = StandardEvidenceAssembler().assemble(frame(), [sneaky])

    assert evidence.p_spec is None
    assert evidence.expert_statuses["E1"] == ExpertStatus.TIMEOUT


def test_frame_context_is_copied_through():
    evidence = StandardEvidenceAssembler().assemble(frame(), all_abstaining())
    assert evidence.session_id == "s1"
    assert evidence.frame_id == 3
    assert evidence.q_t == 0.83


def test_model_versions_record_provenance():
    """Model identity reaches the frozen contract via model_versions[]."""
    signature = "E2:mo-thecreator/Deepfake-audio-detection@abc123"
    evidence = StandardEvidenceAssembler([signature]).assemble(frame(), all_abstaining())
    assert signature in evidence.model_versions


def test_evidence_vector_round_trips():
    """The assembled vector validates against its own schema."""
    evidence = StandardEvidenceAssembler().assemble(frame(), all_abstaining())
    restored = EvidenceVector.model_validate_json(evidence.model_dump_json())
    assert restored.session_id == evidence.session_id
    assert restored.frame_id == evidence.frame_id
