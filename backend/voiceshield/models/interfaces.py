"""Model adapter interfaces — the ML-library-agnostic boundary (C-19, §13).

This module defines the four interchangeable model protocols required by the L3
specification, plus the rich result type they return.

    AntiSpoofingModel        - produces a synthetic/spoof probability
    SpeakerVerificationModel - produces embeddings and a similarity
    ProsodyModel             - produces a behavioural probability from prosody
    RepresentationModel      - produces SSL hidden-state representations

NOTHING IN THIS FILE MAY IMPORT torch, transformers, OR ANY OTHER ML LIBRARY.
That isolation is the point: the UI, the risk engine, and the experts depend on
these protocols, never on a specific ML runtime. Only modules under
``models/adapters/`` are permitted to import an ML library, and they do so lazily
inside ``load()``. ``tests/test_architecture_boundaries.py`` enforces this.

Two axes, deliberately kept separate
------------------------------------
The four names above are CAPABILITY PROTOCOLS - what a model can do.
E1..E6 are CONTRACT SLOTS - which EvidenceVector field the result fills.
One adapter may serve several slots (a WavLM checkpoint can act as both a
SpeakerVerificationModel and a RepresentationModel); a slot may have no adapter
at all (E1 has no AASIST weights). Keeping the axes separate lets us satisfy the
L3 interface requirement without renaming anything in the frozen contracts.

The frozen-contract conflict, and how it is resolved
-----------------------------------------------------
The L3 specification requires every model result to carry a model identifier, a
model version, an inference timestamp, a latency, and an error state.
``contracts.evidence.ExpertResult`` is frozen (``extra="forbid"``) with only
``expert_id, status, p, confidence, logits, latency_ms`` - there is nowhere to
put model identity, timestamp, or an error message. SYMPHONY_REFERENCE §22
forbids amending a frozen contract without a specification amendment.

So the richer record lives HERE as ``ModelInferenceResult``, carrying every
required field, and is PROJECTED DOWN onto the frozen contract at the boundary
via ``to_expert_result()``. Model identity still reaches the contract through the
existing ``EvidenceVector.model_versions[]`` field, via ``version_signature()``.
Nothing frozen changes.

Nothing outside ``models/`` may depend on ``ModelInferenceResult``.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

from voiceshield.contracts import ExpertResult, ExpertStatus

# --- Measured input floors -----------------------------------------------------
#
# These are MEASURED, not guessed. Determined by binary search against the actual
# checkpoints on 2026-08-28 (torch 2.1.2+cpu, transformers 4.36.2):
#
#   WavLMForXVector           : raises RuntimeError below 4880 samples (0.305 s)
#                               from an internal TDNN conv layer.
#   Wav2Vec2ForSequenceClass. : raises below 400 samples (0.025 s).
#
# They live here as module constants (not only in settings) so the guard survives
# a config misconfiguration. Feeding a model less than this does not degrade the
# score - it throws - so the experts must abstain BEFORE calling inference.
MIN_SAMPLES_XVECTOR = 4880
MIN_SAMPLES_SPOOF = 400

# --- Score polarity ------------------------------------------------------------
#
# `p` MEANS P(INAUTHENTIC) FOR EVERY EXPERT, WITHOUT EXCEPTION.
#
# p_spec / p_raw / p_ssl are natively "probability of synthesis" - higher is more
# suspicious. Speaker verification is natively the opposite: a HIGH cosine
# similarity to the enrolled reference means the caller MATCHES the claimed
# identity, which is LESS suspicious. Emitting raw cosine as p_spk would invert
# the polarity of one expert relative to the other five, and L4 has no way to
# know which convention each field uses.
#
# So E4 emits p_spk = 1 - normalised_similarity, and carries the raw cosine in
# `logits[0]` and in `extra["cosine"]` for explanation and audit.
P_MEANS_PROBABILITY_INAUTHENTIC = True


class ModelDescriptor(BaseModel):
    """Static identity of a model artefact, known without loading it.

    ``is_substitution`` is deliberately machine-readable rather than a comment:
    the L3 specification names AASIST, RawNet2 and ECAPA-TDNN, and where we run a
    different architecture that fact must be visible in the availability report,
    assertable in a test, and impossible to lose in a docstring.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    model_id: str = Field(description="Canonical model identifier (e.g. HF repo id)")
    model_version: str = Field(description="Pinned revision SHA or manifest version")
    family: str = Field(description="Architecture family, e.g. 'wav2vec2-seq-cls'")
    sample_rate: int = Field(default=16000, description="Required input sample rate in Hz")
    min_input_samples: int = Field(description="Measured minimum input length in samples")
    license: Optional[str] = Field(default=None, description="Artefact licence identifier")
    is_substitution: bool = Field(
        default=False,
        description="True when this is NOT the architecture named in the L3 specification",
    )
    substitution_note: Optional[str] = Field(
        default=None,
        description="If is_substitution: what the spec named, what this is, and why",
    )


