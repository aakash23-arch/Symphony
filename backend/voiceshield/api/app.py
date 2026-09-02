"""FastAPI Application Factory for VoiceShield (C-47)."""

import uuid
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from voiceshield.config import settings
from voiceshield.contracts import ErrorDetail, ErrorEnvelope, VoiceShieldException
from voiceshield.obs.logging import get_logger, setup_logging
from .routes import (
    api_detect_router,
    demo_api_router,
    demo_router,
    detect_router,
    health_router,
    inference_api_router,
    inference_router,
    root_demo_router,
    sessions_api_router,
    sessions_router,
    transactions_api_router,
    transactions_router,
    v1_detect_router,
)
from .ws_audio import router as ws_audio_router
from .ws_events import router as ws_events_router
from .ws_session import router as ws_session_router

logger = get_logger("voiceshield.api")


def _summarise_validation(exc: RequestValidationError) -> str:
    """Render a validation failure as one readable line.

    Names the offending fields rather than echoing Pydantic's nested error
    structure, which would leak internal model shapes into a client response.
    """
    parts = []
    for error in exc.errors()[:5]:
        location = ".".join(str(item) for item in error.get("loc", ()) if item != "body")
        parts.append(f"{location or 'body'}: {error.get('msg', 'invalid')}")
    if not parts:
        return "Request validation failed"
    return "Request validation failed - " + "; ".join(parts)


