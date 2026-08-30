"""Orchestration error types and reason codes.

Follows the L1 convention: typed failures carrying a machine-readable code, so a
route can translate them into the standard ErrorEnvelope without inspecting
exception text.
"""

from typing import Optional

from voiceshield.contracts.errors import VoiceShieldException

# --- Reason codes -------------------------------------------------------------

ANALYSIS_STATE_NOT_FOUND = "ANALYSIS_STATE_NOT_FOUND"
RISK_NOT_YET_AVAILABLE = "RISK_NOT_YET_AVAILABLE"
ANALYSIS_NOT_STARTED = "ANALYSIS_NOT_STARTED"


class AnalysisStateNotFound(VoiceShieldException):
    """No analysis state exists for the session (it never started, or was released)."""

    def __init__(self, session_id: str):
        super().__init__(
            code=ANALYSIS_STATE_NOT_FOUND,
            message=f"No analysis state for session: {session_id}",
            status_code=404,
            session_id=session_id,
            retriable=False,
        )
        self.reason = ANALYSIS_STATE_NOT_FOUND


class RiskNotYetAvailable(VoiceShieldException):
    """No action-grade assessment has been produced for this session yet.

    Deliberately an error rather than a zero-valued assessment. ``risk_score``
    is a non-optional float, so returning a "not yet" assessment would mean
    emitting 0.0 - which a dashboard renders as a reassuring green LOW for a
    call the system has said nothing about. ``retriable`` is True because the
    correct client behaviour is to keep polling, not to treat absence as a
    verdict.
    """

    def __init__(self, session_id: str, frames_seen: int = 0, frames_scored: int = 0):
        super().__init__(
            code=RISK_NOT_YET_AVAILABLE,
            message=(
                "No action-grade assessment has been produced for this session yet. "
                f"Frames seen: {frames_seen}; frames scored: {frames_scored}."
            ),
            status_code=409,
            session_id=session_id,
            retriable=True,
        )
        self.reason = RISK_NOT_YET_AVAILABLE
        self.frames_seen = frames_seen
        self.frames_scored = frames_scored
