"""L3 model error types and reason codes (C-19..C-27, §22).

Every L3 failure is typed and carries a machine-readable reason code so the UI can
show *why* an expert produced no score instead of showing an invented one (§22).

L3's normal failure mode is to RETURN an abstaining ExpertResult, not to raise.
These exceptions exist so the reason code is a shared constant, and for the few
genuinely fatal integrity failures in the loader.
"""

from typing import Optional

from voiceshield.contracts.errors import VoiceShieldException

# --- Reason codes --------------------------------------------------------------

# Weight acquisition / integrity (C-27)
WEIGHTS_NOT_ACQUIRED = "WEIGHTS_NOT_ACQUIRED"
MANIFEST_MISSING = "MANIFEST_MISSING"
MANIFEST_MALFORMED = "MANIFEST_MALFORMED"
ARTEFACT_MISSING = "ARTEFACT_MISSING"
CHECKSUM_MISMATCH = "CHECKSUM_MISMATCH"
BACKEND_IMPORT_FAILED = "BACKEND_IMPORT_FAILED"
MODEL_LOAD_FAILED = "MODEL_LOAD_FAILED"

# Model semantics
PROBE_NOT_TRAINED = "PROBE_NOT_TRAINED"
LABEL_MAP_UNRECOGNIZED = "LABEL_MAP_UNRECOGNIZED"

# Input validation
INSUFFICIENT_AUDIO = "INSUFFICIENT_AUDIO"
MISSING_RAW_PCM = "MISSING_RAW_PCM"
MISSING_SPECTRAL = "MISSING_SPECTRAL"
MALFORMED_INPUT = "MALFORMED_INPUT"
NON_FINITE_INPUT = "NON_FINITE_INPUT"

# Speaker enrollment (C-23)
ENROLLMENT_MISSING = "ENROLLMENT_MISSING"
ENROLLMENT_DIM_MISMATCH = "ENROLLMENT_DIM_MISMATCH"
E4_STRIDE_SKIP = "E4_STRIDE_SKIP"

# Execution (C-19)
INFERENCE_TIMEOUT = "INFERENCE_TIMEOUT"
INFERENCE_ERROR = "INFERENCE_ERROR"

# Deferred experts (B1/B2)
DEFERRED_IN_DEMO = "DEFERRED_IN_DEMO"


class ModelUnavailable(VoiceShieldException):
    """Model weights are absent, unreadable, or the backend could not be imported.

    Raised only inside the loader. Experts translate this into an abstaining
    ExpertResult; they never let it escape into the pipeline (C-19).
    """

    def __init__(
        self,
        reason: str = WEIGHTS_NOT_ACQUIRED,
        message: Optional[str] = None,
        session_id: Optional[str] = None,
    ):
        super().__init__(
            code=reason,
            message=message or f"Model unavailable: {reason}",
            status_code=503,
            session_id=session_id,
            retriable=False,
        )
        self.reason = reason


class ModelIntegrityError(VoiceShieldException):
    """A vendored artefact failed checksum verification (C-27).

    This is fatal for the affected model: a weight file that does not match the
    manifest must never be loaded and silently used for inference.
    """

    def __init__(
        self,
        message: str = "Model artefact failed integrity verification",
        reason: str = CHECKSUM_MISMATCH,
        session_id: Optional[str] = None,
    ):
        super().__init__(
            code=reason,
            message=message,
            status_code=500,
            session_id=session_id,
            retriable=False,
        )
        self.reason = reason


class InferenceTimeout(VoiceShieldException):
    """An expert exceeded its per-expert time budget (C-19)."""

    def __init__(
        self,
        message: str = "Expert inference exceeded its time budget",
        session_id: Optional[str] = None,
    ):
        super().__init__(
            code=INFERENCE_TIMEOUT,
            message=message,
            status_code=504,
            session_id=session_id,
            retriable=True,
        )
        self.reason = INFERENCE_TIMEOUT
