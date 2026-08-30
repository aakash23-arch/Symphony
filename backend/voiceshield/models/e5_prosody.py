"""E5 - prosodic / behavioural expert (C-24).

STATUS: DEFERRED (readiness B1).

This expert is registered and returns an explicit DEFERRED status so the frozen
contract field ``p_beh`` stays populated with a real status rather than being
quietly dropped. C-25's test method requires proof that the contract was not
shortened by removing a deferred expert.

It consumes prosody features and returns ``p=None``. L4 assigns a deferred expert
zero weight; it must never be read as weak evidence of authenticity.

Note that §6.2 describes E5 as "a weak supporting expert, never proof of human
speech" even once implemented.
"""

from __future__ import annotations

from typing import List

from voiceshield.contracts import ExpertResult, ExpertStatus
from voiceshield.signal_processing import FeatureBundle

from . import errors as err
from ._expert_support import abstain
from .base import Expert

MODEL_ID_DEFERRED = "prosody:deferred-b1"


class E5ProsodyExpert(Expert):
    """Behavioural expert, deferred in this build. Always returns p=None."""

    def __init__(self, version: str = "0.0.0-deferred"):
        super().__init__(expert_id="E5", version=version)

    @property
    def required_features(self) -> List[str]:
        return ["prosody"]

    def is_available(self) -> bool:
        return False

    async def score(self, bundle: FeatureBundle) -> ExpertResult:
        """Returns DEFERRED with no probability (B1)."""
        result = abstain(
            model_id=MODEL_ID_DEFERRED,
            error_code=err.DEFERRED_IN_DEMO,
            error_message="Prosodic/behavioural expert deferred in this build (B1)",
            status=ExpertStatus.DEFERRED,
        )
        return result.to_expert_result(self.expert_id)
