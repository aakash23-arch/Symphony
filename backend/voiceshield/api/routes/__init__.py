"""API route endpoints.

Each module exposes ``router`` (the spec-aligned /v1 surface) and ``api_router``
(the /api surface requested in Gate 10). Both are built from the same handlers,
so the two prefixes can never drift apart in behaviour.
"""

from .demo import api_router as demo_api_router
from .demo import root_demo_router
from .demo import router as demo_router
from .health import router as health_router
from .inference import api_detect_router
from .inference import api_router as inference_api_router
from .inference import detect_router
from .inference import router as inference_router
from .inference import v1_detect_router
from .sessions import api_router as sessions_api_router
from .sessions import router as sessions_router
from .transactions import api_router as transactions_api_router
from .transactions import router as transactions_router

__all__ = [
    "health_router",
    "sessions_router",
    "sessions_api_router",
    "transactions_router",
    "transactions_api_router",
    "demo_router",
    "demo_api_router",
    "root_demo_router",
    "inference_router",
    "inference_api_router",
    "detect_router",
    "v1_detect_router",
    "api_detect_router",
]

