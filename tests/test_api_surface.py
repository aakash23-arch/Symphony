"""Tests for the complete FastAPI surface (Gate 10).

Covers the thirteen requested endpoints on both mounts, the structured error
envelope, input validation, explicit timestamps, and the guarantee that no
response can carry raw audio.
"""

import pytest
from fastapi import status

from voiceshield.contracts import DEMO_ENVIRONMENT_LABEL

#: The endpoints the gate asked for, as (method, path template) pairs.
REQUESTED_ROUTES = [
    ("get", "/health"),
    ("post", "/api/sessions"),
    ("get", "/api/sessions/{session_id}"),
    ("post", "/api/sessions/{session_id}/start"),
    ("post", "/api/sessions/{session_id}/stop"),
    ("get", "/api/sessions/{session_id}/risk"),
    ("get", "/api/sessions/{session_id}/evidence"),
    ("get", "/api/sessions/{session_id}/timeline"),
    ("post", "/api/transactions"),
    ("get", "/api/transactions/{transaction_id}"),
    ("post", "/api/transactions/{transaction_id}/hold"),
    ("post", "/api/transactions/{transaction_id}/release"),
]

#: Property names that would indicate audio leaking into a response.
AUDIO_FIELDS = {"pcm", "audio", "samples", "waveform", "raw_pcm", "audio_bytes"}


@pytest.fixture
def api(client):
    """Test client with a clean runtime, so sessions do not leak between tests."""
    from voiceshield.api.runtime import get_runtime

    runtime = get_runtime()
    runtime.reset()
    return client


