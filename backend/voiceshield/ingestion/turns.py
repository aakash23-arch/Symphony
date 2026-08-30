"""Turn segmentation, diarisation-lite (C-11).

Marks speaker_turn and overlap_flag using energy and pause heuristics only.

This is NOT speaker diarisation and it does not identify speakers. Calling it
diarisation in the UI would be a production claim the system cannot support.
On failure it falls back to a single-turn assumption with overlap_flag = None.
"""

from dataclasses import dataclass
from typing import Optional

import numpy as np

from voiceshield.obs.logging import get_logger

logger = get_logger("voiceshield.ingestion.turns")

_EPS = 1e-12

#: Seconds of continuous non-speech that ends the current turn.
DEFAULT_PAUSE_S = 0.6
#: Level change (dB) across a pause that suggests a different talker.
DEFAULT_LEVEL_DELTA_DB = 6.0


@dataclass
class TurnResult:
    speaker_turn: Optional[int]
    overlap_flag: Optional[bool]


class TurnSegmenter:
    """Track a turn index across frames using pause and level heuristics."""

    def __init__(
        self,
        pause_s: float = DEFAULT_PAUSE_S,
        level_delta_db: float = DEFAULT_LEVEL_DELTA_DB,
    ):
        self.pause_s = pause_s
        self.level_delta_db = level_delta_db
        self._turn_index = 0
        self._silence_accum = 0.0
        self._last_speech_level_db: Optional[float] = None
        self._pending_boundary = False
        self.failure_count = 0

    def reset(self) -> None:
        self._turn_index = 0
        self._silence_accum = 0.0
        self._last_speech_level_db = None
        self._pending_boundary = False

    def segment(
        self,
        pcm: np.ndarray,
        sample_rate: int,
        is_speech: bool,
        frame_duration_s: float,
    ) -> TurnResult:
        """Update and return the turn index and overlap flag for this frame."""
        try:
            return self._segment(pcm, sample_rate, is_speech, frame_duration_s)
        except Exception as exc:
            self.failure_count += 1
            logger.warning(
                "Turn segmentation failed; assuming a single turn",
                extra={"extra_fields": {"error": str(exc)}},
            )
            return TurnResult(speaker_turn=self._turn_index, overlap_flag=None)

    def _segment(
        self,
        pcm: np.ndarray,
        sample_rate: int,
        is_speech: bool,
        frame_duration_s: float,
    ) -> TurnResult:
        if not is_speech:
            self._silence_accum += frame_duration_s
            if self._silence_accum >= self.pause_s:
                self._pending_boundary = True
            return TurnResult(speaker_turn=self._turn_index, overlap_flag=False)

        level_db = 20.0 * np.log10(
            max(float(np.sqrt(np.mean(pcm.astype(np.float64) ** 2))), _EPS)
        )

        if self._pending_boundary:
            # A long pause alone starts a new turn; a level jump across it is
            # extra evidence, not a requirement.
            self._turn_index += 1
            self._pending_boundary = False
        elif (
            self._last_speech_level_db is not None
            and abs(level_db - self._last_speech_level_db) >= self.level_delta_db
            and self._silence_accum > 0
        ):
            self._turn_index += 1

        self._silence_accum = 0.0
        self._last_speech_level_db = level_db

        return TurnResult(speaker_turn=self._turn_index, overlap_flag=self._detect_overlap(pcm))

    @staticmethod
    def _detect_overlap(pcm: np.ndarray) -> Optional[bool]:
        """Crude overlap hint: unusually high spectral flatness during speech.

        This is a heuristic placeholder, deliberately conservative. It never
        claims multi-speaker separation.
        """
        if pcm.size < 64:
            return None
        try:
            spectrum = np.abs(np.fft.rfft(pcm.astype(np.float64))) ** 2
            spectrum = spectrum[1:]
            if spectrum.size == 0 or spectrum.sum() <= _EPS:
                return None
            geo = np.exp(np.mean(np.log(spectrum + _EPS)))
            arith = float(np.mean(spectrum))
            flatness = float(geo / (arith + _EPS))
            return bool(flatness > 0.5)
        except Exception:
            return None
