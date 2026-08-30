"""WebSocket audio ingress: WS /v1/sessions/{id}/audio (C-04, C-48, §8.1).

Client -> server: one JSON header {type:"audio.header", sample_rate, channels,
encoding} followed by binary PCM frames.
Server -> client: {type:"audio.ack", frames_received, dropped} and error frames
only.

Any other client message type closes the socket with 4400
AUDIO_PROTOCOL_VIOLATION. The client-declared sample rate is validated, never
trusted. No JSON control message may alter scoring, because this endpoint does
no scoring at all.
"""

import asyncio
import json
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from voiceshield.ingestion.errors import (
    AUDIO_PROTOCOL_VIOLATION,
    WS_CLOSE_AUDIO_PROTOCOL_VIOLATION,
    AudioFormatRejected,
)
from voiceshield.ingestion.pipeline import L1IngestionPipeline
from voiceshield.ingestion.session import SessionState
from voiceshield.ingestion.sources import WebSocketSource
from voiceshield.obs.logging import get_logger

from .runtime import get_runtime

logger = get_logger("voiceshield.api.ws_audio")

router = APIRouter(tags=["Audio Ingress"])

#: Send an ack at most every N accepted chunks, to avoid chattiness.
ACK_INTERVAL = 10


@router.websocket("/v1/sessions/{session_id}/audio")
async def websocket_audio(websocket: WebSocket, session_id: str) -> None:
    """Accept browser-pushed PCM and drive the L1 pipeline for this session."""
    runtime = get_runtime()
    await websocket.accept()

    # An unknown session is a client error, not a protocol violation.
    if not runtime.sessions.exists(session_id):
        await websocket.send_json(
            {"type": "error", "code": "SESSION_NOT_FOUND", "session_id": session_id}
        )
        await websocket.close(code=4404)
        return

    source: Optional[WebSocketSource] = None
    pump: Optional[asyncio.Task] = None
    frames_received = 0

    try:
        raw_header = await websocket.receive()
        header = _extract_header(raw_header)
        sample_rate, channels, encoding = WebSocketSource.validate_header(header)
    except AudioFormatRejected as exc:
        runtime.sessions.degrade(session_id, exc.code)
        await _close_violation(websocket, exc.message)
        return
    except WebSocketDisconnect:
        _finalise(runtime, session_id)
        return

    source = WebSocketSource(
        sample_rate=sample_rate, channels=channels, encoding=encoding
    )
    pipeline: L1IngestionPipeline = runtime.pipeline

    try:
        await source.open()
        await runtime.orchestrator.start(session_id)
        pump = asyncio.create_task(
            pipeline.run(session_id, source, on_frame=runtime.make_frame_sink(session_id))
        )

        while True:
            message = await websocket.receive()
            if message.get("type") == "websocket.disconnect":
                raise WebSocketDisconnect(message.get("code", 1000))

            payload = message.get("bytes")
            if payload is None:
                # Text mid-stream is a protocol violation (§8.1).
                runtime.sessions.degrade(session_id, AUDIO_PROTOCOL_VIOLATION)
                await _close_violation(
                    websocket, "Only binary PCM frames are accepted after the header"
                )
                return

            accepted = source.push(payload)
            frames_received += 1
            if not accepted:
                runtime.sessions.degrade(session_id, "INGEST_BACKPRESSURE")

            if frames_received % ACK_INTERVAL == 0:
                await websocket.send_json(
                    {
                        "type": "audio.ack",
                        "frames_received": frames_received,
                        "dropped": source.dropped_chunks,
                    }
                )

    except WebSocketDisconnect:
        # A disconnect ends the stream cleanly; it is not a failure.
        logger.info(
            "Audio websocket disconnected",
            extra={"extra_fields": {"session_id": session_id,
                                    "frames_received": frames_received}},
        )
    except Exception as exc:
        logger.error(
            "Audio websocket error",
            extra={"extra_fields": {"session_id": session_id, "error": str(exc)}},
        )
        runtime.sessions.degrade(session_id, "AUDIO_STREAM_ERROR")
    finally:
        if source is not None:
            source.signal_end()
        if pump is not None:
            try:
                await asyncio.wait_for(pump, timeout=5.0)
            except (asyncio.TimeoutError, asyncio.CancelledError, Exception):
                if not pump.done():
                    pump.cancel()
        # Let in-flight scoring finish, then release buffered audio. A drain
        # that times out leaves the last frames unscored rather than
        # synthesising a final score for them.
        await runtime.orchestrator.drain(session_id)
        _finalise(runtime, session_id)


def _extract_header(message: dict) -> dict:
    """Pull the JSON header out of the first websocket message."""
    if message.get("type") == "websocket.disconnect":
        raise WebSocketDisconnect(message.get("code", 1000))
    text = message.get("text")
    if text is None:
        raise AudioFormatRejected("First message must be a JSON audio.header frame")
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError) as exc:
        raise AudioFormatRejected(f"Malformed audio header: {exc}") from exc


async def _close_violation(websocket: WebSocket, reason: str) -> None:
    try:
        await websocket.send_json(
            {"type": "error", "code": AUDIO_PROTOCOL_VIOLATION, "message": reason}
        )
        await websocket.close(code=WS_CLOSE_AUDIO_PROTOCOL_VIOLATION, reason=reason)
    except Exception:
        pass


def _finalise(runtime, session_id: str) -> None:
    """Bring the session to a terminal state without synthesising any score."""
    try:
        record = runtime.sessions.get(session_id)
    except Exception:
        return
    if not record.is_terminal and record.state is not SessionState.CREATED:
        runtime.sessions.stop(session_id)

