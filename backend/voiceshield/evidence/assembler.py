"""EvidenceVector assembler (C-26).

Assembles the six expert results plus frame metadata into the frozen
EvidenceVector, and does nothing else. Per C-26 the assembler does NOT weight,
calibrate, fuse, or threshold - that is L4's job - and it does NOT carry PCM.

The absence of a PCM field is the physical proof of privacy principle P2 (raw
audio is confined to the ingestion boundary). ``EvidenceVector`` has no such
field and ``extra="forbid"``, so it cannot be smuggled through; a test asserts
the serialised message contains no audio.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Dict, List, Optional, Sequence

from voiceshield.contracts import EvidenceVector, ExpertResult, ExpertStatus, FrameObject
from voiceshield.obs.logging import get_logger

logger = get_logger("voiceshield.evidence.assembler")

# Which expert fills which frozen EvidenceVector probability field.
EXPERT_TO_FIELD: Dict[str, str] = {
    "E1": "p_spec",
    "E2": "p_raw",
    "E3": "p_ssl",
    "E4": "p_spk",
    "E5": "p_beh",
    "E6": "p_rep",
}


class EvidenceVectorAssembler(ABC):
    """Abstract interface for assembling multi-expert outputs into EvidenceVector without PCM."""

    @abstractmethod
    def assemble(
        self,
        frame: FrameObject,
        expert_results: List[ExpertResult],
    ) -> EvidenceVector:
        """Assemble an EvidenceVector strictly omitting PCM audio."""
        raise NotImplementedError("EvidenceVectorAssembler.assemble is not implemented yet")


class StandardEvidenceAssembler(EvidenceVectorAssembler):
    """Concrete assembler (C-26).

    Copies frame-level context (quality, codec, language) straight through, maps
    each expert result onto its contract field, and records status, confidence
    and latency for every expert including the abstaining ones.
    """

    def __init__(self, model_versions: Optional[Sequence[str]] = None):
        # Provenance signatures, e.g. "E2:mo-thecreator/Deepfake-audio-detection@<sha>".
        # This is how model identity reaches the frozen contract, since
        # ExpertResult itself has no field for it.
        self._model_versions: List[str] = list(model_versions or [])

    def set_model_versions(self, versions: Sequence[str]) -> None:
        """Replace the recorded model provenance signatures."""
        self._model_versions = list(versions)

    def assemble(
        self,
        frame: FrameObject,
        expert_results: List[ExpertResult],
    ) -> EvidenceVector:
        """Assemble an EvidenceVector strictly omitting PCM audio.

        If every expert abstains, this still publishes a complete vector with all
        six probabilities None (C-26). L4 will read that as UNCERTAIN, which is
        the correct answer - an empty result is not the same as a safe one.
        """
        probabilities: Dict[str, Optional[float]] = {field: None for field in EXPERT_TO_FIELD.values()}
        confidences: Dict[str, Optional[float]] = {}
        statuses: Dict[str, ExpertStatus] = {}
        latencies: Dict[str, float] = {}
        frame_logits: Dict[str, List[float]] = {}

        for result in expert_results or []:
            eid = result.expert_id
            field = EXPERT_TO_FIELD.get(eid)
            if field is None:
                logger.warning(
                    "discarding result from unknown expert",
                    extra={"extra_fields": {"expert_id": eid, "session_id": frame.session_id}},
                )
                continue

            # Only an OK expert contributes a probability. Anything else leaves
            # the field None, so an abstention can never be read as a score (§22).
            if result.status == ExpertStatus.OK:
                probabilities[field] = result.p
            elif result.p is not None:
                logger.warning(
                    "expert reported a probability while not OK; discarding it",
                    extra={"extra_fields": {"expert_id": eid, "status": result.status.value}},
                )

            confidences[eid] = result.confidence if result.status == ExpertStatus.OK else None
            statuses[eid] = result.status
            latencies[eid] = result.latency_ms
            if result.logits:
                frame_logits[eid] = list(result.logits)

        return EvidenceVector(
            session_id=frame.session_id,
            frame_id=frame.frame_id,
            **probabilities,
            frame_logits=frame_logits,
            expert_confidences=confidences,
            expert_statuses=statuses,
            q_t=frame.q_t,
            codec_vec=frame.codec_vec,
            lang_t=frame.lang_t,
            switch_flag=frame.switch_flag,
            inference_latency_ms=latencies,
            model_versions=list(self._model_versions),
            timestamp=datetime.now(timezone.utc),
        )
