"""WebSocket event egress: WS /v1/sessions/{id}/events (C-46, C-49, §8.2).

Pushes WebSocketEventEnvelopes with a monotonic per-session seq so the client can
detect and display gaps.

This socket is documented as L1 ingestion telemetry only: session lifecycle,
per-frame descriptors and quality. Analysis events (belief, risk, decision) are
filtered out here and carried on WS /ws/sessions/{id} instead, so an existing
integrator's event stream does not change shape underneath them.
"""

from fastapi import APIRouter, WebSocket

from .ws_stream import stream_session_events

router = APIRouter(tags=["Events"])


@router.websocket("/v1/sessions/{session_id}/events")
async def websocket_events(websocket: WebSocket, session_id: str) -> None:
    """Stream L1 ingestion events for one session until the client disconnects."""
    await stream_session_events(websocket, session_id, include_analysis=False)
