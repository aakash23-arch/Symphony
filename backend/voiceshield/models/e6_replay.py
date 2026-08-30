"""E6 - replay / liveness expert (C-25).

STATUS: DEFERRED (readiness B2).

Registered and abstaining so the contract field ``p_rep`` retains an explicit
status. C-25 requires a test proving the contract was NOT shortened by deleting
this expert - replay is a distinct attack class (re-recorded genuine audio) that
neither TTS detection nor speaker verification covers, and dropping the field
would erase that gap from the evidence rather than reporting it.
"""

from __future__ import annotations

from typing import List

from voiceshield.contracts import ExpertResult, ExpertStatus
from voiceshield.signal_processing import FeatureBundle

from . import errors as err
from ._expert_support import abstain
from .base import Expert

MODEL_ID_DEFERRED = "replay:deferred-b2"


class E6ReplayExpert(Expert):
    """Replay/liveness expert, deferred in this build. Always returns p=None."""

    def __init__(self, version: str = "0.0.0-deferred"):
        super().__init__(expert_id="E6", version=version)

    @property
    def required_features(self) -> List[str]:
        return ["spectral", "quality"]

    def is_available(self) -> bool:
        return False

    async def score(self, bundle: FeatureBundle) -> ExpertResult:
        """Returns DEFERRED with no probability (B2)."""
        result = abstain(
            model_id=MODEL_ID_DEFERRED,
            error_code=err.DEFERRED_IN_DEMO,
            error_message="Replay/liveness expert deferred in this build (B2)",
            status=ExpertStatus.DEFERRED,
        )
        return result.to_expert_result(self.expert_id)
