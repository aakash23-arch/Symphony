"""Shared helpers for expert implementations (C-19..C-25).

Kept separate from ``base.py`` because ``Expert`` is a frozen-ish published
interface; this module holds the mechanics the concrete E1..E6 share.

NO ML LIBRARY IMPORTS. Experts orchestrate and validate; adapters do inference.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, List, Optional, Sequence

import numpy as np

from voiceshield.contracts import ExpertStatus
from voiceshield.obs.logging import get_logger
from voiceshield.signal_processing import FeatureBundle

from . import errors as err
from .interfaces import ModelInferenceResult

logger = get_logger("voiceshield.models.expert")


class Timer:
    """Wall-clock inference timer in milliseconds."""

    def __init__(self) -> None:
        self._start = time.perf_counter()

    @property
    def elapsed_ms(self) -> float:
        return (time.perf_counter() - self._start) * 1000.0


def validate_bundle(bundle: Any) -> Optional[str]:
    """Return a reason code if the bundle is unusable, else None.

    Malformed input must produce an abstention, never an exception escaping into
    the pipeline (C-19).
    """
    if bundle is None:
        return err.MALFORMED_INPUT
    if not isinstance(bundle, FeatureBundle):
        return err.MALFORMED_INPUT
    return None


def extract_pcm(bundle: FeatureBundle) -> tuple[Optional[np.ndarray], Optional[str]]:
    """Pull raw PCM out of a bundle as a finite float32 array.

    Returns ``(pcm, None)`` or ``(None, reason_code)``. ``raw_pcm`` is None unless
    the bundle was built with ``include_raw=True``, which is a legitimate
    abstention cause rather than an error.
    """
    raw = bundle.raw_pcm
    if raw is None:
        return None, err.MISSING_RAW_PCM

    try:
        pcm = np.asarray(raw, dtype=np.float32)
    except (TypeError, ValueError):
        return None, err.MALFORMED_INPUT

    if pcm.ndim != 1 or pcm.size == 0:
        return None, err.MALFORMED_INPUT
    if not np.all(np.isfinite(pcm)):
        # NaN/Inf would propagate silently through a forward pass and produce a
        # nan probability that looks like a real score.
        return None, err.NON_FINITE_INPUT

    return pcm, None


def abstain(
    *,
    model_id: str,
    error_code: str,
    error_message: str,
    status: ExpertStatus = ExpertStatus.MODEL_UNAVAILABLE,
    model_version: str = "none",
    latency_ms: float = 0.0,
    input_samples: int = 0,
) -> ModelInferenceResult:
    """Build an abstaining result with no probability attached."""
    return ModelInferenceResult.unavailable(
        model_id=model_id,
        model_version=model_version,
        error_code=error_code,
        error_message=error_message,
        status=status,
        latency_ms=latency_ms,
        input_samples=input_samples,
    )


async def run_blocking(fn, *args) -> Any:
    """Run blocking inference off the event loop.

    Torch inference is blocking C++ that ignores asyncio cancellation. Calling it
    directly inside a coroutine would stall the entire event loop for the whole
    forward pass, and ``asyncio.wait_for`` around it could never fire. Pushing it
    to the default executor at least gets it off the loop and makes the
    registry's timeout observable. See ``ExpertRegistry.score_all`` for the
    limitation that remains.
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, fn, *args)
