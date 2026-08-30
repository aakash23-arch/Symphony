"""E3 - multilingual SSL representation expert (C-22).

STATUS: MODEL_UNAVAILABLE, reason PROBE_NOT_TRAINED.

This one needs care, because the backbone IS available while the expert is NOT.

C-22 specifies: ``selected hidden layers -> lightweight probe -> spoof
classifier``. A WavLM backbone can be loaded and hidden states extracted - that
half works and the layer-selection machinery below is real. What does not exist
is the PROBE: the trained head that maps those hidden states to a spoof
probability.

VERIFIED 2026-08-28: ``microsoft/wavlm-base-plus-sv``'s ``id2label`` contains
1211 generic ``LABEL_n`` entries - speaker identity classes from x-vector
training, NOT spoof/genuine classes. There is no trained spoof probe for this
backbone in this environment, and training one requires labelled spoof data
which readiness R1 confirms does not exist here.

Producing ``p_ssl`` anyway would mean inventing a mapping from representation to
probability. That is precisely the fabrication §22 forbids, so E3 abstains.

Deliberately NOT done: reusing the E2 deepfake classifier's output as p_ssl.
That would make E3 a copy of E2, and L4 would fuse two perfectly correlated
numbers as if they were independent evidence - actively worse than abstaining,
because it would inflate apparent agreement between experts.

The layer-selection config is implemented and tested so that when a probe is
trained, this expert becomes a drop-in.
"""

from __future__ import annotations

from typing import List, Optional

from voiceshield.contracts import ExpertResult, ExpertStatus
from voiceshield.signal_processing import FeatureBundle

from . import errors as err
from ._expert_support import abstain
from .base import Expert
from .interfaces import RepresentationModel

MODEL_ID_NO_PROBE = "wavlm-ssl:probe-not-trained"

# C-22: "probe frozen SSL layers rather than blindly assuming the final layer is
# optimal." Middle layers of an SSL encoder typically carry more phonetic and
# channel detail than the final layer, which specialises toward the pretraining
# objective. These are the layers a future probe would consume.
DEFAULT_PROBE_LAYERS = [4, 8, 12]


class E3SSLExpert(Expert):
    """SSL representation expert. Abstains: backbone loads, probe does not exist."""

    def __init__(
        self,
        adapter: Optional[RepresentationModel] = None,
        layers: Optional[List[int]] = None,
        version: str = "0.0.0-no-probe",
    ):
        super().__init__(expert_id="E3", version=version)
        self._adapter = adapter
        self._layers = list(layers) if layers is not None else list(DEFAULT_PROBE_LAYERS)

    @property
    def required_features(self) -> List[str]:
        return ["raw_pcm"]

    @property
    def probe_layers(self) -> List[int]:
        """Hidden layers a trained probe would consume (C-22 layer selection)."""
        return list(self._layers)

    @property
    def model_id(self) -> str:
        return MODEL_ID_NO_PROBE

    @property
    def unavailable_reason(self) -> str:
        """Surfaced in the availability report: the backbone is not the blocker."""
        return err.PROBE_NOT_TRAINED

    def is_available(self) -> bool:
        """False regardless of backbone availability: no trained probe exists.

        Note this is False even when ``self._adapter`` loads successfully. A
        backbone without a probe cannot produce a spoof probability, and
        reporting OK here would imply an evidence source that does not exist.
        """
        return False

    async def score(self, bundle: FeatureBundle) -> ExpertResult:
        """Always abstains with PROBE_NOT_TRAINED."""
        result = abstain(
            model_id=MODEL_ID_NO_PROBE,
            error_code=err.PROBE_NOT_TRAINED,
            error_message=(
                "SSL backbone is loadable but no trained spoof probe exists; "
                "mapping hidden states to a probability would require inventing "
                "a classifier head (C-22, §22)"
            ),
            status=ExpertStatus.MODEL_UNAVAILABLE,
        )
        return result.to_expert_result(self.expert_id)
