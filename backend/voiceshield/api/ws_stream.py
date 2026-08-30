"""Shared session event fan-out (C-46, C-49, §8.2).

One implementation behind both event sockets, so ``/v1/sessions/{id}/events``
and ``/ws/sessions/{id}`` can never drift into disagreeing about what a session
is doing. They differ only in whether analysis events are forwarded:

* ``/v1/.../events`` is documented as L1 ingestion telemetry only, and keeps
  that contract by passing ``include_analysis=False``.
* ``/ws/sessions/{id}`` is the dashboard socket and carries everything.

Neither socket ever carries audio. The frame telemetry whitelist lives in
``ws_audio`` and is imported rather than re-derived, so a field added to
``FrameObject`` cannot silently start being broadcast.
"""

import asyncio
from typing import Optional

from fastapi import WebSocket, WebSocketDisconnect

from voiceshield.contracts.events import EventType
from voiceshield.obs.logging import get_logger

from .runtime import get_runtime

logger = get_logger("voiceshield.api.ws_stream")

#: Seconds between keepalive checks while no event is pending.
POLL_INTERVAL = 0.5

#: Events produced by the analysis layers rather than by ingestion.
ANALYSIS_EVENTS = {
    EventType.BELIEF_UPDATED,
    EventType.RISK_UPDATED,
    EventType.DECISION_EMITTED,
    EventType.TIMELINE_EVENT,
    EventType.STATE_TRANSITION,
    EventType.EVIDENCE_EMITTED,
}


def build_snapshot(session_id: str) -> dict:
    """Current session state, for a client attaching mid-call.

    Without this a dashboard that connects late shows nothing until the next
    slow tick, which on a quiet call can be seconds of blank screen during the
    moment an analyst most needs to see the state.

    Carries no audio: the belief and decision are already PCM-free by contract.
    """
    runtime = get_runtime()
    record = runtime.sessions.get(session_id)
    store = runtime.orchestrator.store
    state = store.get(session_id) if store.exists(session_id) else None

    decision = state.latest_decision if state else None
    belief = (state.latest_belief_slow or state.latest_belief_fast) if state else None

    return {
        "type": "session.snapshot",
        "session_id": session_id,
        "session_state": record.state.value,
        "source_type": record.source_type,
        "scenario_id": record.scenario_id,
        "started_at": record.started_at.isoformat() if record.started_at else None,
        "frames_published": record.frames_published,
        "frames_seen": state.frames_seen if state else 0,
        "frames_scored": state.frames_scored if state else 0,
        "frames_skipped": state.frames_skipped_backpressure if state else 0,
        # None rather than a zeroed placeholder: "no assessment yet" and
        # "assessed as low risk" must never look the same on the wire.
        "decision": decision.model_dump(mode="json") if decision else None,
        "belief": belief.model_dump(mode="json") if belief else None,
        "timeline": [entry.model_dump(mode="json") for entry in (state.timeline if state else [])][-20:],
        "analysis_degraded": bool(state.degradation_reasons()) if state else False,
        "degradation_reasons": state.degradation_reasons() if state else [],
    }


async def stream_session_events(
    websocket: WebSocket,
    session_id: str,
    *,
    include_analysis: bool,
    send_snapshot: bool = False,
) -> None:
    """Accept a socket and stream one session's events until it ends."""
    runtime = get_runtime()
    await websocket.accept()

    if not runtime.sessions.exists(session_id):
        await websocket.send_json(
            {"type": "error", "code": "SESSION_NOT_FOUND", "session_id": session_id}
        )
        await websocket.close(code=4404)
        return

    queue = runtime.events.subscribe(session_id)

    try:
        record = runtime.sessions.get(session_id)
        opening = runtime.events.build(
            session_id,
            EventType.SESSION_STARTED,
            {
                "state": record.state.value,
                "source_type": record.source_type,
                "started_at": record.started_at.isoformat() if record.started_at else None,
                "scenario_id": record.scenario_id,
            },
        )
        await websocket.send_json(opening.model_dump(mode="json"))

        if send_snapshot:
            await websocket.send_json(build_snapshot(session_id))

        while True:
            try:
                envelope = await asyncio.wait_for(queue.get(), timeout=POLL_INTERVAL)
            except asyncio.TimeoutError:
                # Nothing pending: stop once the session has reached a terminal state.
                if runtime.sessions.get(session_id).is_terminal and queue.empty():
                    break
                continue
            if not include_analysis and envelope.event_type in ANALYSIS_EVENTS:
                continue
            await websocket.send_json(envelope.model_dump(mode="json"))

        final = runtime.sessions.get(session_id)
        closing = runtime.events.build(
            session_id,
            EventType.SESSION_STOPPED,
            {
                "state": final.state.value,
                "reason": final.reason,
                "frames_published": final.frames_published,
                "frames_dropped": final.frames_dropped,
            },
        )
        await websocket.send_json(closing.model_dump(mode="json"))
        await websocket.close()

    except WebSocketDisconnect:
        logger.info(
            "session events websocket disconnected",
            extra={"extra_fields": {"session_id": session_id}},
        )
    except Exception as exc:  # noqa: BLE001 - a socket failure must not kill the session
        logger.error(
            "session events websocket error",
            extra={"extra_fields": {"session_id": session_id, "error": str(exc)}},
        )
    finally:
        runtime.events.unsubscribe(session_id, queue)
