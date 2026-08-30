"""Tests verifying data contract invariance (I1, I3, §6)."""

from datetime import datetime, timezone
import pytest
from pydantic import ValidationError

from voiceshield.contracts import (
    ClockType,
    Decision,
    DecisionBand,
    EvidenceRecord,
    EvidenceVector,
    ExpertResult,
    ExpertScoreSummary,
    ExpertStatus,
    FrameObject,
    PolicyAction,
    ProvenanceType,
    RiskAssessment,
    RiskBand,
    RiskState,
    TransactionTier,
    VoiceBelief,
    ContextVector,
    TransactionContext,
)


def test_frame_object_forbids_extra_fields():
    with pytest.raises(ValidationError):
        FrameObject(
            session_id="s1",
            frame_id=1,
            pcm=[0.0] * 320,
            t_start=0.0,
            t_end=0.02,
            created_at=datetime.now(timezone.utc),
            forbidden_custom_field="malicious_payload",
        )


def test_evidence_vector_contains_no_pcm_field():
    """Physical enforcement of Invariant P2/I2: EvidenceVector contains no PCM."""
    ev_fields = EvidenceVector.model_fields.keys()
    assert "pcm" not in ev_fields
    assert "raw_pcm" not in ev_fields
    assert "audio" not in ev_fields


def test_evidence_vector_instantiation():
    ev = EvidenceVector(
        session_id="s1",
        frame_id=1,
        p_spec=0.85,
        p_raw=None,
        p_ssl=0.90,
        p_spk=None,
        p_beh=None,
        p_rep=None,
        expert_statuses={
            "E1": ExpertStatus.OK,
            "E2": ExpertStatus.MODEL_UNAVAILABLE,
            "E3": ExpertStatus.OK,
            "E4": ExpertStatus.ABSTAIN,
            "E5": ExpertStatus.DEFERRED,
            "E6": ExpertStatus.DEFERRED,
        },
        timestamp=datetime.now(timezone.utc),
    )
    assert ev.p_spec == 0.85
    assert ev.expert_statuses["E4"] == ExpertStatus.ABSTAIN


def test_decision_contract_validation():
    risk = RiskAssessment(
        session_id="s1",
        risk_score=0.82,
        risk_confidence=0.91,
        risk_band=RiskBand.HIGH,
        timestamp=datetime.now(timezone.utc),
    )
    decision = Decision(
        decision_id="d1",
        session_id="s1",
        voice_belief_ref="vb-123",
        risk=risk,
        transaction_tier=TransactionTier.TIER_3,
        action=PolicyAction.HOLD,
        state=RiskState.HIGH_RISK,
        reason_codes=["SYNTHETIC_HIGH_CONFIDENCE", "TIER_3_RESTRICTION"],
        policy_version="1.0.0",
        clock=ClockType.SLOW,
        timestamp=datetime.now(timezone.utc),
    )
    assert decision.action == PolicyAction.HOLD
    assert decision.transaction_tier == 3
