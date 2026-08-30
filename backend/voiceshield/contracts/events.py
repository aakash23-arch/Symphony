"""WebSocket event contracts (C-46, C-49, §8.3)."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field


class EventType(str, Enum):
    """Frozen WebSocket event types dispatched to UI clients."""
    SESSION_STARTED = "session.started"
    SESSION_STOPPED = "session.stopped"
    SESSION_ERROR = "session.error"

    FRAME_PROCESSED = "frame.processed"
    QUALITY_TELEMETRY = "quality.telemetry"

    EVIDENCE_EMITTED = "evidence.emitted"
    BELIEF_UPDATED = "belief.updated"

    RISK_UPDATED = "risk.updated"
    DECISION_EMITTED = "decision.emitted"
    STATE_TRANSITION = "state.transition"

    TIMELINE_EVENT = "timeline.event"
    EVIDENCE_RECORDED = "evidence.recorded"
    TAMPER_ALERT = "tamper.alert"


class WebSocketEventEnvelope(BaseModel):
    """Structured envelope for real-time WebSocket event broadcasts."""
    model_config = ConfigDict(extra="forbid")

    seq: int = Field(description="Monotonic sequence number per session")
    session_id: str = Field(description="Session identifier")
    event_type: EventType = Field(description="Categorical event type")
    timestamp: datetime = Field(description="UTC timestamp")
    data: Dict[str, Any] = Field(description="Typed payload corresponding to event type")
