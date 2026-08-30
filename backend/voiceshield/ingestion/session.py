"""Session lifecycle management (C-05).

Creates, starts and stops sessions; owns session lifecycle state; binds exactly
one AudioSource per session; allocates session_id.

It computes nothing about audio content and decides no risk. When a source dies
the session goes to FAILED and a terminal event is published -- no final score is
ever synthesised.

This build keeps session state in memory. Redis/SQLite persistence is a
follow-up and is deliberately not faked here.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional

from .errors import (
    ILLEGAL_STATE_TRANSITION,
    SESSION_ALREADY_STARTED,
    SESSION_NOT_FOUND,
    SessionError,
)
from .sources import AudioSource


class SessionState(str, Enum):
    """Legal session lifecycle states."""

    CREATED = "CREATED"
    RUNNING = "RUNNING"
    DEGRADED = "DEGRADED"
    STOPPING = "STOPPING"
    STOPPED = "STOPPED"
    FAILED = "FAILED"
    #: Set at startup for sessions found non-terminal after a restart (§17.3).
    #: They are never resumed and no score is reconstructed for them.
    INTERRUPTED = "INTERRUPTED"


TERMINAL_STATES = {SessionState.STOPPED, SessionState.FAILED, SessionState.INTERRUPTED}

LEGAL_TRANSITIONS: Dict[SessionState, set] = {
    SessionState.CREATED: {SessionState.RUNNING, SessionState.FAILED, SessionState.STOPPED,
                           SessionState.INTERRUPTED},
    SessionState.RUNNING: {SessionState.DEGRADED, SessionState.STOPPING, SessionState.STOPPED,
                           SessionState.FAILED, SessionState.INTERRUPTED},
    SessionState.DEGRADED: {SessionState.RUNNING, SessionState.STOPPING, SessionState.STOPPED,
                            SessionState.FAILED, SessionState.INTERRUPTED},
    SessionState.STOPPING: {SessionState.STOPPED, SessionState.FAILED},
    SessionState.STOPPED: set(),
    SessionState.FAILED: set(),
    SessionState.INTERRUPTED: set(),
}


@dataclass
class SessionRecord:
    """In-memory record of one session."""

    session_id: str
    source_type: str
    state: SessionState = SessionState.CREATED
    scenario_id: Optional[str] = None
    caller_ref: Optional[str] = None
    correlation_id: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    stopped_at: Optional[datetime] = None
    reason: Optional[str] = None
    source: Optional[AudioSource] = None

    #: Monotonic counters owned by the session (§6.1, §8.2).
    frame_counter: int = 0
    seq_counter: int = 0

    frames_published: int = 0
    frames_dropped: int = 0

    def next_frame_id(self) -> int:
        value = self.frame_counter
        self.frame_counter += 1
        return value

    def next_seq(self) -> int:
        self.seq_counter += 1
        return self.seq_counter

    @property
    def is_terminal(self) -> bool:
        return self.state in TERMINAL_STATES


class SessionManager:
    """Own the session lifecycle and the one-source-per-session binding."""

    def __init__(self) -> None:
        self._sessions: Dict[str, SessionRecord] = {}

    # -- lifecycle ------------------------------------------------------------

    def create(
        self,
        source_type: str = "wav",
        scenario_id: Optional[str] = None,
        caller_ref: Optional[str] = None,
        correlation_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> SessionRecord:
        sid = session_id or uuid.uuid4().hex
        if sid in self._sessions:
            raise SessionError(
                SESSION_ALREADY_STARTED, f"Session already exists: {sid}", session_id=sid
            )
        record = SessionRecord(
            session_id=sid,
            source_type=source_type,
            scenario_id=scenario_id,
            caller_ref=caller_ref,
            correlation_id=correlation_id or uuid.uuid4().hex,
        )
        self._sessions[sid] = record
        return record

    def get(self, session_id: str) -> SessionRecord:
        record = self._sessions.get(session_id)
        if record is None:
            raise SessionError(
                SESSION_NOT_FOUND,
                f"Unknown session: {session_id}",
                status_code=404,
                session_id=session_id,
            )
        return record

    def exists(self, session_id: str) -> bool:
        return session_id in self._sessions

    def bind_source(self, session_id: str, source: AudioSource) -> SessionRecord:
        """Bind exactly one AudioSource to the session."""
        record = self.get(session_id)
        if record.source is not None:
            raise SessionError(
                SESSION_ALREADY_STARTED,
                f"Session {session_id} already has a bound source",
                session_id=session_id,
            )
        record.source = source
        record.source_type = source.source_type
        return record

    def start(self, session_id: str) -> SessionRecord:
        record = self.get(session_id)
        if record.state is SessionState.RUNNING:
            raise SessionError(
                SESSION_ALREADY_STARTED,
                f"Session {session_id} is already running",
                session_id=session_id,
            )
        self.transition(session_id, SessionState.RUNNING)
        record.started_at = datetime.now(timezone.utc)
        return record

    def stop(self, session_id: str) -> SessionRecord:
        record = self.get(session_id)
        if record.is_terminal:
            return record
        if record.state is not SessionState.STOPPING:
            self.transition(session_id, SessionState.STOPPING)
        self.transition(session_id, SessionState.STOPPED)
        record.stopped_at = datetime.now(timezone.utc)
        return record

    def fail(self, session_id: str, reason: str) -> SessionRecord:
        """Terminal failure. The UI shows the failure; it does not show a score."""
        record = self.get(session_id)
        if record.is_terminal:
            return record
        self.transition(session_id, SessionState.FAILED)
        record.reason = reason
        record.stopped_at = datetime.now(timezone.utc)
        return record

    def degrade(self, session_id: str, reason: str) -> SessionRecord:
        """Mark degraded without ending the session."""
        record = self.get(session_id)
        if record.state is SessionState.RUNNING:
            self.transition(session_id, SessionState.DEGRADED)
        record.reason = reason
        return record

    def transition(self, session_id: str, target: SessionState) -> SessionRecord:
        record = self.get(session_id)
        if target not in LEGAL_TRANSITIONS[record.state]:
            raise SessionError(
                ILLEGAL_STATE_TRANSITION,
                f"Illegal transition {record.state.value} -> {target.value}",
                session_id=session_id,
            )
        record.state = target
        return record

    def mark_interrupted(self) -> List[SessionRecord]:
        """Mark every non-terminal session INTERRUPTED (§17.3). None are resumed."""
        interrupted: List[SessionRecord] = []
        for record in self._sessions.values():
            if not record.is_terminal:
                record.state = SessionState.INTERRUPTED
                record.reason = "PROCESS_RESTART"
                interrupted.append(record)
        return interrupted

    def list_sessions(self) -> List[SessionRecord]:
        return list(self._sessions.values())

    def remove(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)
