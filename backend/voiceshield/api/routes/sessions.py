"""Session REST routes (C-47, §7).

Thin readers over the services. No route computes a score, a band or an action:
they read what :mod:`voiceshield.orchestration` has already concluded and shape
it for the wire. A route that recomputed anything would be a second, divergent
implementation of the decision logic.

Mounted twice (see :func:`build_router`) so the spec's ``/v1`` surface and the
requested ``/api`` surface hit the same handlers.
"""

import re
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path as FsPath
from typing import Any, List, Optional

from fastapi import APIRouter, HTTPException, Path, Query, Request, status
from pydantic import BaseModel, ConfigDict, Field

from voiceshield.contracts import (
    ClockType,
    ContextVector,
    EvidenceReference,
    ExpertStatus,
    RiskContribution,
    RiskDecision,
    TimelineEntry,
    TimelineResponse,
    TrajectoryPoint,
    VoiceBelief,
)
from voiceshield.ingestion.errors import SessionError
from voiceshield.orchestration import RiskNotYetAvailable

from ..runtime import get_runtime

#: Context may describe a call, but it may never carry a verdict. A payload
#: that tries to set a score is rejected rather than ignored, so an integrator
#: discovers immediately that scoring is not an input (§22).
FORBIDDEN_SCORING_PATTERN = re.compile(r"^(p_.*|risk.*|confidence|band|P_spoof|score)$", re.IGNORECASE)


# --- request/response schemas -------------------------------------------------


class CreateSessionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_type: str = Field(default="wav", description="Audio source type: 'wav' | 'mic' | 'ws'")
    scenario_id: Optional[str] = Field(default=None, description="Demo scenario identifier")
    caller_ref: Optional[str] = Field(default=None, description="External caller reference")


class SessionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    session_id: str
    state: str


class SessionDetailResponse(BaseModel):
    """Session status plus analysis progress counters."""

    model_config = ConfigDict(extra="forbid")
    session_id: str
    state: str
    source_type: str
    scenario_id: Optional[str] = None
    caller_ref: Optional[str] = None

    frames_published: int
    frames_dropped: int
    frames_scored: int
    frames_skipped: int

    has_assessment: bool = Field(description="True once an action-grade assessment exists")

    created_at: datetime
    started_at: Optional[datetime] = None
    stopped_at: Optional[datetime] = None
    served_at: datetime


class SessionLifecycleResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    session_id: str
    state: str
    frames_published: Optional[int] = None
    served_at: datetime


class SessionRiskResponse(BaseModel):
    """The latest action-grade assessment for a session.

    Carries the whole ``RiskDecision`` rather than a flattened score, because
    the decision is where ``score_semantics`` and ``score_label`` live: a client
    cannot render 0.78 as "78% chance of fraud" without ignoring fields it was
    handed.
    """

    model_config = ConfigDict(extra="forbid")
    session_id: str
    session_state: str

    decision: RiskDecision
    belief: Optional[VoiceBelief] = Field(
        default=None, description="Voice belief behind this assessment"
    )
    explanation: str = Field(description="Plain-text factor breakdown (attribution, not proof)")
    clock: ClockType = Field(default=ClockType.SLOW, description="Always SLOW: action-grade only")

    analysis_degraded: bool = Field(description="True when evidence was incomplete")
    degradation_reasons: List[str] = Field(
        default_factory=list, description="Why the analysis was less than fully informed"
    )

    frames_seen: int
    frames_scored: int
    frames_skipped: int

    computed_at: datetime = Field(description="When the assessment was produced")
    served_at: datetime = Field(description="When this response was built")


class ExpertEvidenceView(BaseModel):
    """One expert's contribution, as an auditor would want to see it."""

    model_config = ConfigDict(extra="forbid")
    expert_id: str
    status: ExpertStatus
    p: Optional[float] = Field(default=None, description="Probability; None unless status is OK")
    confidence: Optional[float] = None
    latency_ms: float = 0.0


