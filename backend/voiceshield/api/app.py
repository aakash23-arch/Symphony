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
    demo_api_router,
    demo_router,
    health_router,
    sessions_api_router,
    sessions_router,
    transactions_api_router,
    transactions_router,
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

    @app.on_event("startup")
    async def register_l3_experts() -> None:
        """Register the L3 experts and log which ones are actually live (C-27).

        Startup must never proceed silently as if all six experts were available.
        A missing model marks that expert unavailable and is named in the log;
        it never prevents the API from starting.
        """
        from voiceshield.models.bootstrap import register_experts

        try:
            register_experts()
        except Exception as exc:  # pragma: no cover - defensive
            logger.error(
                "expert registration failed; L3 will report unavailable",
                extra={"extra_fields": {"error_type": type(exc).__name__, "detail": str(exc)[:200]}},
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
    # Gate 10 surface. Same handlers, so the two can never diverge.
    app.include_router(sessions_api_router)
    app.include_router(transactions_api_router)
    app.include_router(demo_api_router)
    app.include_router(ws_audio_router)
    app.include_router(ws_events_router)
    app.include_router(ws_session_router)

    return app


# Default app instance for ASGI servers
app = create_app()
