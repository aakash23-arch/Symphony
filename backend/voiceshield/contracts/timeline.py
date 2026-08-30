"""Call timeline contracts (§34, C-49).

The timeline is the analyst-facing narrative of a call: what the system noticed,
when, and what it did about it. It is derived from the same artefacts as the
risk assessment - it never carries a signal the rest of the system does not
already hold.

Entries are appended on TRANSITIONS, not per frame. A 60 s call at the 250 ms
hop would otherwise produce 240 rows of "still the same", which is not a
narrative and would bury the three moments that mattered.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from .decision import EvidenceReference, PolicyAction, RiskBand


class TimelineEventKind(str, Enum):
    """Kinds of timeline entry."""

    SESSION_STARTED = "SESSION_STARTED"
    SESSION_STOPPED = "SESSION_STOPPED"
    SESSION_FAILED = "SESSION_FAILED"

    ANALYSIS_STARTED = "ANALYSIS_STARTED"
    BAND_CHANGED = "BAND_CHANGED"
    ACTION_CHANGED = "ACTION_CHANGED"

    LANGUAGE_DETECTED = "LANGUAGE_DETECTED"
    LANGUAGE_SWITCH = "LANGUAGE_SWITCH"
    QUALITY_DEGRADED = "QUALITY_DEGRADED"

    MODEL_UNAVAILABLE = "MODEL_UNAVAILABLE"
    ANALYSIS_DEGRADED = "ANALYSIS_DEGRADED"

    CONTEXT_INGESTED = "CONTEXT_INGESTED"
    TRANSACTION_LINKED = "TRANSACTION_LINKED"
    TRANSACTION_HELD = "TRANSACTION_HELD"
    TRANSACTION_RELEASED = "TRANSACTION_RELEASED"


class TimelineSeverity(str, Enum):
    """How prominently the UI should render an entry."""

    INFO = "INFO"
    NOTICE = "NOTICE"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class TimelineEntry(BaseModel):
    """One moment in a call's narrative.

    Carries no audio and no PCM: an entry references the evidence that produced
    it (``evidence_refs``) rather than embedding it.
    """

    model_config = ConfigDict(extra="forbid")

    seq: int = Field(description="Monotonic sequence number within the session")
    session_id: str = Field(description="Session identifier")

    kind: TimelineEventKind = Field(description="Kind of event")
    severity: TimelineSeverity = Field(default=TimelineSeverity.INFO, description="Render prominence")

    label: str = Field(description="Short UI line, e.g. 'Risk crossed critical threshold'")
    detail: Optional[str] = Field(default=None, description="Longer explanation, if any")

    #: Seconds from session start. Drives the UI's "00:15" column; None for
    #: entries that are not anchored to a point in the audio.
    t_offset_s: Optional[float] = Field(default=None, description="Seconds from session start")

    risk_band: Optional[RiskBand] = Field(default=None, description="Risk band at this moment")
    action: Optional[PolicyAction] = Field(default=None, description="Action in force at this moment")
    reason_codes: List[str] = Field(default_factory=list, description="Machine-readable reason codes")
    evidence_refs: List[EvidenceReference] = Field(
        default_factory=list, description="Evidence artefacts behind this entry"
    )

    transaction_id: Optional[str] = Field(default=None, description="Linked demo transaction, if any")

    timestamp: datetime = Field(description="Absolute UTC timestamp")


class TimelineResponse(BaseModel):
    """A page of timeline entries for one session."""

    model_config = ConfigDict(extra="forbid")

    session_id: str = Field(description="Session identifier")
    entries: List[TimelineEntry] = Field(default_factory=list, description="Ordered entries")
    #: True when the session's bounded buffer discarded older entries, so a
    #: reader knows the history is incomplete rather than assuming it is whole.
    truncated: bool = Field(default=False, description="Older entries were discarded")
    served_at: datetime = Field(description="UTC timestamp this response was built")
