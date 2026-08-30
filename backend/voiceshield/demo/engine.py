"""Concrete Demo Scenario Engine (C-51).

This module manages frozen demo scenarios, selects the audio fixture, context,
and transaction context, and starts real pipeline sessions.

INVARIANT (§36):
  The ScenarioEngine must NEVER directly set or inject a risk score, decision
  band, or policy action. It may ONLY:
    - select audio fixture
    - provide context
    - provide transaction context
    - start the session
  The real pipeline must produce the result.
"""

from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from voiceshield.contracts import DEMO_ENVIRONMENT_LABEL
from voiceshield.demo.replay import ReplaySimulator
from voiceshield.demo.simulator import ScenarioEngine
from voiceshield.obs.logging import get_logger

logger = get_logger("voiceshield.demo.engine")

_FIXTURE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "demo" / "audio"

DISALLOWED_CONTEXT_KEYS = {
    "risk",
    "risk_score",
    "risk_band",
    "band",
    "action",
    "decision",
    "verdict",
    "score",
    "policy_action",
    "matched_policy",
}


@dataclass(frozen=True)
class ExpectedOutcome:
    """Expected outcome definition for test assertion and documentation only.
    
    This is NEVER passed to the session, context engine, or risk engine.
    """
    risk_band: str
    action: str
    decision_label: str
    target_policy: Optional[str] = None


@dataclass(frozen=True)
class ScenarioDefinition:
    """A frozen demo scenario specification."""
    scenario_id: str
    title: str
    summary: str
    caller_name: str
    caller_ref: str
    audio_fixture: str
    context: Dict[str, Any]
    transaction: Optional[Dict[str, Any]] = None
    expected_outcome: Optional[ExpectedOutcome] = None

    def to_dict(self) -> Dict[str, Any]:
        data = {
            "scenario_id": self.scenario_id,
            "title": self.title,
            "summary": self.summary,
            "caller_name": self.caller_name,
            "caller_ref": self.caller_ref,
            "audio_fixture": self.audio_fixture,
            "context": dict(self.context),
            "transaction": dict(self.transaction) if self.transaction else None,
            "expected_outcome": asdict(self.expected_outcome) if self.expected_outcome else None,
            "environment": DEMO_ENVIRONMENT_LABEL,
        }
        return data


# --- Mandated Scenario Definitions --------------------------------------------

SCENARIO_1_GENUINE_EXECUTIVE = ScenarioDefinition(
    scenario_id="genuine-executive",
    title="Scenario 1 — Genuine Executive",
    summary="Enrolled executive (CFO) conducting an authorized ₹25,00,000 corporate disbursement over a clean PSTN channel.",
    caller_name="CFO (Ananya Sharma)",
    caller_ref="+91 22 6123 4567",
    audio_fixture="clean_speechlike",
    context={
        "claimed_identity": "cfo.ananya_sharma",
        "verified_identity": "cfo.ananya_sharma",
        "enrollment_status": "ENROLLED",
        "known_contact": "KNOWN_CONTACT",
        "identity_mismatch": False,
        "transaction_type": "WIRE_TRANSFER",
        "beneficiary_novelty": "KNOWN",
        "urgency": False,
        "secrecy": False,
        "callback_refusal": False,
        "workflow_state": "NONE",
        "call_source": "INBOUND_PSTN",
        "voip_mobile_indicator": "MOBILE",
        "reputation": 0.98,
        "age_days": 1825,
        "language": "en",
    },
    transaction={
        "caller_identity": "cfo.ananya_sharma",
        "amount": "2500000.00",
        "currency": "INR",
        "beneficiary": "Apex Infrastructure & Industrial Suppliers Ltd",
        "beneficiary_novelty": "KNOWN",
        "transaction_type": "WIRE_TRANSFER",
    },
    expected_outcome=ExpectedOutcome(
        risk_band="LOW",
        action="ALLOW",
        decision_label="LOW RISK / ALLOW",
        target_policy="P-ORDINARY-CALL",
    ),
)

SCENARIO_2_AI_IMPERSONATION = ScenarioDefinition(
    scenario_id="ai-impersonation",
    title="Scenario 2 — AI Voice Impersonation",
    summary="Voice clone attempting an unauthorized ₹25,00,000 wire to an unverified offshore account with high urgency and callback refusal.",
    caller_name="CFO (Impersonated)",
    caller_ref="+91 99999 88888",
    audio_fixture="clean_speechlike",
    context={
        "claimed_identity": "cfo.ananya_sharma",
        "verified_identity": None,
        "identity_mismatch": True,
        "enrollment_status": "ENROLLED",
        "known_contact": "FIRST_CONTACT",
        "transaction_type": "WIRE_TRANSFER",
        "beneficiary_novelty": "NEW",
        "urgency": True,
        "secrecy": True,
        "callback_refusal": True,
        "workflow_state": "HIGH_VALUE_TRANSFER",
        "sensitive_action": "WIRE_TRANSFER",
        "call_source": "INBOUND_VOIP",
        "voip_mobile_indicator": "VOIP",
        "reputation": 0.12,
        "age_days": 2,
        "language": "en",
    },
    transaction={
        "caller_identity": "cfo.ananya_sharma",
        "amount": "2500000.00",
        "currency": "INR",
        "beneficiary": "Nexus Holdings Offshore Ltd (Unverified Payee)",
        "beneficiary_novelty": "NEW",
        "transaction_type": "WIRE_TRANSFER",
    },
    expected_outcome=ExpectedOutcome(
        risk_band="HIGH",
        action="HOLD",
        decision_label="HIGH or CRITICAL RISK / HOLD",
        target_policy="P-SUSPICIOUS-VOICE-HIGH-VALUE",
    ),
)

