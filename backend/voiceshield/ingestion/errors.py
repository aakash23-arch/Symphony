"""L1 ingestion error types and reason codes (§4, C-01..C-14).

Every failure in L1 is typed and carries a machine-readable reason code so the UI
can show the failure instead of a score (§22).
"""

from typing import Optional

from voiceshield.contracts.errors import VoiceShieldException

# --- Reason codes (C-01..C-14) -------------------------------------------------

SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"
FIXTURE_MISSING = "FIXTURE_MISSING"
NO_CAPTURE_DEVICE = "NO_CAPTURE_DEVICE"
AUDIO_FORMAT_REJECTED = "AUDIO_FORMAT_REJECTED"
AUDIO_PROTOCOL_VIOLATION = "AUDIO_PROTOCOL_VIOLATION"
FRAME_REJECTED = "FRAME_REJECTED"
FRAME_INVALID = "FRAME_INVALID"
INGEST_BACKPRESSURE = "INGEST_BACKPRESSURE"
SESSION_NOT_FOUND = "SESSION_NOT_FOUND"
SESSION_ALREADY_STARTED = "SESSION_ALREADY_STARTED"
ILLEGAL_STATE_TRANSITION = "ILLEGAL_STATE_TRANSITION"

# WebSocket close code for a protocol violation on the audio ingress (§8.1).
WS_CLOSE_AUDIO_PROTOCOL_VIOLATION = 4400


class SourceUnavailable(VoiceShieldException):
    """An AudioSource could not be opened (C-01..C-03).

    The session enters FAILED. No frames are emitted and no score is synthesised.
    """

    def __init__(
        self,
        reason: str = SOURCE_UNAVAILABLE,
        message: Optional[str] = None,
        session_id: Optional[str] = None,
    ):
        super().__init__(
            code=reason,
            message=message or f"Audio source unavailable: {reason}",
            status_code=503,
            session_id=session_id,
            retriable=True,
        )
        self.reason = reason


class AudioFormatRejected(VoiceShieldException):
    """Declared or detected audio format is not supported (C-04, C-07)."""

    def __init__(
        self,
        message: str = "Unsupported audio format",
        session_id: Optional[str] = None,
        reason: str = AUDIO_FORMAT_REJECTED,
    ):
        super().__init__(
            code=reason,
            message=message,
            status_code=415,
            session_id=session_id,
            retriable=False,
        )
        self.reason = reason


class FrameRejected(VoiceShieldException):
    """A single frame failed normalisation or validation (C-07, C-13).

    The frame is dropped and counted; the session continues, because one bad
    frame must not end a call.
    """

    def __init__(
        self,
        message: str = "Frame rejected",
        session_id: Optional[str] = None,
        reason: str = FRAME_REJECTED,
    ):
        super().__init__(
            code=reason,
            message=message,
            status_code=422,
            session_id=session_id,
            retriable=False,
        )
        self.reason = reason


class SessionError(VoiceShieldException):
    """Session lifecycle violation (C-05)."""

    def __init__(
        self,
        reason: str,
        message: str,
        status_code: int = 409,
        session_id: Optional[str] = None,
    ):
        super().__init__(
            code=reason,
            message=message,
            status_code=status_code,
            session_id=session_id,
            retriable=False,
        )
        self.reason = reason