class SessionEvidenceResponse(BaseModel):
    """What the system actually observed for a session.

    Explicitly NOT a hash-chained audit record. ``EvidenceRecord`` requires a
    call id and a transaction context that a voice-only session does not have,
    and a chain with no durable store behind it would offer tamper-evidence
    against nobody. The flags below say so in the payload, so no reader can
    infer an assurance property this build does not provide.
    """

    model_config = ConfigDict(extra="forbid")
    session_id: str

    record_type: str = Field(default="LIVE_ANALYSIS_SUMMARY")
    hash_chained: bool = Field(default=False, description="No hash chain backs this response")
    chain_status: str = Field(default="NOT_IMPLEMENTED")

    experts: List[ExpertEvidenceView] = Field(default_factory=list)
    model_versions: List[str] = Field(default_factory=list)
    belief_trajectory: List[TrajectoryPoint] = Field(default_factory=list)
    top_factors: List[RiskContribution] = Field(default_factory=list)
    evidence_refs: List[EvidenceReference] = Field(default_factory=list)

    audio_quality: Optional[float] = Field(default=None, description="Call-level acoustic quality")
    frames_seen: int = 0
    frames_scored: int = 0
    served_at: datetime


class ContextIngestResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    session_id: str
    context: ContextVector
    accepted_at: datetime


class ReplayFixture(str, Enum):
    """Audio fixtures the replay route will play.

    An allowlisted enum rather than a caller-supplied path. A free-text path on
    a POST route would be a directory-traversal read primitive, and the demo
    only ever needs these five.
    """

    CASE_01_AUTHENTIC_HUMAN = "case_01_authentic_human"
    CASE_02_CLONED_SYNTHETIC = "case_02_cloned_synthetic"
    CASE_03_ADVERSARIAL_MANIPULATED = "case_03_adversarial_manipulated"
    CLEAN_SPEECHLIKE = "clean_speechlike"
    NOISY_SPEECHLIKE = "noisy_speechlike"
    NARROWBAND_SPEECHLIKE = "narrowband_speechlike"
    SILENCE = "silence"
    TONE_440 = "tone_440"


#: Repository root, resolved from this file rather than the process CWD.
_REPO_ROOT = FsPath(__file__).resolve().parents[4]
_FIXTURE_DIR = _REPO_ROOT / "demo" / "audio"


class ReplayRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    fixture: ReplayFixture = Field(description="Which demo WAV fixture to play")
    speed: float = Field(default=1.0, gt=0.0, le=64.0, description="Playback rate multiplier")
    repeat: int = Field(
        default=1,
        ge=1,
        le=20,
        description="Play the fixture this many times back to back",
    )


class ReplayResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    session_id: str
    state: str
    fixture: ReplayFixture
    environment: str = Field(default="DEMO REPLAY - controlled test audio, not a live call")
    served_at: datetime


# --- helpers ------------------------------------------------------------------


def _looped_fixture(path: FsPath, repeat: int) -> FsPath:
    """Write a temp WAV holding ``repeat`` back-to-back copies of ``path``.

    The bundled fixtures are 1-2.5 s, shorter than the slow clock's own window,
    so a single pass can end a call before any action-grade assessment forms.
    The fixtures themselves are pinned by tests, so the lengthening happens here
    instead of in the generator.
    """
    import tempfile
    import wave

    with wave.open(str(path), "rb") as source:
        params = source.getparams()
        frames = source.readframes(source.getnframes())

    handle = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    handle.close()
    target = FsPath(handle.name)
    with wave.open(str(target), "wb") as out:
        out.setparams(params)
        for _ in range(repeat):
            out.writeframes(frames)
    return target


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _require_session(runtime, session_id: str) -> None:
    """404 on an unknown session, before any analysis lookup."""
    if not runtime.sessions.exists(session_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"SESSION_NOT_FOUND: Unknown session: {session_id}",
        )


def _analysis_state(runtime, session_id: str):
    """Analysis state for a session, or None if none was ever created."""
    store = runtime.orchestrator.store
    return store.get(session_id) if store.exists(session_id) else None


# --- router factory -----------------------------------------------------------


