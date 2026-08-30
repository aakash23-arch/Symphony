import pytest
from datetime import datetime, timezone
from voiceshield.contracts import EvidenceVector, ExpertStatus, DecisionBand
from voiceshield.fusion import StandardBeliefAccumulator, FusionConfig

@pytest.fixture
def base_evidence():
    return EvidenceVector(
        session_id="test_session",
        frame_id=0,
        p_spec=0.1,
        p_raw=0.1,
        p_ssl=0.1,
        p_spk=0.1,
        p_beh=0.1,
        p_rep=0.1,
        expert_statuses={
            "E1": ExpertStatus.OK,
            "E2": ExpertStatus.OK,
            "E3": ExpertStatus.OK,
            "E4": ExpertStatus.OK,
            "E5": ExpertStatus.OK,
            "E6": ExpertStatus.OK,
        },
        expert_confidences={
            "E1": 1.0, "E2": 1.0, "E3": 1.0, "E4": 1.0, "E5": 1.0, "E6": 1.0
        },
        q_t=1.0,
        timestamp=datetime.now(timezone.utc)
    )

def test_all_experts_available(base_evidence):
    accum = StandardBeliefAccumulator()
    belief = accum.update("test_session", base_evidence)
    
    # Very low spoof probabilities -> GENUINE
    assert belief.band == DecisionBand.GENUINE
    assert belief.P_spoof < 0.2
    assert belief.confidence > 0.9
    assert len(belief.contributing_experts) == 6

def test_one_expert_unavailable(base_evidence):
    base_evidence.expert_statuses["E4"] = ExpertStatus.MODEL_UNAVAILABLE
    base_evidence.p_spk = None
    
    accum = StandardBeliefAccumulator()
    belief = accum.update("test_session", base_evidence)
    
    assert belief.band == DecisionBand.GENUINE
    # P_spoof shouldn't drop to 0 just because E4 is missing
    assert belief.P_spoof > 0.05
    # Confidence should drop because E4 is missing
    assert belief.confidence < 1.0
    assert len(belief.contributing_experts) == 5

def test_poor_audio(base_evidence):
    # Perfect audio
    accum_good = StandardBeliefAccumulator()
    belief_good = accum_good.update("good_session", base_evidence)
    
    # Poor audio
    base_evidence.q_t = 0.2
    accum_bad = StandardBeliefAccumulator()
    belief_bad = accum_bad.update("bad_session", base_evidence)
    
    # Confidence should drop significantly due to quality-sensitive weights reducing
    assert belief_bad.confidence < belief_good.confidence

def test_contradictory_evidence(base_evidence):
    # High variance
    base_evidence.p_spec = 1.0
    base_evidence.p_raw = 0.0
    base_evidence.p_ssl = 1.0
    base_evidence.p_spk = 0.0
    base_evidence.p_beh = 1.0
    base_evidence.p_rep = 0.0
    
    accum = StandardBeliefAccumulator(FusionConfig(variance_penalty=3.0))
    belief = accum.update("test_session", base_evidence)
    
    # Should trigger UNCERTAIN due to high variance penalty
    assert belief.band == DecisionBand.UNCERTAIN

def test_high_spoof_evidence(base_evidence):
    base_evidence.p_spec = 0.95
    base_evidence.p_raw = 0.95
    base_evidence.p_ssl = 0.95
    base_evidence.p_spk = 0.95
    base_evidence.p_beh = 0.95
    base_evidence.p_rep = 0.95
    
    accum = StandardBeliefAccumulator(FusionConfig(smoothing_time_constant=0.01)) # Fast smoothing for test
    belief = accum.update("test_session", base_evidence)
    
    # Ensure EMA reaches critical in a few frames
    for _ in range(5):
        belief = accum.update("test_session", base_evidence)
        
    assert belief.band == DecisionBand.SYNTHETIC_HIGH_CONFIDENCE
    assert belief.P_spoof > 0.85

def test_high_speaker_mismatch(base_evidence):
    # Only E4 says spoof
    base_evidence.p_spk = 1.0
    
    accum = StandardBeliefAccumulator(FusionConfig(smoothing_time_constant=0.01))
    
    for _ in range(5):
        belief = accum.update("test_session", base_evidence)
        
    # Should rise to suspicious since E4 has high weight (1.5)
    assert belief.P_spoof > 0.1 # Should be pulled up from 0.1 baseline
    assert belief.band in [DecisionBand.SUSPICIOUS, DecisionBand.UNCERTAIN, DecisionBand.GENUINE]

def test_low_confidence(base_evidence):
    base_evidence.expert_confidences["E1"] = 0.1
    base_evidence.expert_confidences["E2"] = 0.1
    base_evidence.expert_confidences["E3"] = 0.1
    base_evidence.expert_confidences["E4"] = 0.1
    base_evidence.expert_confidences["E5"] = 0.1
    base_evidence.expert_confidences["E6"] = 0.1
    
    accum = StandardBeliefAccumulator()
    belief = accum.update("test_session", base_evidence)
    
    assert belief.confidence < 0.4
    assert belief.band == DecisionBand.UNCERTAIN

def test_temporal_smoothing(base_evidence):
    accum = StandardBeliefAccumulator(FusionConfig(smoothing_time_constant=1.0)) # Slow smoothing
    
    # Frame 0: Genuine
    accum.update("test_session", base_evidence)
    
    # Frame 1: Sudden spike
    spike_evidence = base_evidence.model_copy()
    spike_evidence.frame_id = 1
    spike_evidence.p_spec = 1.0
    spike_evidence.p_raw = 1.0
    spike_evidence.p_ssl = 1.0
    spike_evidence.p_spk = 1.0
    
    belief = accum.update("test_session", spike_evidence)
    
    # Even though current frame is 1.0, smoothed should not immediately reach 1.0
    assert belief.P_spoof < 0.85
    assert belief.band != DecisionBand.SYNTHETIC_HIGH_CONFIDENCE