class ModelInferenceResult(BaseModel):
    """Rich per-inference record carrying everything the L3 spec requires.

    Projected onto the frozen ``ExpertResult`` at the contract boundary via
    ``to_expert_result()``. See the module docstring for why this type exists.
    """

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    # Identity (spec: "model identifier", "model version")
    model_id: str = Field(description="Model identifier, or a sentinel when unavailable")
    model_version: str = Field(description="Model version / pinned revision")
    model_family: str = Field(default="", description="Architecture family")

    # Timing (spec: "inference timestamp", "latency")
    inference_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp taken at the moment of inference",
    )
    latency_ms: float = Field(default=0.0, description="Measured wall-clock inference latency")

    # Outcome
    status: ExpertStatus = Field(description="Execution status (frozen enum, reused)")
    p: Optional[float] = Field(default=None, description="P(inauthentic) in [0,1], or None")
    confidence: Optional[float] = Field(default=None, description="Confidence in [0,1], or None")
    logits: Optional[List[float]] = Field(default=None, description="Raw model outputs if available")

    # Error state (spec: "error state if applicable")
    error_code: Optional[str] = Field(default=None, description="Machine-readable reason code")
    error_message: Optional[str] = Field(default=None, description="Human-readable detail")

    # Audit trail for abstention decisions
    input_samples: int = Field(default=0, description="Number of input samples seen")
    input_sample_rate: int = Field(default=0, description="Input sample rate in Hz")

    # Diagnostics with no home in the frozen contract (e.g. raw cosine)
    extra: Dict[str, float] = Field(default_factory=dict, description="Auxiliary diagnostics")

    def to_expert_result(self, expert_id: str) -> ExpertResult:
        """Project onto the frozen contract, dropping fields it cannot carry.

        This is the ONLY place a ModelInferenceResult crosses into the contract
        layer. The dropped fields (model identity, timestamp, error text) are not
        lost: identity reaches the EvidenceVector via ``version_signature()`` and
        the error text is logged by the caller.
        """
        return ExpertResult(
            expert_id=expert_id,
            status=self.status,
            p=self.p,
            confidence=self.confidence,
            logits=self.logits,
            latency_ms=self.latency_ms,
        )

    def version_signature(self, expert_id: str) -> str:
        """Identity string for ``EvidenceVector.model_versions[]``.

        Format: ``E2:mo-thecreator/Deepfake-audio-detection@<revision>``.
        This is how model provenance survives the down-conversion.
        """
        return f"{expert_id}:{self.model_id}@{self.model_version}"

    @classmethod
    def unavailable(
        cls,
        *,
        model_id: str,
        model_version: str = "none",
        error_code: str,
        error_message: str,
        status: ExpertStatus = ExpertStatus.MODEL_UNAVAILABLE,
        latency_ms: float = 0.0,
        input_samples: int = 0,
        input_sample_rate: int = 0,
    ) -> "ModelInferenceResult":
        """Build an abstaining result. Never carries a probability.

        ``p`` and ``confidence`` are forced to None: §22 requires that an
        unavailable or abstaining expert produce no score at all, rather than a
        default value that downstream layers could mistake for evidence.
        """
        return cls(
            model_id=model_id,
            model_version=model_version,
            status=status,
            p=None,
            confidence=None,
            error_code=error_code,
            error_message=error_message,
            latency_ms=latency_ms,
            input_samples=input_samples,
            input_sample_rate=input_sample_rate,
        )


@runtime_checkable
class LoadableModel(Protocol):
    """Lifecycle shared by every adapter (C-27).

    Loading is lazy and idempotent; ``load()`` must not raise on a missing
    artefact but record the failure so ``is_loaded()`` returns False. A failed
    load must not be retried on every frame.
    """

    def describe(self) -> ModelDescriptor:
        """Static identity, available without loading."""
        ...

    def load(self) -> bool:
        """Load weights. Returns True on success. Never downloads at runtime."""
        ...

    def is_loaded(self) -> bool:
        """True only if a load was attempted AND succeeded."""
        ...

    def unload(self) -> None:
        """Release the loaded model and its memory."""
        ...


@runtime_checkable
class AntiSpoofingModel(LoadableModel, Protocol):
    """Produces a synthetic/spoof probability from audio.

    Per the L3 specification, a spoof probability is produced ONLY when real
    model inference succeeds. Every other path returns an abstaining
    ModelInferenceResult with ``p=None``.
    """

    def infer(self, pcm: np.ndarray, sample_rate: int) -> ModelInferenceResult:
        """Run spoof detection. Returns p = P(synthetic) on success."""
        ...


@runtime_checkable
class SpeakerVerificationModel(LoadableModel, Protocol):
    """Produces speaker embeddings and compares them against a reference."""

    @property
    def embedding_dim(self) -> int:
        """Embedding dimensionality (model-dependent: WavLM x-vector 512, ECAPA 192)."""
        ...

    def embed(self, pcm: np.ndarray, sample_rate: int) -> np.ndarray:
        """Generate a speaker embedding for the given audio."""
        ...

    def similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Cosine similarity in [-1, 1] between two embeddings."""
        ...

    def verify(
        self, pcm: np.ndarray, sample_rate: int, reference: np.ndarray
    ) -> ModelInferenceResult:
        """Embed and compare against a reference embedding.

        Returns p = P(inauthentic) = 1 - normalised_similarity, with the raw
        cosine preserved in ``extra["cosine"]``.
        """
        ...


@runtime_checkable
class RepresentationModel(LoadableModel, Protocol):
    """Produces SSL hidden-state representations (C-22).

    Note this protocol deliberately exposes representations, NOT a probability.
    Turning hidden states into a spoof probability requires a trained probe; when
    no probe exists the consuming expert must abstain rather than invent a
    mapping.
    """

    @property
    def num_layers(self) -> int:
        """Number of transformer layers available for selection."""
        ...

    def hidden_states(
        self, pcm: np.ndarray, sample_rate: int, layers: List[int]
    ) -> np.ndarray:
        """Extract hidden states from the selected layers."""
        ...


@runtime_checkable
class ProsodyModel(LoadableModel, Protocol):
    """Produces a behavioural probability from prosodic features (C-24).

    Deferred in this build (readiness B1). The protocol exists so the contract
    field ``p_beh`` retains an explicit status rather than being removed.
    """

    def infer(self, prosody: Dict[str, Any]) -> ModelInferenceResult:
        """Score prosodic features. Returns p = P(inauthentic) on success."""
        ...
