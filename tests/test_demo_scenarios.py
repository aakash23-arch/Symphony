"""Automated tests for the Demo Scenario Engine (C-51).

Verifies the central invariants:
  1. The scenario engine NEVER directly sets the risk score, decision band or
     action. It only selects audio fixtures, provides context, provides transaction
     context, and starts the session.
  2. The real pipeline produces the result for each mandated scenario:
     - SCENARIO 1 (GENUINE EXECUTIVE) -> LOW RISK / ALLOW
     - SCENARIO 2 (AI VOICE IMPERSONATION) -> HIGH or CRITICAL RISK / HOLD
     - SCENARIO 3 (UNCERTAIN / POOR AUDIO) -> UNCERTAIN / STEP-UP VERIFICATION
  3. Demo Control API endpoints function as specified on both /api and /v1 mounts.
"""

from datetime import datetime, timezone
from decimal import Decimal
import pytest
from fastapi import status

from voiceshield.api.runtime import get_runtime
from voiceshield.contracts import (
    DEMO_ENVIRONMENT_LABEL,
    DecisionBand,
    ExpertContribution,
    PolicyAction,
    RiskBand,
    TransactionState,
    VoiceBelief,
)
from voiceshield.demo.engine import (
    MANDATED_SCENARIOS,
    CASE_01_AUTHENTIC,
    CASE_02_CLONED,
    CASE_03_ADVERSARIAL,
    ScenarioDefinition,
    StandardScenarioEngine,
    default_scenario_engine,
)
from voiceshield.orchestration import AnalysisOrchestrator, OrchestrationConfig
from voiceshield.risk import StandardRiskEngine


@pytest.fixture
def clean_runtime():
    runtime = get_runtime()
    runtime.reset()
    return runtime


@pytest.fixture
def api(client, clean_runtime):
    return client


class TestScenarioCatalogAndImmutability:
    """The scenario engine is an input provider, not an oracle."""

    def test_mandated_scenarios_are_present(self):
        engine = default_scenario_engine
        scenarios = engine.list_scenarios()
        scenario_ids = [s["scenario_id"] for s in scenarios]

        assert "case-01-authentic" in scenario_ids
        assert "case-02-cloned" in scenario_ids
        assert "case-03-adversarial" in scenario_ids

    def test_mandated_scenarios_specify_expected_amounts_and_callers(self):
        s1 = default_scenario_engine.get_scenario("case-01-authentic")
        assert s1 is not None
        assert "CFO" in s1.caller_name
        assert s1.transaction["amount"] == "2500000.00"
        assert s1.transaction["currency"] == "INR"

        s2 = default_scenario_engine.get_scenario("case-02-cloned")
        assert s2 is not None
        assert "CFO" in s2.caller_name
        assert s2.transaction["amount"] == "2500000.00"

        s3 = default_scenario_engine.get_scenario("case-03-adversarial")
        assert s3 is not None
        assert s3.audio_fixture == "case_03_adversarial_manipulated"

    def test_scenario_context_cannot_contain_scoring_fields(self):
        """A scenario that smuggled a score would compromise the demo invariant."""
        illegal_scenario = ScenarioDefinition(
            scenario_id="illegal-oracle",
            title="Illegal Oracle",
            summary="Smuggles a risk score",
            caller_name="Hacker",
            caller_ref="+91 00000 00000",
            audio_fixture="silence",
            context={"claimed_identity": "cfo", "risk_score": 0.05, "band": "LOW"},
        )
        engine = StandardScenarioEngine([illegal_scenario])
        with pytest.raises(ValueError, match="ILLEGAL_SCENARIO_PAYLOAD"):
            import asyncio
            asyncio.run(engine.start_scenario("illegal-oracle", get_runtime()))


