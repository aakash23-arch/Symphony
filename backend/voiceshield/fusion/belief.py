"""Temporal belief accumulation interface (C-30..C-35)."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from datetime import datetime, timezone
import math

from voiceshield.contracts import EvidenceVector, VoiceBelief, DecisionBand, TrajectoryPoint, ExpertContribution, ClockType, ExpertStatus
from .config import FusionConfig
from .weighting import StandardQualityConditionedWeighting
from .calibrator import StandardCalibrator


class BeliefAccumulator(ABC):
    """Abstract interface for stateful temporal voice belief accumulation."""

    @abstractmethod
    def update(self, session_id: str, evidence: EvidenceVector) -> VoiceBelief:
        """Update session belief state with new evidence."""
        pass

    @abstractmethod
    def get_current_belief(self, session_id: str) -> VoiceBelief:
        """Retrieve current session belief state."""
        pass


class StandardBeliefAccumulator(BeliefAccumulator):
    """Concrete implementation of temporal belief accumulation."""
    
    def __init__(self, config: Optional[FusionConfig] = None):
        self.config = config or FusionConfig()
        self.weighting = StandardQualityConditionedWeighting(self.config)
        self.calibrator = StandardCalibrator()
        
        # State: session_id -> { 'p_smoothed': float, 'trajectory': list, 'last_frame': int }
        self._states: Dict[str, Dict] = {}
        
    def _get_expert_prob(self, evidence: EvidenceVector, expert_id: str) -> Optional[float]:
        mapping = {
            "E1": evidence.p_spec,
            "E2": evidence.p_raw,
            "E3": evidence.p_ssl,
            "E4": evidence.p_spk,
            "E5": evidence.p_beh,
            "E6": evidence.p_rep,
        }
        return mapping.get(expert_id)

    def update(self, session_id: str, evidence: EvidenceVector) -> VoiceBelief:
        if session_id not in self._states:
            self._states[session_id] = {
                'p_smoothed': 0.0,
                'trajectory': [],
                'last_frame': -1
            }
            
        state = self._states[session_id]
        state['last_frame'] = evidence.frame_id
        
        # 1. Weights
        normalized_weights = self.weighting.compute_weights(evidence)
        
        # 2. Frame Probability
        frame_p = 0.0
        active_experts = []
        for eid, w in normalized_weights.items():
            if w > 0:
                raw_p = self._get_expert_prob(evidence, eid)
                if raw_p is not None:
                    calibrated = self.calibrator.calibrate(eid, raw_p)
                    frame_p += w * calibrated
                    
                    active_experts.append(ExpertContribution(
                        expert_id=eid,
                        weight=w,
                        raw_p=raw_p,
                        calibrated_p=calibrated
                    ))
                    
        # If no active experts, frame probability is undefined (0)
        has_experts = sum(normalized_weights.values()) > 0
        
        # 3. Temporal Smoothing (EMA)
        # Approximate dt (for testing, we assume uniform if we don't have exact timestamps per frame)
        # A typical frame is 0.02s hop if 16000sr and 320 hop_length. 
        # But for strict EMA independent of actual frame rate, we can just use a fixed alpha, or estimate from tau.
        # Let's use a fixed beta for now assuming ~50 frames per sec. 
        # beta = 1.0 if not initialized, else based on tau
        dt = 0.02 # Assuming 20ms per frame
        beta = min(1.0, dt / self.config.smoothing_time_constant) if self.config.smoothing_time_constant > 0 else 1.0

        # BUG-05 FIX: The old code only seeded p_smoothed on the first frame when
        # has_experts was True AND trajectory was empty. If the very first frame had
        # no experts (has_experts=False), p_smoothed stayed 0.0. All subsequent
        # frames would then mix real frame_p against that spurious 0.0, producing a
        # systematic downward bias in P_spoof during session warm-up.
        # Fix: track whether p_smoothed has ever been seeded; seed it on the first
        # frame with valid experts regardless of trajectory length.
        p_seeded = state.get('p_seeded', False)
        if has_experts:
            if not p_seeded:
                state['p_smoothed'] = frame_p
                state['p_seeded'] = True
            else:
                state['p_smoothed'] = (1.0 - beta) * state['p_smoothed'] + beta * frame_p

            
        # 4. Confidence Calculation
        # C_base = sum(w'_i) / sum(w_base_i)
        q_t = evidence.q_t if evidence.q_t is not None else 1.0
        w_prime_sum = 0.0
        w_base_sum = 0.0
        
        for eid, base_w in self.config.expert_weights.items():
            w_base_sum += base_w
            if evidence.expert_statuses.get(eid) == ExpertStatus.OK:
                c_i = evidence.expert_confidences.get(eid, 1.0)
                alpha = self.config.quality_sensitivities.get(eid, 0.0)
                q_factor = max(0.0, 1.0 - alpha * (1.0 - q_t))
                w_prime_sum += base_w * c_i * q_factor
                
        c_base = w_prime_sum / w_base_sum if w_base_sum > 0 else 0.0
        
        # Variance
        variance = 0.0
        if has_experts:
            for active in active_experts:
                variance += active.weight * (active.calibrated_p - frame_p)**2
                
        confidence = c_base * max(0.0, 1.0 - self.config.variance_penalty * variance)
        if not has_experts:
            confidence = 0.0
            
        # 5. Band Logic
        p_smoothed = state['p_smoothed']
        if confidence < self.config.threshold_uncertain_confidence or not has_experts:
            band = DecisionBand.UNCERTAIN
            uncertainty_reason = "No active experts available" if not has_experts else "Low confidence (contradictory evidence or poor quality)"
        elif p_smoothed >= self.config.threshold_critical:
            band = DecisionBand.SYNTHETIC_HIGH_CONFIDENCE
            uncertainty_reason = None
        elif p_smoothed >= self.config.threshold_suspicious:
            band = DecisionBand.SUSPICIOUS
            uncertainty_reason = None
        else:
            band = DecisionBand.GENUINE
            uncertainty_reason = None
            
        # 6. Update Trajectory
        t_sec = evidence.frame_id * dt
        traj_point = TrajectoryPoint(
            t=t_sec,
            p_spoof=p_smoothed if has_experts else None,
            confidence=confidence
        )
        state['trajectory'].append(traj_point)
        
        belief = VoiceBelief(
            session_id=session_id,
            P_spoof=p_smoothed if has_experts else None,
            confidence=confidence,
            band=band,
            q_call=q_t,
            spans=[],
            trajectory=list(state['trajectory']), # Copy
            contributing_experts=active_experts,
            uncertainty_reason=uncertainty_reason,
            switch_damping_events=[],
            model_versions=evidence.model_versions,
            clock=ClockType.SLOW,
            timestamp=datetime.now(timezone.utc)
        )
        
        state['last_belief'] = belief
        return belief
        
    def get_current_belief(self, session_id: str) -> VoiceBelief:
        if session_id not in self._states or 'last_belief' not in self._states[session_id]:
            raise ValueError(f"No belief state found for session {session_id}")
        return self._states[session_id]['last_belief']
