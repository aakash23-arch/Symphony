"""Unified session WebSocket: WS /ws/sessions/{id} (Gate 10).

The dashboard socket. Carries everything one session produces - ingestion
telemetry, belief updates, risk assessments, decisions and timeline entries -
and opens with a snapshot so a client attaching mid-call is not blind until the
next slow tick.

Egress only. Audio ingress stays on WS /v1/sessions/{id}/audio: folding both
into one socket would need a mixed binary/JSON protocol and would couple audio
capture to UI backpressure, so a slow dashboard could stall the microphone.
"""

from fastapi import APIRouter, WebSocket

from .ws_stream import stream_session_events

router = APIRouter(tags=["Session Stream"])


@router.websocket("/ws/sessions/{session_id}")
async def websocket_session(websocket: WebSocket, session_id: str) -> None:
    """Stream the full event set for one session, opening with a snapshot."""
    await stream_session_events(
        websocket, session_id, include_analysis=True, send_snapshot=True
    )