from contextlib import asynccontextmanager
from pathlib import Path
import numpy as np
import soundfile as sf

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Deterministic SIH Demo Startup Sequence:
    1. Preload and register L3 experts
    2. Preload & pre-warm Wav2Vec2 and WavLM neural detectors in memory
    3. Validate all 3 demo audio assets on disk
    4. Warm up pipeline JIT compilation
    5. Clean startup logging banner
    """
    from voiceshield.models.bootstrap import register_experts
    from voiceshield.pipeline.detectors import (
        Wav2Vec2DeepfakeDetector,
        WavLMSpeakerVerificationDetector,
    )
    from voiceshield.pipeline.orchestrator import default_orchestrator

    logger.info("Initializing VoiceShield SIH Demo Backend...")

    # 1. Register and warmup L3 experts
    try:
        register_experts(warmup=True)
    except Exception as exc:
        logger.error(f"L3 expert registration warning: {exc}")

    # 2. Preload neural detectors
    try:
        w2v = Wav2Vec2DeepfakeDetector.get_instance()
        w2v.ensure_loaded()
        wavlm = WavLMSpeakerVerificationDetector.get_instance()
        wavlm.ensure_loaded()
        logger.info(f"Preloaded neural detectors: Wav2Vec2 ({w2v.model_version}), WavLM ({wavlm.model_version})")
    except Exception as exc:
        logger.error(f"Neural detector preload error: {exc}")

    # 3. Validate demo audio assets
    audio_dir = Path("demo/audio")
    demo_assets = [
        "case_01_authentic_human.wav",
        "case_02_cloned_synthetic.wav",
        "case_03_adversarial_manipulated.wav",
    ]
    missing = []
    for asset in demo_assets:
        p = audio_dir / asset
        if not p.exists():
            missing.append(asset)
        else:
            try:
                info = sf.info(str(p))
                logger.info(f"Verified demo fixture '{asset}': {info.duration:.2f}s @ {info.samplerate}Hz")
            except Exception as e:
                logger.error(f"Corrupted demo fixture '{asset}': {e}")
                missing.append(asset)

    if missing:
        logger.warning(f"Demo assets missing or corrupted: {missing}")

    # 4. Pipeline Warmup
    try:
        dummy_pcm = (0.1 * np.sin(2 * np.pi * 220.0 * np.linspace(0, 0.2, 3200, endpoint=False, dtype=np.float32)))
        import io
        bio = io.BytesIO()
        sf.write(bio, dummy_pcm, 16000, format="WAV", subtype="PCM_16")
        default_orchestrator.process_audio(audio_bytes=bio.getvalue(), session_id="warmup-init")
        logger.info("Forensic inference pipeline JIT warmup completed.")
    except Exception as exc:
        logger.warning(f"Pipeline warmup note: {exc}")

    logger.info("VoiceShield SIH Demo Backend is ONLINE and READY for live judging.")
    yield
    logger.info("VoiceShield SIH Demo Backend shutting down.")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance."""
    setup_logging(
        level=settings.log_level,
        log_format=settings.log_format,
        role=settings.role.value,
    )

    app = FastAPI(
        title="VoiceShield API",
        description="Real-Time Voice Integrity & Impersonation Defense System",
        version=settings.app_version,
        lifespan=lifespan,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
    )

    # CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Middleware: Correlation ID
    @app.middleware("http")
    async def correlation_id_middleware(request: Request, call_next):
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        request.state.correlation_id = correlation_id
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response

    # Domain errors -> ErrorEnvelope (§7.1).
    #
    # Every typed failure in the system subclasses VoiceShieldException and
    # already carries the code, status and retriability the envelope needs, so
    # routes can let them propagate instead of re-wrapping each one by hand.
    @app.exception_handler(VoiceShieldException)
    async def voiceshield_exception_handler(request: Request, exc: VoiceShieldException):
        correlation_id = getattr(request.state, "correlation_id", str(uuid.uuid4()))
        envelope = ErrorEnvelope(
            error=ErrorDetail(
                code=exc.code,
                message=exc.message,
                session_id=exc.session_id or request.path_params.get("session_id"),
                correlation_id=correlation_id,
                retriable=exc.retriable,
            )
        )
        logger.warning(
            "handled domain error",
            extra={"extra_fields": {
                "code": exc.code,
                "session_id": exc.session_id,
                "correlation_id": correlation_id,
            }},
        )
        return JSONResponse(status_code=exc.status_code, content=envelope.model_dump(mode="json"))

    # Validation failures must use the same envelope as everything else.
    # FastAPI's default 422 body is {"detail": [...]}, which would make request
    # validation the one error shape a client has to special-case.
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        correlation_id = getattr(request.state, "correlation_id", str(uuid.uuid4()))
        envelope = ErrorEnvelope(
            error=ErrorDetail(
                code="VALIDATION_ERROR",
                message=_summarise_validation(exc),
                session_id=request.path_params.get("session_id"),
                correlation_id=correlation_id,
                retriable=False,
            )
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=envelope.model_dump(mode="json"),
        )

    # Global Exception Handler -> ErrorEnvelope (§7.1)
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        correlation_id = getattr(request.state, "correlation_id", str(uuid.uuid4()))
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": f"HTTP_{exc.status_code}",
                    "message": exc.detail,
                    "session_id": request.path_params.get("session_id"),
                    "correlation_id": correlation_id,
                    "retriable": exc.status_code in [502, 503, 504],
                }
            },
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        correlation_id = getattr(request.state, "correlation_id", str(uuid.uuid4()))
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred. Check server logs.",
                    "session_id": request.path_params.get("session_id"),
                    "correlation_id": correlation_id,
                    "retriable": False,
                }
            },
        )

    # Mount Route Handlers
    # Spec §12 surface.
    app.include_router(health_router)
    app.include_router(sessions_router)
    app.include_router(transactions_router)
    app.include_router(demo_router)
    app.include_router(root_demo_router)
    # Gate 10 & Minimal Production Surface
    app.include_router(sessions_api_router)
    app.include_router(transactions_api_router)
    app.include_router(demo_api_router)
    app.include_router(inference_router)
    app.include_router(inference_api_router)
    app.include_router(detect_router)
    app.include_router(v1_detect_router)
    app.include_router(api_detect_router)
    app.include_router(ws_audio_router)
    app.include_router(ws_events_router)
    app.include_router(ws_session_router)

    return app


# Default app instance for ASGI servers
app = create_app()
