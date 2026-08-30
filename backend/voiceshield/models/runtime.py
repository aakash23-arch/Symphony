"""Torch runtime configuration: threads, determinism, device fallback (C-19, C-27).

This module is the single place that touches global torch state. It imports torch
LAZILY so that importing ``voiceshield.models`` never requires an ML library to be
installed - the experts must be constructible, and the availability report
truthful, on a machine with no torch at all.
"""

from __future__ import annotations

import threading
import warnings
from typing import Optional

from voiceshield.config import settings
from voiceshield.obs.logging import get_logger

logger = get_logger("voiceshield.models.runtime")

_configured = False
_lock = threading.Lock()


def _suppress_cosmetic_weight_norm_warning() -> None:
    """Silence a transformers warning that is misleading, not a real problem.

    Loading ``microsoft/wavlm-base-plus-sv`` under torch 2.1 + transformers 4.36
    prints:

        Some weights of the model checkpoint ... were not used ...
          ['wavlm.encoder.pos_conv_embed.conv.weight_g', '...weight_v']
        Some weights ... newly initialized:
          ['...conv.parametrizations.weight.original0', '...original1']

    That reads exactly like "the positional convolution is randomly initialised",
    which would silently corrupt every embedding. It is NOT what happens.

    VERIFIED 2026-08-28 by loading the checkpoint and comparing tensors directly:

        original0 == checkpoint weight_g  -> torch.allclose(...) is True
        original1 == checkpoint weight_v  -> torch.allclose(...) is True

    torch 2.1 renamed weight-norm's storage from ``weight_g``/``weight_v`` to
    ``parametrizations.weight.original0``/``original1``; transformers remaps them
    correctly but reports the old names as "unused". Inference was additionally
    confirmed bit-for-bit identical across independent loads with different
    torch seeds.

    We suppress it deliberately so the startup log stays readable. Do not remove
    this note: without it, the next person to see the warning will "fix" a bug
    that does not exist.
    """
    warnings.filterwarnings(
        "ignore",
        message=r".*were not used when initializing.*",
        category=UserWarning,
        module=r"transformers.*",
    )
    warnings.filterwarnings(
        "ignore",
        message=r".*newly initialized.*",
        category=UserWarning,
        module=r"transformers.*",
    )

    # transformers emits the checkpoint-mismatch notice through `logging`, not
    # `warnings`, so filterwarnings alone does not catch it. Raise the modeling
    # logger to ERROR to suppress exactly that message while leaving real load
    # failures (which log at ERROR) visible.
    import logging

    logging.getLogger("transformers.modeling_utils").setLevel(logging.ERROR)


def resolve_device(requested: Optional[str] = None) -> str:
    """Resolve the inference device, falling back to CPU where feasible.

    Never raises: an unavailable accelerator degrades to CPU with a warning
    rather than taking down the analysis worker.
    """
    want = (requested or settings.device or "cpu").lower()
    if want == "cpu":
        return "cpu"

    try:
        import torch
    except ImportError:
        logger.warning(
            "torch not installed; forcing CPU",
            extra={"extra_fields": {"requested_device": want}},
        )
        return "cpu"

    if want == "cuda" and not torch.cuda.is_available():
        logger.warning(
            "CUDA requested but unavailable; falling back to CPU",
            extra={"extra_fields": {"requested_device": want}},
        )
        return "cpu"

    if want == "mps" and not getattr(torch.backends, "mps", None):
        logger.warning(
            "MPS requested but unavailable; falling back to CPU",
            extra={"extra_fields": {"requested_device": want}},
        )
        return "cpu"

    return want


def configure_torch_runtime(force: bool = False) -> bool:
    """Configure thread count, seeding and determinism. Idempotent.

    Returns True if torch was configured, False if torch is not installed.
    Called once by the loader before any model is constructed.
    """
    global _configured
    with _lock:
        if _configured and not force:
            return True

        _suppress_cosmetic_weight_norm_warning()

        try:
            import torch
        except ImportError:
            logger.warning("torch not installed; L3 inference is unavailable")
            return False

        torch.set_num_threads(max(1, int(settings.torch_threads)))

        if settings.deterministic_mode:
            # Deterministic evaluation mode: identical audio must yield an
            # identical score, so a demo run is reproducible and a regression is
            # attributable. warn_only=True because some ops have no deterministic
            # CPU kernel; we prefer a warning over a hard failure mid-call.
            torch.manual_seed(settings.torch_seed)
            try:
                torch.use_deterministic_algorithms(True, warn_only=True)
            except (RuntimeError, TypeError) as exc:  # pragma: no cover - torch version dependent
                logger.warning(
                    "could not enable deterministic algorithms",
                    extra={"extra_fields": {"detail": str(exc)}},
                )

        _configured = True
        logger.info(
            "torch runtime configured",
            extra={
                "extra_fields": {
                    "torch_version": torch.__version__,
                    "threads": torch.get_num_threads(),
                    "deterministic": bool(settings.deterministic_mode),
                    "device": resolve_device(),
                }
            },
        )
        return True


def reset_for_tests() -> None:
    """Allow tests to re-run configuration against changed settings."""
    global _configured
    with _lock:
        _configured = False