def new_session(api, **overrides) -> str:
    payload = {"source_type": "wav"}
    payload.update(overrides)
    response = api.post("/api/sessions", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()["session_id"]


def new_transaction(api, **overrides) -> str:
    payload = {"caller_identity": "alice", "amount": "5000.00", "beneficiary": "acme"}
    payload.update(overrides)
    response = api.post("/api/transactions", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()["transaction"]["transaction_id"]


# =============================================================================
# Route surface
# =============================================================================


class TestRouteSurface:
    @pytest.mark.parametrize("method,path", REQUESTED_ROUTES)
    def test_every_requested_route_exists(self, api, method, path):
        """The gate's list, checked against the generated OpenAPI document."""
        spec = api.get("/openapi.json").json()
        assert path in spec["paths"], f"missing route: {path}"
        assert method in spec["paths"][path], f"{path} does not accept {method.upper()}"

    def test_the_spec_surface_is_still_mounted(self, api):
        """§12 froze the /v1 shape; the /api mount is additive, not a move."""
        spec = api.get("/openapi.json").json()
        for path in ("/v1/sessions", "/v1/sessions/{session_id}/risk", "/v1/health"):
            assert path in spec["paths"]

    def test_both_mounts_reach_the_same_handler(self, api):
        """A session created on one prefix must be visible on the other."""
        session_id = new_session(api)
        v1 = api.get(f"/v1/sessions/{session_id}")
        api_mount = api.get(f"/api/sessions/{session_id}")
        assert v1.status_code == api_mount.status_code == status.HTTP_200_OK
        assert v1.json()["session_id"] == api_mount.json()["session_id"]

    def test_operation_ids_are_unique(self, api):
        """Duplicate operationIds would make the OpenAPI document invalid."""
        spec = api.get("/openapi.json").json()
        ids = [
            operation["operationId"]
            for methods in spec["paths"].values()
            for operation in methods.values()
            if "operationId" in operation
        ]
        assert len(ids) == len(set(ids))

    def test_the_session_websocket_is_registered(self, api):
        """WebSocket routes are absent from OpenAPI, so check the route table.

        The tree is nested (mounted routers hold their own routes), so this
        walks it rather than reading only the top level.
        """
        from voiceshield.api.app import create_app

        paths = set()

        def walk(routes):
            for route in routes:
                path = getattr(route, "path", None)
                if path:
                    paths.add(path)
                # This FastAPI version wraps each include_router call in an
                # _IncludedRouter holding its own .router, so both attributes
                # have to be followed to see the whole table.
                nested = getattr(route, "routes", None)
                if nested:
                    walk(nested)
                for attribute in ("router", "original_router"):
                    inner = getattr(route, attribute, None)
                    if inner is not None and getattr(inner, "routes", None):
                        walk(inner.routes)

        walk(create_app().routes)
        assert "/ws/sessions/{session_id}" in paths
        # The L1-only events socket keeps its documented contract.
        assert "/v1/sessions/{session_id}/events" in paths


# =============================================================================
# No raw audio may leave through the API
# =============================================================================


class TestNoAudioExposure:
    def test_no_response_schema_exposes_pcm(self, api):
        """Structural guard: walk every schema the API can return."""
        spec = api.get("/openapi.json").json()
        offenders = []
        for name, schema in spec.get("components", {}).get("schemas", {}).items():
            for prop in (schema.get("properties") or {}):
                if prop.lower() in AUDIO_FIELDS:
                    offenders.append(f"{name}.{prop}")
        assert not offenders, f"audio fields reachable from a response: {offenders}"

    def test_the_evidence_response_carries_no_audio(self, api):
        session_id = new_session(api)
        body = api.get(f"/api/sessions/{session_id}/evidence").text
        assert "pcm" not in body.lower()

    def test_the_timeline_carries_no_audio(self, api):
        session_id = new_session(api)
        body = api.get(f"/api/sessions/{session_id}/timeline").text
        assert "pcm" not in body.lower()


# =============================================================================
# Sessions
# =============================================================================


class TestSessionRoutes:
    def test_create_returns_a_session_id(self, api):
        response = api.post("/api/sessions", json={"source_type": "wav"})
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["state"] == "CREATED"

    def test_create_rejects_unknown_fields(self, api):
        response = api.post("/api/sessions", json={"source_type": "wav", "risk_score": 0.1})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_get_reports_analysis_progress(self, api):
        session_id = new_session(api)
        body = api.get(f"/api/sessions/{session_id}").json()
        assert body["frames_scored"] == 0
        assert body["has_assessment"] is False

    def test_get_of_an_unknown_session_is_404(self, api):
        response = api.get("/api/sessions/no-such-session")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["error"]["code"]

    def test_start_then_stop(self, api):
        session_id = new_session(api)
        started = api.post(f"/api/sessions/{session_id}/start")
        assert started.status_code == status.HTTP_202_ACCEPTED
        assert started.json()["state"] == "RUNNING"
        stopped = api.post(f"/api/sessions/{session_id}/stop")
        assert stopped.status_code == status.HTTP_202_ACCEPTED
        assert stopped.json()["state"] == "STOPPED"

    def test_starting_twice_is_a_conflict(self, api):
        """A duplicate start must never silently restart an in-flight session."""
        session_id = new_session(api)
        api.post(f"/api/sessions/{session_id}/start")
        response = api.post(f"/api/sessions/{session_id}/start")
        assert response.status_code == status.HTTP_409_CONFLICT

    def test_starting_an_unknown_session_is_404(self, api):
        assert api.post("/api/sessions/ghost/start").status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# Risk — the no-assessment guard
# =============================================================================


class TestRiskRoute:
    def test_risk_before_any_analysis_is_409_not_a_zero_score(self, api):
        """The load-bearing API guarantee.

        Returning 200 with risk_score 0.0 would paint a green LOW panel for a
        call the system has said nothing about.
        """
        session_id = new_session(api)
        response = api.get(f"/api/sessions/{session_id}/risk")
        assert response.status_code == status.HTTP_409_CONFLICT
        error = response.json()["error"]
        assert error["code"] == "RISK_NOT_YET_AVAILABLE"
        assert "0.0" not in response.text
        assert "risk_score" not in response.text

    def test_the_no_assessment_error_tells_the_client_to_retry(self, api):
        """Absence of a verdict is not a verdict; the client should poll."""
        session_id = new_session(api)
        error = api.get(f"/api/sessions/{session_id}/risk").json()["error"]
        assert error["retriable"] is True

    def test_risk_for_an_unknown_session_is_404(self, api):
        assert api.get("/api/sessions/ghost/risk").status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# Evidence
# =============================================================================


class TestEvidenceRoute:
    def test_evidence_answers_before_any_analysis(self, api):
        """Unlike a score, an empty evidence set is a truthful statement."""
        session_id = new_session(api)
        response = api.get(f"/api/sessions/{session_id}/evidence")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["experts"] == []

    def test_it_declares_that_it_is_not_hash_chained(self, api):
        """No reader may infer tamper-evidence this build does not provide."""
        session_id = new_session(api)
        body = api.get(f"/api/sessions/{session_id}/evidence").json()
        assert body["hash_chained"] is False
        assert body["chain_status"] == "NOT_IMPLEMENTED"
        assert body["record_type"] == "LIVE_ANALYSIS_SUMMARY"

    def test_evidence_for_an_unknown_session_is_404(self, api):
        assert api.get("/api/sessions/ghost/evidence").status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# Timeline
# =============================================================================


class TestTimelineRoute:
    def test_an_unstarted_session_has_an_empty_timeline(self, api):
        session_id = new_session(api)
        body = api.get(f"/api/sessions/{session_id}/timeline").json()
        assert body["entries"] == []
        assert body["truncated"] is False

    def test_starting_a_session_records_an_entry(self, api):
        session_id = new_session(api)
        api.post(f"/api/sessions/{session_id}/start")
        entries = api.get(f"/api/sessions/{session_id}/timeline").json()["entries"]
        assert any(entry["kind"] == "ANALYSIS_STARTED" for entry in entries)

    def test_since_seq_filters_earlier_entries(self, api):
        session_id = new_session(api)
        api.post(f"/api/sessions/{session_id}/start")
        entries = api.get(f"/api/sessions/{session_id}/timeline").json()["entries"]
        last = entries[-1]["seq"]
        filtered = api.get(
            f"/api/sessions/{session_id}/timeline", params={"since_seq": last}
        ).json()["entries"]
        assert filtered == []

    def test_an_out_of_range_limit_is_rejected(self, api):
        session_id = new_session(api)
        response = api.get(f"/api/sessions/{session_id}/timeline", params={"limit": 9999})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# =============================================================================
# Context
# =============================================================================


class TestContextRoute:
    def test_context_is_accepted_and_parsed(self, api):
        session_id = new_session(api)
        response = api.post(
            f"/api/sessions/{session_id}/context",
            json={"claimed_identity": "alice", "transaction_type": "WIRE_TRANSFER"},
        )
        assert response.status_code == status.HTTP_202_ACCEPTED
        assert response.json()["context"]["identity"]["claimed_identity"] == "alice"

    def test_a_scoring_field_is_rejected(self, api):
        """Context describes a call; it may never carry a verdict."""
        session_id = new_session(api)
        response = api.post(
            f"/api/sessions/{session_id}/context", json={"risk_score": 0.9}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "SCORING_FIELD_REJECTED" in response.json()["error"]["message"]

    def test_a_scoring_field_nested_in_a_subobject_is_also_rejected(self, api):
        """A score must not be smuggled in one level down."""
        session_id = new_session(api)
        response = api.post(
            f"/api/sessions/{session_id}/context",
            json={"identity": {"claimed_identity": "a"}, "transaction": {"P_spoof": 0.9}},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_a_non_object_payload_is_rejected(self, api):
        session_id = new_session(api)
        response = api.post(f"/api/sessions/{session_id}/context", json=["not", "an", "object"])
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# =============================================================================
# Transactions
# =============================================================================


class TestTransactionRoutes:
    def test_create_and_view(self, api):
        transaction_id = new_transaction(api)
        response = api.get(f"/api/transactions/{transaction_id}")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["environment"] == DEMO_ENVIRONMENT_LABEL

    def test_hold_then_release(self, api):
        transaction_id = new_transaction(api)
        held = api.post(f"/api/transactions/{transaction_id}/hold", json={"reason": "voice risk"})
        assert held.json()["transaction"]["state"] == "HELD"
        released = api.post(
            f"/api/transactions/{transaction_id}/release",
            json={"verification_reference": "CALLBACK-8891"},
        )
        assert released.json()["transaction"]["state"] == "APPROVED"

    def test_release_requires_a_verification_reference(self, api):
        transaction_id = new_transaction(api)
        api.post(f"/api/transactions/{transaction_id}/hold", json={})
        response = api.post(
            f"/api/transactions/{transaction_id}/release", json={"verification_reference": ""}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_a_missing_required_field_is_rejected(self, api):
        response = api.post("/api/transactions", json={"caller_identity": "alice"})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_view_of_an_unknown_transaction_is_404(self, api):
        assert api.get("/api/transactions/ghost").status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# Structured errors
# =============================================================================


class TestErrorEnvelope:
    def test_every_error_uses_the_same_envelope(self, api):
        """One shape for every failure, so a client needs no special cases."""
        responses = [
            api.get("/api/sessions/ghost"),
            api.get("/api/transactions/ghost"),
            api.post("/api/sessions", json={"bogus": 1}),
            api.get(f"/api/sessions/{new_session(api)}/risk"),
        ]
        for response in responses:
            assert response.status_code >= 400
            body = response.json()
            assert "error" in body, body
            assert set(body["error"]) == {
                "code", "message", "session_id", "correlation_id", "retriable"
            }

    def test_validation_errors_use_the_envelope_not_fastapis_default(self, api):
        """FastAPI's default 422 body is {"detail": [...]}, which would be the
        one error shape a client has to handle differently."""
        response = api.post("/api/sessions", json={"source_type": 12345, "bogus": True})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        body = response.json()
        assert "detail" not in body
        assert body["error"]["code"] == "VALIDATION_ERROR"

    def test_no_internal_exception_leaks_into_a_response(self, api):
        """A traceback or exception class name would leak implementation detail."""
        for response in (
            api.get("/api/sessions/ghost"),
            api.get("/api/transactions/ghost"),
            api.post("/api/sessions", json={"bogus": 1}),
        ):
            text = response.text
            assert "Traceback" not in text
            assert "voiceshield." not in text
            for leak in ("KeyError", "ValueError", "AttributeError", "Exception("):
                assert leak not in text

    def test_the_correlation_id_is_echoed(self, api):
        response = api.get("/api/sessions/ghost", headers={"X-Correlation-ID": "trace-42"})
        assert response.headers["X-Correlation-ID"] == "trace-42"
        assert response.json()["error"]["correlation_id"] == "trace-42"


# =============================================================================
# Explicit timestamps
# =============================================================================


class TestTimestamps:
    def test_responses_carry_an_explicit_served_at(self, api):
        session_id = new_session(api)
        for path in (
            f"/api/sessions/{session_id}",
            f"/api/sessions/{session_id}/evidence",
            f"/api/sessions/{session_id}/timeline",
        ):
            body = api.get(path).json()
            assert "served_at" in body, path

    def test_timestamps_are_timezone_qualified(self, api):
        """A naive timestamp is ambiguous the moment it crosses a boundary.

        Accepts the ``Z`` suffix as well as ``+00:00``: both are valid ISO 8601
        UTC, but Python 3.10's ``fromisoformat`` only parses the latter.
        """
        from datetime import datetime

        session_id = new_session(api)
        served_at = api.get(f"/api/sessions/{session_id}").json()["served_at"]
        assert datetime.fromisoformat(served_at.replace("Z", "+00:00")).tzinfo is not None

    def test_transaction_timestamps_are_explicit(self, api):
        transaction_id = new_transaction(api)
        transaction = api.get(f"/api/transactions/{transaction_id}").json()["transaction"]
        assert transaction["created_at"]
        assert transaction["updated_at"]


# =============================================================================
# Health
# =============================================================================


class TestHealth:
    def test_health_reports_dependencies_and_experts(self, api):
        body = api.get("/health").json()
        assert body["status"] in ("healthy", "degraded")
        assert "dependencies" in body
        assert "expert_models" in body

    def test_health_carries_an_explicit_timestamp(self, api):
        assert api.get("/health").json()["timestamp"]
