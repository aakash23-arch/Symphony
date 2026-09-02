"""Smoke test for the deterministic three-case inference.

Runs the sequence:
case-01 -> case-02 -> case-03 -> case-01 -> case-02 -> case-03
and verifies successful completion, deterministic behavior, and proper pipeline states.
"""

import asyncio
import time
import pytest
from fastapi import status
from httpx import AsyncClient, ASGITransport


@pytest.fixture
def clean_runtime():
    from voiceshield.api.runtime import get_runtime
    runtime = get_runtime()
    runtime.reset()
    return runtime


@pytest.fixture
async def async_api(app, clean_runtime):
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            yield client


async def _wait_for_session(api: AsyncClient, session_id: str, timeout: float = 300.0):
    start = time.time()
    while time.time() - start < timeout:
        res = await api.get(f"/v1/sessions/{session_id}")
        if res.status_code == 200:
            data = res.json()
            if data["state"] in ("STOPPED", "FAILED", "INTERRUPTED"):
                return data
        await asyncio.sleep(0.5)
    raise TimeoutError(f"Session {session_id} did not finish within {timeout}s")


@pytest.mark.asyncio
class TestDeterministicSmoke:
    """Verifies the three-case demo sequence behavior."""
    
    async def test_demo_sequence(self, async_api: AsyncClient):
        cases = [
            "case-01-authentic",
            "case-02-cloned",
            "case-03-adversarial",
        ]
        sequence = cases + cases
        
        # Store risk results to compare iterations
        results = {}

        for iteration, case_id in enumerate(sequence):
            # 1. Start the scenario. Use slow speed (0.25) to prevent frame drops due to backpressure in test environments.
            response = await async_api.post(f"/api/demo/scenarios/{case_id}/start", params={"speed": 0.25})
            assert response.status_code == status.HTTP_202_ACCEPTED
            start_data = response.json()
            session_id = start_data["session_id"]
            
            # 2. Wait for completion
            session_state = await _wait_for_session(async_api, session_id)
            assert session_state["state"] == "STOPPED", f"Expected STOPPED, got {session_state['state']}"
            
            # 3. Verify risk response
            risk_res = await async_api.get(f"/api/sessions/{session_id}/risk")
            assert risk_res.status_code == status.HTTP_200_OK
            risk_data = risk_res.json()
            import pprint
            pprint.pprint(risk_data)
            
            # Extract key fields to compare deterministic behavior
            decision = risk_data["decision"]
            band = decision["risk"]["risk_band"]
            action = decision["action"]
            confidence = risk_data["belief"]["confidence"]
            
            result = (band, action, confidence)
            
            if iteration < 3:
                # First pass: record the results
                results[case_id] = result
                
                # Verify basic correctness per case
                if case_id == "case-01-authentic":
                    assert band == "LOW", f"Expected LOW for case-01, got {band}. Result: {result}"
                    assert action == "ALLOW"
                elif case_id == "case-02-cloned":
                    assert band in ("HIGH", "CRITICAL")
                    assert action in ("HOLD", "ESCALATE")
                elif case_id == "case-03-adversarial":
                    assert band == "LOW", f"Expected LOW for case-03, got {band}"
                    assert action == "ALLOW"
            else:
                # Second pass: ensure exact same results as first pass (determinism)
                assert results[case_id] == result, f"Iteration mismatch for {case_id}: expected {results[case_id]}, got {result}"
                
            # Provenance was removed from VoiceBelief in the demo hardening pass
            # because the inference engine no longer carries frontend/demo fakes.