def build_router(prefix: str, suffix: str) -> APIRouter:
    """Build the session router at ``prefix``.

    ``suffix`` disambiguates operation ids between the two mounts; without it
    the generated OpenAPI document would carry duplicate operationIds and no
    longer be a valid spec.
    """
    router = APIRouter(prefix=prefix, tags=["Sessions"])

    @router.post(
        "",
        response_model=SessionResponse,
        status_code=status.HTTP_201_CREATED,
        operation_id=f"create_session{suffix}",
        summary="Create a session",
    )
    async def create_session(request: CreateSessionRequest) -> SessionResponse:
        """Create a session. Does not start audio processing."""
        runtime = get_runtime()
        record = runtime.sessions.create(
            source_type=request.source_type,
            scenario_id=request.scenario_id,
            caller_ref=request.caller_ref,
        )
        return SessionResponse(session_id=record.session_id, state=record.state.value)

    @router.get(
        "/{session_id}",
        response_model=SessionDetailResponse,
        operation_id=f"get_session{suffix}",
        summary="Get session status",
    )
    async def get_session(session_id: str = Path(min_length=1)) -> SessionDetailResponse:
        """Session lifecycle state and analysis progress."""
        runtime = get_runtime()
        _require_session(runtime, session_id)
        record = runtime.sessions.get(session_id)
        state = _analysis_state(runtime, session_id)
        return SessionDetailResponse(
            session_id=record.session_id,
            state=record.state.value,
            source_type=record.source_type,
            scenario_id=record.scenario_id,
            caller_ref=record.caller_ref,
            frames_published=record.frames_published,
            frames_dropped=record.frames_dropped,
            frames_scored=state.frames_scored if state else 0,
            frames_skipped=state.frames_skipped_backpressure if state else 0,
            has_assessment=bool(state and state.has_assessment),
            created_at=record.created_at,
            started_at=record.started_at,
            stopped_at=record.stopped_at,
            served_at=_now(),
        )

    @router.post(
        "/{session_id}/start",
        response_model=SessionLifecycleResponse,
        status_code=status.HTTP_202_ACCEPTED,
        operation_id=f"start_session{suffix}",
        summary="Mark a session ready for audio",
    )
    async def start_session(session_id: str = Path(min_length=1)) -> SessionLifecycleResponse:
        """Mark the session ready and spawn its analysis worker.

        The audio source attaches over the audio WebSocket; a duplicate start is
        a 409 and never silently restarts an in-flight session.
        """
        runtime = get_runtime()
        _require_session(runtime, session_id)
        try:
            record = runtime.sessions.start(session_id)
        except SessionError as exc:
            raise HTTPException(status_code=exc.status_code, detail=f"{exc.code}: {exc.message}") from exc
        await runtime.orchestrator.start(session_id)
        return SessionLifecycleResponse(
            session_id=record.session_id, state=record.state.value, served_at=_now()
        )

    @router.post(
        "/{session_id}/stop",
        response_model=SessionLifecycleResponse,
        status_code=status.HTTP_202_ACCEPTED,
        operation_id=f"stop_session{suffix}",
        summary="Stop a session",
    )
    async def stop_session(session_id: str = Path(min_length=1)) -> SessionLifecycleResponse:
        """Drain and stop. No final score is synthesised for the last frames."""
        runtime = get_runtime()
        _require_session(runtime, session_id)
        await runtime.orchestrator.drain(session_id)
        record = runtime.sessions.stop(session_id)
        return SessionLifecycleResponse(
            session_id=record.session_id,
            state=record.state.value,
            frames_published=record.frames_published,
            served_at=_now(),
        )

    @router.get(
        "/{session_id}/risk",
        response_model=SessionRiskResponse,
        operation_id=f"get_session_risk{suffix}",
        summary="Get the latest action-grade risk assessment",
    )
    async def get_session_risk(session_id: str = Path(min_length=1)) -> SessionRiskResponse:
        """Latest assessment, or 409 if none has been produced yet.

        The 409 is deliberate. ``risk_score`` is a non-optional float, so a
        "nothing yet" body would have to carry 0.0 - which a dashboard renders
        as a reassuring LOW for a call the system has said nothing about.
        """
        runtime = get_runtime()
        _require_session(runtime, session_id)
        record = runtime.sessions.get(session_id)
        state = _analysis_state(runtime, session_id)

        if state is None or state.latest_decision is None:
            # Propagates to the VoiceShieldException handler as a structured
            # 409 with retriable=true: the client should poll, not conclude.
            raise RiskNotYetAvailable(
                session_id,
                frames_seen=state.frames_seen if state else 0,
                frames_scored=state.frames_scored if state else 0,
            )

        decision = state.latest_decision
        return SessionRiskResponse(
            session_id=session_id,
            session_state=record.state.value,
            decision=decision,
            belief=state.latest_belief_slow or state.latest_belief_fast,
            explanation=runtime.orchestrator.risk.explain(decision),
            clock=ClockType.SLOW,
            analysis_degraded=bool(state.degradation_reasons()),
            degradation_reasons=state.degradation_reasons(),
            frames_seen=state.frames_seen,
            frames_scored=state.frames_scored,
            frames_skipped=state.frames_skipped_backpressure,
            computed_at=decision.timestamp,
            served_at=_now(),
        )

    @router.get(
        "/{session_id}/evidence",
        response_model=SessionEvidenceResponse,
        operation_id=f"get_session_evidence{suffix}",
        summary="Get the evidence behind a session's assessment",
    )
    async def get_session_evidence(session_id: str = Path(min_length=1)) -> SessionEvidenceResponse:
        """Per-expert evidence, belief trajectory and factor attribution.

        Answers before an assessment exists: an empty expert list with the
        counters at zero is a truthful statement about a session that has not
        been analysed yet, unlike a risk score, which cannot be empty.
        """
        runtime = get_runtime()
        _require_session(runtime, session_id)
        state = _analysis_state(runtime, session_id)

        if state is None:
            return SessionEvidenceResponse(session_id=session_id, served_at=_now())

        experts: List[ExpertEvidenceView] = []
        evidence = state.latest_evidence
        if evidence is not None:
            for expert_id, expert_status in sorted(evidence.expert_statuses.items()):
                experts.append(
                    ExpertEvidenceView(
                        expert_id=expert_id,
                        status=expert_status,
                        # Mirrors the assembler: a non-OK expert has no
                        # probability, and None must not be shown as 0.0.
                        p=_probability_for(evidence, expert_id),
                        confidence=evidence.expert_confidences.get(expert_id),
                        latency_ms=evidence.inference_latency_ms.get(expert_id, 0.0),
                    )
                )

        belief = state.latest_belief_slow or state.latest_belief_fast
        decision = state.latest_decision
        return SessionEvidenceResponse(
            session_id=session_id,
            experts=experts,
            model_versions=list(evidence.model_versions) if evidence else [],
            belief_trajectory=list(belief.trajectory) if belief else [],
            top_factors=list(decision.top_factors) if decision else [],
            evidence_refs=list(decision.evidence_refs) if decision else [],
            audio_quality=belief.q_call if belief else None,
            frames_seen=state.frames_seen,
            frames_scored=state.frames_scored,
            served_at=_now(),
        )

    @router.get(
        "/{session_id}/timeline",
        response_model=TimelineResponse,
        operation_id=f"get_session_timeline{suffix}",
        summary="Get the call timeline",
    )
    async def get_session_timeline(
        session_id: str = Path(min_length=1),
        since_seq: Optional[int] = Query(default=None, ge=0, description="Return entries after this seq"),
        limit: int = Query(default=100, ge=1, le=500, description="Maximum entries to return"),
    ) -> TimelineResponse:
        """Narrative of what the system noticed, when, and what it did."""
        runtime = get_runtime()
        _require_session(runtime, session_id)
        state = _analysis_state(runtime, session_id)

        entries: List[TimelineEntry] = list(state.timeline) if state else []
        if since_seq is not None:
            entries = [entry for entry in entries if entry.seq > since_seq]
        return TimelineResponse(
            session_id=session_id,
            entries=entries[:limit],
            truncated=bool(state and state.timeline_truncated),
            served_at=_now(),
        )

    @router.post(
        "/{session_id}/replay",
        response_model=ReplayResponse,
        status_code=status.HTTP_202_ACCEPTED,
        operation_id=f"start_replay{suffix}",
        summary="Play a demo audio fixture into a session",
    )
    async def start_replay(session_id: str, request: ReplayRequest) -> ReplayResponse:
        """Stream a bundled WAV fixture through the real L1 pipeline.

        The route selects the fixture and starts the session. It computes no
        score and sets no band: the pipeline produces the result (§36). A
        scenario that could set its own risk score would make the demo a
        puppet show rather than a demonstration.
        """
        runtime = get_runtime()
        _require_session(runtime, session_id)

        path = _FIXTURE_DIR / f"{request.fixture.value}.wav"
        if not path.is_file():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    f"FIXTURE_MISSING: demo fixture {request.fixture.value}.wav is not "
                    "present; run scripts/make_demo_fixtures.py"
                ),
            )

        record = runtime.sessions.get(session_id)
        if record.is_terminal:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"SESSION_TERMINAL: session {session_id} has already ended",
            )

        await runtime.orchestrator.start(session_id)

        from voiceshield.demo.replay import ReplaySimulator

        # ``repeat`` concatenates the fixture into a temporary WAV rather than
        # replaying it N times: L1IngestionPipeline.run() stops the session when
        # its source is exhausted, so a second pass would find a terminated
        # session and emit nothing. Concatenating keeps it one continuous call.
        source_path = path if request.repeat == 1 else _looped_fixture(path, request.repeat)

        async def _drive() -> None:
            """Play the fixture, then drain analysis and close the session."""
            try:
                simulator = ReplaySimulator(
                    source_path,
                    pipeline=runtime.pipeline,
                    speed=request.speed,
                    session_id=session_id,
                )
                await simulator.run(on_frame=runtime.make_frame_sink(session_id))
            except Exception:
                # The session manager already marks FAILED; the socket reports
                # it. Never synthesise a final score to paper over the gap.
                pass
            finally:
                await runtime.orchestrator.drain(session_id)
                if source_path != path:
                    source_path.unlink(missing_ok=True)

        # Detached: the client watches progress over the session socket rather
        # than holding an HTTP request open for the length of the call. Spawned
        # through the runtime so a strong reference survives - a bare
        # create_task can be garbage collected mid-replay.
        runtime.spawn(_drive())

        return ReplayResponse(
            session_id=session_id,
            state=record.state.value,
            fixture=request.fixture,
            served_at=_now(),
        )

    @router.post(
        "/{session_id}/context",
        response_model=ContextIngestResponse,
        status_code=status.HTTP_202_ACCEPTED,
        operation_id=f"post_session_context{suffix}",
        summary="Ingest call context",
    )
    async def post_session_context(session_id: str, request: Request) -> ContextIngestResponse:
        """Ingest context. Rejects any payload carrying a scoring field."""
        runtime = get_runtime()
        _require_session(runtime, session_id)

        try:
            body = await request.json()
        except Exception as exc:  # noqa: BLE001 - malformed JSON is a client error
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="MALFORMED_JSON: Request body is not valid JSON",
            ) from exc

        if not isinstance(body, dict):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="INVALID_CONTEXT: Context payload must be a JSON object",
            )

        for key in _walk_keys(body):
            if FORBIDDEN_SCORING_PATTERN.match(key):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"SCORING_FIELD_REJECTED: Context cannot accept score key '{key}'",
                )

        context = runtime.orchestrator.ingest_context(session_id, body)
        return ContextIngestResponse(
            session_id=session_id, context=context, accepted_at=_now()
        )

    return router


def _probability_for(evidence, expert_id: str) -> Optional[float]:
    """Read one expert's probability off the evidence vector."""
    field = {
        "E1": "p_spec", "E2": "p_raw", "E3": "p_ssl",
        "E4": "p_spk", "E5": "p_beh", "E6": "p_rep",
    }.get(expert_id)
    return getattr(evidence, field, None) if field else None


def _walk_keys(payload: Any, depth: int = 0):
    """Yield every key in a nested payload, so a score cannot hide in a subobject."""
    if depth > 6 or not isinstance(payload, dict):
        return
    for key, value in payload.items():
        yield key
        if isinstance(value, dict):
            yield from _walk_keys(value, depth + 1)


#: Spec §12 surface, and the surface the existing tests address.
router = build_router("/v1/sessions", "_v1")

#: The surface requested in Gate 10. Same handlers, different mount.
api_router = build_router("/api/sessions", "_api")