class TestScenarioDecisionsViaRealPipeline:
    """The real pipeline must evaluate the scenario signals and produce the required verdict."""

    @pytest.mark.asyncio
    async def test_scenario_1_genuine_executive_yields_low_risk_allow(self, clean_runtime):
        """Scenario 1: Verified CFO + known transaction + clean acoustic belief -> LOW RISK / ALLOW."""
        risk_engine = clean_runtime.orchestrator.risk
        context_engine = clean_runtime.orchestrator.context_engine

        scenario = CASE_01_AUTHENTIC
        session_id = "s_demo_gen_exec"

        # 1. Ingest scenario context into ContextEngine (real pipeline)
        context = context_engine.ingest_context(session_id, scenario.context)

        # 2. Authentic acoustic belief (genuine voice, low spoof probability)
        belief = VoiceBelief(
            session_id=session_id,
            P_spoof=0.04,
            confidence=0.95,
            band=DecisionBand.GENUINE,
            q_call=0.92,
            contributing_experts=[
                ExpertContribution(expert_id="E1", weight=0.33, raw_p=0.04, calibrated_p=0.04),
                ExpertContribution(expert_id="E2", weight=0.33, raw_p=0.03, calibrated_p=0.03),
                ExpertContribution(expert_id="E3", weight=0.34, raw_p=0.05, calibrated_p=0.05),
            ],
            model_versions=["E1:demo@1.0", "E2:demo@1.0", "E3:demo@1.0"],
            timestamp=datetime.now(timezone.utc),
        )

        # 3. Real Risk Engine computes the decision
        decision = risk_engine.assess(session_id, belief, context)

        assert decision.risk.risk_band == RiskBand.LOW, f"Expected LOW risk band, got {decision.risk.risk_band}"
        assert decision.action == PolicyAction.ALLOW, f"Expected ALLOW action, got {decision.action}"
        assert decision.matched_policy == "P-ORDINARY-CALL"

    @pytest.mark.asyncio
    async def test_scenario_2_ai_voice_impersonation_yields_high_critical_hold(self, clean_runtime):
        """Scenario 2: CFO impersonation + high-value transfer + suspicious cues -> HIGH or CRITICAL / HOLD."""
        risk_engine = clean_runtime.orchestrator.risk
        context_engine = clean_runtime.orchestrator.context_engine

        scenario = CASE_02_CLONED
        session_id = "s_demo_ai_spoof"

        # 1. Ingest scenario context (identity mismatch, VoIP, urgent, new offshore beneficiary)
        context = context_engine.ingest_context(session_id, scenario.context)

        # 2. Acoustic voice belief carrying deepfake / synthetic speech indications
        belief = VoiceBelief(
            session_id=session_id,
            P_spoof=0.88,
            confidence=0.92,
            band=DecisionBand.SUSPICIOUS,
            q_call=0.85,
            contributing_experts=[
                ExpertContribution(expert_id="E1", weight=0.33, raw_p=0.85, calibrated_p=0.85),
                ExpertContribution(expert_id="E2", weight=0.33, raw_p=0.92, calibrated_p=0.92),
                ExpertContribution(expert_id="E3", weight=0.34, raw_p=0.87, calibrated_p=0.87),
            ],
            model_versions=["E1:demo@1.0", "E2:demo@1.0", "E3:demo@1.0"],
            timestamp=datetime.now(timezone.utc),
        )

        # 3. Real Risk Engine computes the decision
        decision = risk_engine.assess(session_id, belief, context)

        assert decision.risk.risk_band in (RiskBand.HIGH, RiskBand.CRITICAL), (
            f"Expected HIGH or CRITICAL risk band, got {decision.risk.risk_band}"
        )
        assert decision.action in (PolicyAction.HOLD, PolicyAction.ESCALATE), (
            f"Expected HOLD or ESCALATE action, got {decision.action}"
        )
        assert decision.matched_policy in (
            "P-SUSPICIOUS-VOICE-HIGH-VALUE",
            "P-STRONG-SPEAKER-MISMATCH",
            "P-ELEVATED-CONTEXT",
        )

    @pytest.mark.asyncio
    async def test_scenario_3_poor_audio_yields_uncertain_step_up(self, clean_runtime):
        """Scenario 3: Degraded audio quality below floor -> UNCERTAIN / STEP-UP VERIFICATION."""
        risk_engine = clean_runtime.orchestrator.risk
        context_engine = clean_runtime.orchestrator.context_engine

        scenario = CASE_03_ADVERSARIAL
        session_id = "s_demo_poor_audio"

        # 1. Ingest scenario context
        context = context_engine.ingest_context(session_id, scenario.context)

        # 2. Degraded acoustic belief (q_call below floor, uncertain band)
        belief = VoiceBelief(
            session_id=session_id,
            P_spoof=None,
            confidence=0.20,
            band=DecisionBand.UNCERTAIN,
            q_call=0.25,  # Below quality floor of 0.40
            contributing_experts=[],
            uncertainty_reason="POOR_AUDIO_QUALITY",
            timestamp=datetime.now(timezone.utc),
        )

        # 3. Real Risk Engine computes the decision
        decision = risk_engine.assess(session_id, belief, context)

        assert decision.risk.risk_band == RiskBand.UNCERTAIN, (
            f"Expected UNCERTAIN risk band, got {decision.risk.risk_band}"
        )
        assert decision.action == PolicyAction.STEP_UP, (
            f"Expected STEP_UP action, got {decision.action}"
        )
        assert decision.matched_policy in ("P-INSUFFICIENT-CONFIDENCE", "P-MODEL-UNAVAILABLE")
        assert decision.fail_safe_engaged is True


class TestDemoControlAPI:
    """REST API routes for demo scenarios."""

    def test_list_scenarios_on_both_prefixes(self, api):
        for prefix in ("/api/demo/scenarios", "/v1/demo/scenarios"):
            response = api.get(prefix)
            assert response.status_code == status.HTTP_200_OK
            body = response.json()
            assert "scenarios" in body
            assert len(body["scenarios"]) >= 3
            assert "DEMO" in body["environment"].upper()

    def test_get_scenario_by_id(self, api):
        response = api.get("/api/demo/scenarios/case-01-authentic")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["scenario_id"] == "case-01-authentic"
        assert "CFO" in data["caller_name"]
        assert data["transaction"]["amount"] == "2500000.00"

    def test_get_unknown_scenario_returns_404(self, api):
        response = api.get("/api/demo/scenarios/unknown-nonexistent-scenario")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_start_named_scenario_creates_session_and_transaction(self, api):
        response = api.post(
            "/api/demo/scenarios/case-01-authentic/start",
            params={"speed": 64.0},
        )
        assert response.status_code == status.HTTP_202_ACCEPTED
        body = response.json()
        session_id = body["session_id"]
        assert session_id
        assert body["scenario_id"] == "case-01-authentic"
        assert body["transaction_id"] is not None

        # Verify transaction was created in transaction simulator
        tx_response = api.get(f"/api/transactions/{body['transaction_id']}")
        assert tx_response.status_code == status.HTTP_200_OK
        tx_data = tx_response.json()["transaction"]
        assert tx_data["amount"] == "2500000.00"
        assert tx_data["currency"] == "INR"
        assert tx_data["session_id"] == session_id

    def test_start_unknown_scenario_returns_404(self, api):
        response = api.post("/api/demo/scenarios/nonexistent-scenario/start")
        assert response.status_code == status.HTTP_404_NOT_FOUND
