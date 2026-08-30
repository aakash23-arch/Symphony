"""Tests for the demo replay route and the manual-hold timeline entry.

The replay route is what makes the dashboard observable: without an audio
source a session never produces a frame, so risk stays at 409 forever. These
tests pin the two properties that matter most about it — that it plays only
allowlisted fixtures, and that it feeds the SAME frame sink as the audio
socket, so language and quality telemetry are not silently lost.
"""

import pytest
from fastapi import status

from voiceshield.contracts import TimelineEventKind


@pytest.fixture
def api(client):
    """Test client with a clean runtime."""
    from voiceshield.api.runtime import get_runtime

    get_runtime().reset()
    return client


def new_session(api) -> str:
    response = api.post("/api/sessions", json={"source_type": "wav"})
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()["session_id"]


class TestReplayRoute:
    def test_a_known_fixture_is_accepted(self, api):
        session_id = new_session(api)
        api.post(f"/api/sessions/{session_id}/start")
        response = api.post(
            f"/api/sessions/{session_id}/replay",
            json={"fixture": "clean_speechlike", "speed": 64.0},
        )
        assert response.status_code == status.HTTP_202_ACCEPTED
        assert response.json()["fixture"] == "clean_speechlike"

    def test_the_response_is_labelled_as_demo_audio(self, api):
        """A screenshot of this must not read as a claim about a real call."""
        session_id = new_session(api)
        api.post(f"/api/sessions/{session_id}/start")
        body = api.post(
            f"/api/sessions/{session_id}/replay", json={"fixture": "silence"}
        ).json()
        assert "DEMO" in body["environment"].upper()
        assert "not a live call" in body["environment"].lower()

    @pytest.mark.parametrize(
        "fixture",
        ["clean_speechlike", "noisy_speechlike", "narrowband_speechlike", "silence", "tone_440"],
    )
    def test_every_allowlisted_fixture_exists_on_disk(self, api, fixture):
        """A fixture in the enum but missing from disk would 503 at demo time."""
        session_id = new_session(api)
        api.post(f"/api/sessions/{session_id}/start")
        response = api.post(f"/api/sessions/{session_id}/replay", json={"fixture": fixture})
        assert response.status_code == status.HTTP_202_ACCEPTED

    def test_an_unknown_fixture_is_rejected(self, api):
        session_id = new_session(api)
        response = api.post(
            f"/api/sessions/{session_id}/replay", json={"fixture": "not_a_fixture"}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_a_path_cannot_be_smuggled_in_as_a_fixture(self, api):
        """The allowlist is what stops this route being a file-read primitive."""
        session_id = new_session(api)
        for attempt in ("../../etc/passwd", "..\\..\\windows\\win.ini", "/etc/hosts"):
            response = api.post(
                f"/api/sessions/{session_id}/replay", json={"fixture": attempt}
            )
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_replay_on_an_unknown_session_is_404(self, api):
        response = api.post("/api/sessions/ghost/replay", json={"fixture": "silence"})
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_a_non_positive_speed_is_rejected(self, api):
        session_id = new_session(api)
        response = api.post(
            f"/api/sessions/{session_id}/replay", json={"fixture": "silence", "speed": 0}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_the_route_is_on_both_mounts(self, api):
        spec = api.get("/openapi.json").json()
        assert "/api/sessions/{session_id}/replay" in spec["paths"]
        assert "/v1/sessions/{session_id}/replay" in spec["paths"]

    def test_the_route_accepts_no_scoring_input(self, api):
        """The scenario may pick the audio; it may never pick the verdict."""
        session_id = new_session(api)
        response = api.post(
            f"/api/sessions/{session_id}/replay",
            json={"fixture": "silence", "risk_score": 0.9},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestSharedFrameSink:
    def test_both_audio_paths_use_one_frame_sink(self):
        """A second, divergent sink would silently drop frame telemetry.

        The Call panel's language and per-frame quality come only from
        FRAME_PROCESSED. If replay built its own callback and forgot to publish
        it, replayed sessions would show a permanently blank language field.
        """
        import inspect

        from voiceshield.api import routes, ws_audio

        audio_src = inspect.getsource(ws_audio)
        sessions_src = inspect.getsource(routes.sessions)
        assert "make_frame_sink" in audio_src
        assert "make_frame_sink" in sessions_src

    def test_the_telemetry_whitelist_carries_no_audio(self):
        """P2: a field added to FrameObject must not start being broadcast."""
        from voiceshield.api.runtime import frame_telemetry

        class _Frame:
            frame_id = 1
            t_start = 0.0
            t_end = 0.25
            is_speech = True
            q_t = 0.9
            packet_loss = 0.0
            bandwidth = 4000.0
            lang_t = "en"
            source_type = "wav"
            pcm = [0.1] * 4000

        telemetry = frame_telemetry(_Frame())
        assert "pcm" not in telemetry
        assert set(telemetry) == {
            "frame_id", "t_start", "t_end", "is_speech", "q_t",
            "packet_loss", "bandwidth", "lang_t", "source_type",
        }


class TestManualHoldTimeline:
    def _linked(self, api):
        session_id = new_session(api)
        api.post(f"/api/sessions/{session_id}/start")
        transaction_id = api.post(
            "/api/transactions",
            json={
                "caller_identity": "alice",
                "amount": "5000.00",
                "beneficiary": "acme",
                "session_id": session_id,
            },
        ).json()["transaction"]["transaction_id"]
        return session_id, transaction_id

    def test_a_manual_hold_appears_on_the_call_timeline(self, api):
        """Otherwise a hand-held transaction leaves no trace in the narrative."""
        session_id, transaction_id = self._linked(api)
        api.post(
            f"/api/transactions/{transaction_id}/hold",
            json={"reason": "operator judgement", "session_id": session_id},
        )
        kinds = [
            entry["kind"]
            for entry in api.get(f"/api/sessions/{session_id}/timeline").json()["entries"]
        ]
        assert TimelineEventKind.TRANSACTION_HELD.value in kinds

    def test_a_manual_release_appears_too(self, api):
        session_id, transaction_id = self._linked(api)
        api.post(
            f"/api/transactions/{transaction_id}/hold",
            json={"reason": "check", "session_id": session_id},
        )
        api.post(
            f"/api/transactions/{transaction_id}/release",
            json={"verification_reference": "CALLBACK-1", "session_id": session_id},
        )
        entries = api.get(f"/api/sessions/{session_id}/timeline").json()["entries"]
        released = [e for e in entries if e["kind"] == TimelineEventKind.TRANSACTION_RELEASED.value]
        assert released
        assert "CALLBACK-1" in (released[-1]["detail"] or "")

    def test_the_entry_names_the_transaction(self, api):
        session_id, transaction_id = self._linked(api)
        api.post(
            f"/api/transactions/{transaction_id}/hold",
            json={"reason": "check", "session_id": session_id},
        )
        entries = api.get(f"/api/sessions/{session_id}/timeline").json()["entries"]
        held = [e for e in entries if e["kind"] == TimelineEventKind.TRANSACTION_HELD.value]
        assert held[-1]["transaction_id"] == transaction_id

    def test_a_hold_without_a_session_still_succeeds(self, api):
        """A transaction acted on outside any call has nowhere to write."""
        transaction_id = api.post(
            "/api/transactions",
            json={"caller_identity": "bob", "amount": "10.00", "beneficiary": "x"},
        ).json()["transaction"]["transaction_id"]
        response = api.post(f"/api/transactions/{transaction_id}/hold", json={"reason": "r"})
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["transaction"]["state"] == "HELD"

    def test_an_unknown_session_id_does_not_break_the_mutation(self, api):
        """Timeline recording is a side effect; it must never fail the action."""
        transaction_id = api.post(
            "/api/transactions",
            json={"caller_identity": "bob", "amount": "10.00", "beneficiary": "x"},
        ).json()["transaction"]["transaction_id"]
        response = api.post(
            f"/api/transactions/{transaction_id}/hold",
            json={"reason": "r", "session_id": "never-existed"},
        )
        assert response.status_code == status.HTTP_200_OK
