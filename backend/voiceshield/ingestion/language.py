"""Language tagging (C-12).

Populates lang_t and switch_flag.

No language-identification model is loaded and no multilingual capability is
claimed (readiness B5: no Indic fixtures exist, no validated capability). The
honest state for this build is lang_t = "UNKNOWN" and switch_flag = False, and
the UI must render that rather than a plausible-looking guess.
"""

from dataclasses import dataclass
from typing import Optional

import numpy as np

UNKNOWN_LANGUAGE = "UNKNOWN"


@dataclass
class LanguageResult:
    lang_t: str = UNKNOWN_LANGUAGE
    switch_flag: bool = False


class LanguageTagger:
    """Emit the honest UNKNOWN language state until a validated tagger exists."""

    def __init__(self, tagger: Optional[object] = None):
        #: Reserved seam for a real tagger. None means: report UNKNOWN.
        self._tagger = tagger

    @property
    def model_loaded(self) -> bool:
        return self._tagger is not None

    def tag(self, pcm: np.ndarray, sample_rate: int) -> LanguageResult:
        if self._tagger is None:
            return LanguageResult(lang_t=UNKNOWN_LANGUAGE, switch_flag=False)
        raise NotImplementedError(
            "LanguageTagger with a loaded model is not implemented; "
            "no validated language capability is claimed for this build"
        )