SCENARIO_3_POOR_AUDIO = ScenarioDefinition(
    scenario_id="poor-audio",
    title="Scenario 3 — Uncertain / Poor Audio",
    summary="Severely degraded acoustic channel and noise during a ₹25,00,000 corporate transfer triggering fail-safe step-up verification.",
    caller_name="CFO Office (Degraded Line)",
    caller_ref="+91 22 4000 9999",
    audio_fixture="noisy_speechlike",
    context={
        "claimed_identity": "cfo.ananya_sharma",
        "enrollment_status": "ENROLLED",
        "known_contact": "UNKNOWN",
        "transaction_type": "WIRE_TRANSFER",
        "beneficiary_novelty": "KNOWN",
        "call_source": "INBOUND_VOIP",
        "language": "en",
    },
    transaction={
        "caller_identity": "cfo.ananya_sharma",
        "amount": "2500000.00",
        "currency": "INR",
        "beneficiary": "Apex Infrastructure & Industrial Suppliers Ltd",
        "beneficiary_novelty": "KNOWN",
        "transaction_type": "WIRE_TRANSFER",
    },
    expected_outcome=ExpectedOutcome(
        risk_band="UNCERTAIN",
        action="STEP_UP",
        decision_label="UNCERTAIN / STEP-UP VERIFICATION",
        target_policy="P-INSUFFICIENT-CONFIDENCE",
    ),
)

MANDATED_SCENARIOS: List[ScenarioDefinition] = [
    SCENARIO_1_GENUINE_EXECUTIVE,
    SCENARIO_2_AI_IMPERSONATION,
    SCENARIO_3_POOR_AUDIO,
]


class StandardScenarioEngine(ScenarioEngine):
    """Concrete scenario engine managing demo scenarios and session initialization."""

    def __init__(self, scenarios: Optional[List[ScenarioDefinition]] = None):
        self._scenarios: Dict[str, ScenarioDefinition] = {
            s.scenario_id: s for s in (scenarios or MANDATED_SCENARIOS)
        }

    def list_scenarios(self) -> List[Dict[str, Any]]:
        """List all available demo scenarios with full metadata."""
        return [s.to_dict() for s in self._scenarios.values()]

    def get_scenario(self, scenario_id: str) -> Optional[ScenarioDefinition]:
        """Retrieve scenario definition by ID."""
        return self._scenarios.get(scenario_id)

    async def start_scenario(
        self,
        scenario_id: str,
        runtime: Optional[Any] = None,
        speed: float = 1.0,
    ) -> Dict[str, Any]:
        """Start a session initialized with the specified scenario fixture.
        
        The scenario engine ONLY supplies the audio fixture, call context, and
        transaction context. The real pipeline produces the risk evaluation.
        """
        scenario = self.get_scenario(scenario_id)
        if scenario is None:
            raise KeyError(f"SCENARIO_NOT_FOUND: Unknown demo scenario '{scenario_id}'")

        # Verify no scoring keys exist in the context payload
        forbidden = set(scenario.context.keys()) & DISALLOWED_CONTEXT_KEYS
        if forbidden:
            raise ValueError(f"ILLEGAL_SCENARIO_PAYLOAD: Scoring keys {forbidden} not allowed in context")

        if runtime is None:
            from voiceshield.api.runtime import get_runtime
            runtime = get_runtime()

        # 1. Create the session
        session_record = runtime.sessions.create(
            source_type="wav",
            scenario_id=scenario.scenario_id,
            caller_ref=scenario.caller_ref,
        )
        session_id = session_record.session_id

        # 2. Ingest transaction if present
        transaction_id: Optional[str] = None
        if scenario.transaction:
            tx_data = dict(scenario.transaction)
            created_tx = runtime.transactions.create_transaction(
                caller_identity=tx_data["caller_identity"],
                amount=tx_data["amount"],
                beneficiary=tx_data["beneficiary"],
                beneficiary_novelty=tx_data.get("beneficiary_novelty", "KNOWN"),
                currency=tx_data.get("currency", "INR"),
                transaction_type=tx_data.get("transaction_type", "WIRE_TRANSFER"),
                session_id=session_id,
            )
            transaction_id = created_tx.transaction_id
            runtime.orchestrator.link_transaction(session_id, transaction_id)

        # 3. Ingest context vector
        if scenario.context:
            runtime.orchestrator.ingest_context(session_id, scenario.context)

        # 4. Start orchestrator
        await runtime.orchestrator.start(session_id)

        # 5. Start audio replay in background
        fixture_path = _FIXTURE_DIR / f"{scenario.audio_fixture}.wav"
        if not fixture_path.is_file():
            logger.warning(f"Audio fixture {fixture_path} not found on disk")

        async def _drive() -> None:
            try:
                simulator = ReplaySimulator(
                    fixture_path,
                    pipeline=runtime.pipeline,
                    speed=speed,
                    session_id=session_id,
                    scenario_id=scenario.scenario_id,
                )
                await simulator.run(on_frame=runtime.make_frame_sink(session_id))
            except Exception as exc:
                logger.error(
                    "Replay task failed",
                    extra={"extra_fields": {"session_id": session_id, "error": str(exc)}},
                )
            finally:
                await runtime.orchestrator.drain(session_id)

        runtime.spawn(_drive())

        return {
            "session_id": session_id,
            "scenario_id": scenario.scenario_id,
            "transaction_id": transaction_id,
            "audio_fixture": scenario.audio_fixture,
            "caller_name": scenario.caller_name,
            "caller_ref": scenario.caller_ref,
            "state": session_record.state.value,
            "environment": DEMO_ENVIRONMENT_LABEL,
        }


# Global default instance
default_scenario_engine = StandardScenarioEngine()
